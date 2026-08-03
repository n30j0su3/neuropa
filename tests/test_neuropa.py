from __future__ import annotations

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from neuropa.api.app import create_app
from neuropa.domain import (
    Artifact, CalendarEvent, Database, FocusSession, InboxItem, MemoryClaim,
    Preset, Project, Provider, Reminder, Skill, Task,
)


@pytest.fixture
def db(tmp_path: Path):
    database = Database(tmp_path / "neuropa.db")
    yield database
    database.close()


def test_all_domain_entities_crud(db: Database):
    entities = [
        InboxItem(raw_text="idea"), Task(title="T", next_action="do one thing"), Reminder(what="call"),
        Project(name="P"), FocusSession(), CalendarEvent(title="E"),
        MemoryClaim(claim_text="fact", source_type="note", source_ref="n1", confidence=0.8),
        Artifact(title="A"), Skill(name="S"), Provider(model="mock-default"), Preset(name="minimal"),
    ]
    for entity in entities:
        db.create(entity)
        loaded = db.get(entity.entity_type, entity.id)
        assert loaded is not None
        assert loaded.id == entity.id
        updated = db.update(loaded, status="updated") if hasattr(loaded, "status") else db.update(loaded, name="updated") if hasattr(loaded, "name") else loaded
        assert updated.id == entity.id
        assert db.list(entity.entity_type)


def test_inbox_raw_text_is_immutable(db: Database):
    item = db.create(InboxItem(raw_text="original"))
    updated = db.update(item, raw_text="tampered", status="clarified")
    assert updated.raw_text == "original"
    assert updated.status == "clarified"


def test_memory_claim_supersede(db: Database):
    old = db.create(MemoryClaim(claim_text="old", source_type="note", source_ref="a", confidence=.5))
    new = db.supersede(old.id, MemoryClaim(claim_text="new", source_type="user", source_ref="b", confidence=.9))
    assert db.get("memory_claim", old.id).superseded_by == new.id
    assert db.get("memory_claim", new.id).claim_text == "new"


def test_memory_claim_supersede_rolls_back_new_claim_when_old_was_raced(db: Database):
    old = db.create(MemoryClaim(claim_text="old", source_type="note", source_ref="a", confidence=.5))
    winner = db.create(MemoryClaim(claim_text="winner", source_type="user", source_ref="b", confidence=.9))
    db.update(db.get("memory_claim", old.id), superseded_by=winner.id)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="already superseded"):
        db.supersede(old.id, MemoryClaim(claim_text="loser", source_type="user", source_ref="c", confidence=.9))

    assert [claim.claim_text for claim in db.list("memory_claim")] == ["winner", "old"]


def test_memory_claim_supersede_allows_one_winner_under_concurrency(tmp_path: Path):
    path = tmp_path / "concurrent.db"
    setup = Database(path)
    old = setup.create(MemoryClaim(claim_text="old", source_type="note", source_ref="a", confidence=.5))
    setup.close()

    def attempt(text: str):
        database = Database(path)
        try:
            return database.supersede(old.id, MemoryClaim(claim_text=text, source_type="user", source_ref=text, confidence=.9)).claim_text
        finally:
            database.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(attempt, "first"), pool.submit(attempt, "second")]
        outcomes = []
        for future in futures:
            try:
                outcomes.append(("ok", future.result()))
            except ValueError as exc:
                outcomes.append(("rejected", str(exc)))

    assert sorted(status for status, _ in outcomes) == ["ok", "rejected"]
    final = Database(path)
    try:
        claims = final.list("memory_claim")
        assert len(claims) == 2
        assert sum(claim.claim_text in {"first", "second"} for claim in claims) == 1
    finally:
        final.close()


def test_migration_from_zero_is_idempotent(tmp_path: Path):
    path = tmp_path / "fresh.db"
    first = Database(path)
    assert first.migrate() == 1
    first.close()
    second = Database(path)
    assert second.migrate() == 1
    assert second.conn.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0] == 1
    second.close()


def test_api_health_without_auth(tmp_path: Path):
    client = TestClient(create_app(Database(tmp_path / "api.db")))
    assert client.get("/api/health").status_code == 200


def test_api_inbox_auth_and_crud(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("NEUROPA_DATA_DIR", str(tmp_path / "data"))
    client = TestClient(create_app(Database(tmp_path / "api.db")))
    assert client.get("/api/inbox").status_code == 401
    token = (tmp_path / "data" / "token").read_text()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/inbox", json={"raw_text": "capture me"}, headers=headers)
    assert response.status_code == 201
    item_id = response.json()["id"]
    assert client.get("/api/inbox", headers=headers).status_code == 200
    assert client.get(f"/api/inbox/{item_id}", headers=headers).status_code == 200
    assert client.post(f"/api/inbox/{item_id}/archive", headers=headers).status_code == 200
