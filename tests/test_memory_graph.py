from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from neuropa.api.app import create_app
from neuropa.domain import ChatMessage, ChatSession, Database, MemoryClaim
from neuropa.memory import MemoryClaimService
from neuropa.memory.graph import build_memory_graph, normalize_source_node


def test_source_node_is_deterministic_and_does_not_embed_raw_ref():
    first = normalize_source_node("note", "secret-token=abc123")
    second = normalize_source_node("note", "secret-token=abc123")
    assert first["id"] == second["id"]
    assert first["id"].startswith("source:note:")
    assert "abc123" not in first["id"]


@pytest.mark.parametrize(
    "source_ref",
    [
        "https://user:pass@example.test/private?api_key=secret#fragment",
        "Bearer super-secret-token",
        "https://example.test/api_key/secret-value",
        "/home/alice/private/credentials.json",
    ],
)
def test_graph_exposes_only_opaque_display_refs(source_ref: str, tmp_path: Path):
    db = Database(tmp_path / "memory.db")
    claim = db.create(MemoryClaim(claim_text="private", source_type="note", source_ref=source_ref, confidence=.8))

    graph = build_memory_graph(db)
    visible = repr(graph)

    assert source_ref not in visible
    assert "user:pass" not in visible
    assert "super-secret-token" not in visible
    assert "/home/" not in visible
    claim_node = next(node for node in graph["nodes"] if node["id"] == f"claim:{claim.id}")
    assert claim_node["display_ref"].startswith("ref:")
    assert claim_node["display_ref"] == claim_node["source_ref"]


def test_graph_projects_only_explicit_provenance_and_supersession(tmp_path: Path):
    db = Database(tmp_path / "memory.db")
    source_claim = db.create(MemoryClaim(claim_text="Uses SQLite", source_type="note", source_ref="notes/db", confidence=.8))
    derived_claim = db.create(MemoryClaim(claim_text="SQLite is fast", source_type="inference", source_ref="", confidence=.4))
    session = db.create(ChatSession(title="Evidence session"))
    db.create(ChatMessage(session_id=session.id, role="assistant", content="ok", process_summary={"sources": [source_claim.id]}))

    graph = build_memory_graph(db)
    assert {node["id"] for node in graph["nodes"]} >= {f"claim:{source_claim.id}", f"claim:{derived_claim.id}", normalize_source_node("note", "notes/db")["id"], f"session:{session.id}"}
    assert {edge["type"] for edge in graph["edges"]} >= {"sourced_from", "used_in_session"}
    assert not any(edge["type"] == "used_in_session" and edge["source"] == f"claim:{derived_claim.id}" for edge in graph["edges"])
    assert not any(edge["type"] == "derived_from" for edge in graph["edges"])


def test_graph_filters_query_source_status_and_confidence(tmp_path: Path):
    db = Database(tmp_path / "memory.db")
    active = db.create(MemoryClaim(claim_text="Python uses SQLite", source_type="note", source_ref="a", confidence=.9))
    db.create(MemoryClaim(claim_text="Python uses files", source_type="chat", source_ref="b", confidence=.2))
    graph = build_memory_graph(db, {"query": "sqlite", "source": "note", "status": "active", "confidence": .8})
    assert [node["id"] for node in graph["nodes"] if node["type"] == "claim"] == [f"claim:{active.id}"]


def test_supersede_creates_new_claim_preserves_old_and_rejects_double(tmp_path: Path):
    db = Database(tmp_path / "memory.db")
    service = MemoryClaimService(db)
    old = service.store_claim("old", "note", "a", .5)
    new = service.supersede_claim(old.id, claim_text="corrected", source_type="note", source_ref="b", confidence=.9)
    assert db.get("memory_claim", old.id).superseded_by == new.id
    assert db.get("memory_claim", new.id).claim_text == "corrected"
    with pytest.raises(ValueError, match="already superseded"):
        service.supersede_claim(old.id, claim_text="again", source_type="note", source_ref="c", confidence=.9)


def test_graph_api_is_authenticated_and_supersede_endpoint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("NEUROPA_DATA_DIR", str(tmp_path / "data"))
    db = Database(tmp_path / "api.db")
    client = TestClient(create_app(db))
    assert client.get("/api/memory/graph").status_code == 401
    token = (tmp_path / "data" / "token").read_text().strip()
    headers = {"Authorization": f"Bearer {token}"}
    old = client.post("/api/memory/store", json={"claim_text": "old", "source_ref": "a"}, headers=headers).json()
    response = client.post(f"/api/memory/claims/{old['id']}/supersede", json={"claim_text": "new", "source_ref": "b", "confidence": .9}, headers=headers)
    assert response.status_code == 201
    graph = client.get("/api/memory/graph", headers=headers)
    assert graph.status_code == 200
    assert any(edge["type"] == "supersedes" for edge in graph.json()["edges"])
    assert client.post(f"/api/memory/claims/{old['id']}/supersede", json={"claim_text": "again"}, headers=headers).status_code == 409
