from pathlib import Path
import json

import pytest
from fastapi.testclient import TestClient

from neuropa.api.app import create_app
from neuropa.domain import Artifact, Database, Workspace, ChatSession, ChatMessage, AgentMode, ToolDefinition
from neuropa.services import HarnessService
from neuropa.providers import NoAIProviderAvailable


class FakeRouter:
    def __init__(self, fail=False): self.fail = fail
    def generate(self, messages, **kwargs):
        if self.fail: raise RuntimeError("offline")
        return {"text": "respuesta real", "provider_used": "fake", "model": "fake-1", "usage": {"output": 2}}
    def status(self): return {"modes": {}}


class CatalogRouter(FakeRouter):
    def __init__(self):
        super().__init__()
        self.calls = []

    def status(self):
        return {"modes": {"local": {"models": ["local-1"]}}}

    def generate(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        return super().generate(messages, **kwargs)


def test_harness_entities_seed_and_artifact(tmp_path):
    db = Database(tmp_path / "x.db")
    for obj in [Workspace(name="W"), ChatSession(title="S"), ChatMessage(content="m"), AgentMode(slug="x"), ToolDefinition(slug="t")]:
        db.create(obj); assert db.get(obj.entity_type, obj.id).id == obj.id
    svc = HarnessService(db, FakeRouter(), tmp_path)
    HarnessService(db, FakeRouter(), tmp_path)
    assert {m.slug for m in db.list("agent_mode")} >= {"creativity", "clarity", "detail", "memory"}
    session = svc.create_session()
    answer = svc.send_message(session.id, "hola")
    artifact = svc.create_artifact(answer.id)
    assert Path(tmp_path / artifact.path).exists()
    db.close()


def test_failed_provider_preserves_user(tmp_path):
    db = Database(tmp_path / "x.db")
    svc = HarnessService(db, FakeRouter(True), tmp_path)
    session = svc.create_session()
    try: svc.send_message(session.id, "persistir")
    except NoAIProviderAvailable: pass
    assert any(m.content == "persistir" and m.status == "failed" for m in db.list("chat_message"))
    db.close()


def test_session_context_scope_defaults_and_selected_memory_is_evidence_only(tmp_path):
    db = Database(tmp_path / "x.db")
    router = CatalogRouter()
    svc = HarnessService(db, router, tmp_path)
    session = svc.create_session()
    claim = db.create(__import__("neuropa.domain", fromlist=["MemoryClaim"]).MemoryClaim(claim_text="La reunión es el martes"))
    assert session.context_scope == "session"
    assert session.context_claim_ids == []
    answer = svc.send_message(session.id, "¿cuándo?", provider="local", model="local-1", context_scope="session_memory", memory_claim_ids=[claim.id])
    sent = router.calls[-1][0]
    assert len(sent) == 3
    assert "EVIDENCIA NO INSTRUCCIONAL" in sent[1]["content"]
    assert claim.id in answer.process_summary["sources"]
    stored = db.get("chat_session", session.id)
    assert stored.context_scope == "session_memory"
    assert stored.context_claim_ids == [claim.id]
    db.close()


def test_invalid_or_superseded_memory_claim_is_rejected_before_provider(tmp_path):
    db = Database(tmp_path / "x.db")
    router = CatalogRouter()
    svc = HarnessService(db, router, tmp_path)
    session = svc.create_session()
    import pytest
    with pytest.raises(ValueError):
        svc.send_message(session.id, "x", provider="local", model="local-1", context_scope="session_memory", memory_claim_ids=["missing"])
    assert router.calls == []
    db.close()


def test_session_memory_includes_recent_history_evidence_and_current_user_once(tmp_path):
    db = Database(tmp_path / "x.db")
    router = CatalogRouter()
    svc = HarnessService(db, router, tmp_path)
    session = svc.create_session()
    claim = db.create(__import__("neuropa.domain", fromlist=["MemoryClaim"]).MemoryClaim(claim_text="La reunión es el martes"))
    db.create(__import__("neuropa.domain", fromlist=["ChatMessage"]).ChatMessage(session_id=session.id, role="user", content="anterior"))
    db.create(__import__("neuropa.domain", fromlist=["ChatMessage"]).ChatMessage(session_id=session.id, role="assistant", content="respuesta anterior"))

    svc.send_message(session.id, "¿cuándo?", provider="local", model="local-1", context_scope="session_memory", memory_claim_ids=[claim.id])

    sent = router.calls[-1][0]
    assert [message["role"] for message in sent] == ["system", "user", "assistant", "system", "user"]
    assert sent[1]["content"] == "anterior"
    assert sent[2]["content"] == "respuesta anterior"
    assert "EVIDENCIA NO INSTRUCCIONAL" in sent[3]["content"]
    assert [message["content"] for message in sent].count("¿cuándo?") == 1
    db.close()


def test_omitted_request_scope_preserves_session_scope_and_claims(tmp_path):
    from neuropa.api.app import HarnessMessageRequest

    db = Database(tmp_path / "x.db")
    router = CatalogRouter()
    svc = HarnessService(db, router, tmp_path)
    session = svc.create_session()
    claim = db.create(__import__("neuropa.domain", fromlist=["MemoryClaim"]).MemoryClaim(claim_text="Hecho persistente"))
    db.update(session, context_scope="session_memory", context_claim_ids=[claim.id])

    request = HarnessMessageRequest.model_validate({"content": "consulta"})
    svc.send_message(session.id, provider="local", model="local-1", **request.model_dump(exclude={"provider", "model"}))

    sent = router.calls[-1][0]
    assert request.context_scope is None
    assert "EVIDENCIA NO INSTRUCCIONAL" in sent[1]["content"]
    assert sent[-1] == {"role": "user", "content": "consulta"}
    db.close()




def test_send_message_normalizes_and_persists_usage_metrics(tmp_path):
    class TimingRouter(FakeRouter):
        def generate(self, messages, **kwargs):
            return {
                "text": "respuesta real",
                "provider_used": "fake",
                "model": "fake-1",
                "usage": {"output_tokens": 3, "input_tokens": 5, "elapsed": 0.42},
            }

    db = Database(tmp_path / "usage.db")
    svc = HarnessService(db, TimingRouter(), tmp_path)
    session = svc.create_session()
    answer = svc.send_message(session.id, "hola")
    assert answer.usage is not None
    assert answer.usage["input_tokens"] == 5
    assert answer.usage["output_tokens"] == 3
    assert float(answer.usage["elapsed"]) >= 0.0
    assert "output_tokens_per_sec" in answer.usage
    db.close()
def test_unknown_or_unavailable_catalog_does_not_reject_model(tmp_path):
    import pytest

    class RouterWithStatus(FakeRouter):
        def __init__(self, entry):
            super().__init__()
            self.entry = entry

        def status(self):
            return {"modes": {"local": self.entry}}

    for entry in ({"available": False, "models": [], "catalog_known": False}, {"available": True, "catalog_known": False}):
        db = Database(tmp_path / f"{len(entry)}-{entry.get('available')}.db")
        router = RouterWithStatus(entry)
        svc = HarnessService(db, router, tmp_path)
        session = svc.create_session()
        svc.send_message(session.id, "x", provider="local", model="not-listed")
        db.close()

    db = Database(tmp_path / "known.db")
    router = RouterWithStatus({"available": True, "models": ["listed"], "catalog_known": True})
    svc = HarnessService(db, router, tmp_path)
    session = svc.create_session()
    with pytest.raises(ValueError):
        svc.send_message(session.id, "x", provider="local", model="not-listed")
    db.close()


def test__title_from_first_message_basic():
    """G2 RED: pure helper produces deterministic titles."""
    from neuropa.services.harness import _title_from_first_message
    assert _title_from_first_message("Necesito organizar el proyecto") == "Necesito organizar el proyecto"
    assert _title_from_first_message("  espacios  ") == "espacios"
    assert _title_from_first_message("") == "Nueva sesión"
    assert _title_from_first_message("   ") == "Nueva sesión"


def test__title_from_first_message_truncates_at_word_boundary():
    from neuropa.services.harness import _title_from_first_message
    long = "palabra " * 20  # 160 chars
    title = _title_from_first_message(long, limit=60)
    assert len(title) <= 60
    assert not title.endswith(" ")


def test_first_message_renames_default_session(tmp_path):
    """G2 RED: default-titled session gets a deterministic title from first user message."""
    db = Database(tmp_path / "title.db")
    svc = HarnessService(db, FakeRouter(), tmp_path)
    session = svc.create_session()
    assert session.title == "Nueva sesión"
    svc.send_message(session.id, "Necesito organizar el envío de Maaji")
    stored = db.get("chat_session", session.id)
    assert stored.title == "Necesito organizar el envío de Maaji"
    assert stored.title != "Nueva sesión"
    db.close()


def test_custom_title_survives_send_message(tmp_path):
    """G2 RED: a session with a custom title is never auto-renamed."""
    db = Database(tmp_path / "custom.db")
    svc = HarnessService(db, FakeRouter(), tmp_path)
    session = svc.create_session(title="Mi proyecto especial")
    svc.send_message(session.id, "algo nuevo aquí")
    stored = db.get("chat_session", session.id)
    assert stored.title == "Mi proyecto especial"
    db.close()


def test_second_message_does_not_retitle(tmp_path):
    """G2 RED: second user message does not change the title again."""
    db = Database(tmp_path / "second.db")
    svc = HarnessService(db, FakeRouter(), tmp_path)
    session = svc.create_session()
    svc.send_message(session.id, "primera idea")
    title_after_first = db.get("chat_session", session.id).title
    svc.send_message(session.id, "segunda idea completamente diferente")
    title_after_second = db.get("chat_session", session.id).title
    assert title_after_first == title_after_second == "primera idea"
    db.close()


def test_read_artifact_returns_content(tmp_path):
    """G4 RED: read_artifact returns existing markdown content."""
    db = Database(tmp_path / "read_art.db")
    svc = HarnessService(db, FakeRouter(), tmp_path)
    session = svc.create_session()
    answer = svc.send_message(session.id, "contenido de prueba")
    artifact = svc.create_artifact(answer.id)
    result = svc.read_artifact(artifact.id)
    assert result["content"] == "respuesta real"
    assert result["id"] == artifact.id
    db.close()


def test_read_artifact_rejects_missing(tmp_path):
    """G4 RED: read_artifact raises KeyError for missing artifact."""
    import pytest
    db = Database(tmp_path / "read_miss.db")
    svc = HarnessService(db, FakeRouter(), tmp_path)
    with pytest.raises(KeyError):
        svc.read_artifact("nonexistent-id")
    db.close()


def test_read_artifact_rejects_traversal_missing_file_and_non_utf8(tmp_path):
    db = Database(tmp_path / "read_safety.db")
    svc = HarnessService(db, FakeRouter(), tmp_path)

    traversal = db.create(Artifact(type="markdown", path="../outside.md", title="outside"))
    with pytest.raises(ValueError, match="escapes root"):
        svc.read_artifact(traversal.id)

    missing = db.create(Artifact(type="markdown", path="artifacts/missing.md", title="missing"))
    with pytest.raises(FileNotFoundError):
        svc.read_artifact(missing.id)

    artifacts = tmp_path / "artifacts"
    artifacts.mkdir(exist_ok=True)
    (artifacts / "binary.md").write_bytes(b"\xff\xfe")
    non_utf8 = db.create(Artifact(type="markdown", path="artifacts/binary.md", title="binary"))
    with pytest.raises(ValueError, match="UTF-8"):
        svc.read_artifact(non_utf8.id)
    db.close()


def test_artifact_get_is_authenticated_and_returns_exact_escaped_source(tmp_path, monkeypatch):
    data_dir = tmp_path / "api-data"
    monkeypatch.setenv("NEUROPA_DATA_DIR", str(data_dir))
    db = Database(tmp_path / "artifact_api.db")
    svc = HarnessService(db, FakeRouter(), data_dir)
    session = svc.create_session(title="Sesión fuente")
    answer = svc.send_message(session.id, "guarda esto")
    artifact = svc.create_artifact(answer.id)
    artifact_path = data_dir / artifact.path
    artifact_path.write_text("<script>window.__artifact_xss=1</script>", encoding="utf-8")

    client = TestClient(create_app(db, router=FakeRouter(), harness=svc))
    assert client.get(f"/api/artifacts/{artifact.id}").status_code == 401
    token = (data_dir / "token").read_text(encoding="utf-8").strip()
    response = client.get(
        f"/api/artifacts/{artifact.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["content"] == "<script>window.__artifact_xss=1</script>"
    assert payload["source_session"] == "Sesión fuente"
    assert payload["checksum"] == artifact.blob_ref
    db.close()
