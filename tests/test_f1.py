from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from neuropa.api.app import create_app
from neuropa.domain import Database, MemoryClaim, Task
from neuropa.memory import MemoryClaimService
from neuropa.providers import NoAIProviderAvailable, ProviderRouter


@pytest.fixture
def db(tmp_path: Path):
    d = Database(tmp_path / "f1.db")
    yield d
    d.close()


def test_provider_managed_fallback_and_privacy(monkeypatch):
    monkeypatch.setenv("NEUROPA_MANAGED_PROVIDER", "https://managed.invalid/v1")
    monkeypatch.setenv("NEUROPA_MANAGED_KEY", "managed")
    router = ProviderRouter()
    router.local.health = lambda: True  # type: ignore[method-assign]
    calls = []
    def fake(mode, messages, model):
        calls.append(mode)
        if mode == "managed": raise RuntimeError("down")
        return {"content": "ok", "model": model or "local", "usage": {}}
    router._call = fake  # type: ignore[method-assign]
    result = router.generate([{"role": "user", "content": "x"}])
    assert result["provider_used"] == "byok" or result["provider_used"] == "local"
    calls.clear()
    router.generate([{"role": "user", "content": "sensitive"}], privacy_sensitive=True)
    assert calls == ["local"]


def test_memory_grounding(db):
    service = MemoryClaimService(db)
    old = service.store_claim("La reunión es el lunes", "calendar", "cal-1", .6)
    new = service.store_claim("La reunión es el martes", "calendar", "cal-2", .9)
    service.supersede(old.id, new.id)
    assert service.search_claims("reunión") == [new]
    assert service.answer_with_evidence("martes")["source"] == "cal-2"
    assert service.answer_with_evidence("desconocido")["confidence"] == 0


def test_today_recovery_and_parking(db):
    from neuropa.domain.today import TodayService
    for i in range(8):
        db.create(Task(title=f"T{i}", status="pending", priority=i))
    view = TodayService(db).get_today_view()
    assert view["mit"]["title"] == "T7"
    assert len(view["parking_lot"]) == 5
    db.conn.execute("UPDATE entities SET updated_at=?", ((datetime.now(timezone.utc)-timedelta(days=5)).isoformat(),))
    db.conn.commit()
    assert TodayService(db).get_recovery_flow()["needs_recovery"] is True


def test_api_memory_today_and_focus_ws(db, tmp_path, monkeypatch):
    monkeypatch.setenv("NEUROPA_DATA_DIR", str(tmp_path / "data"))
    task = db.create(Task(title="Focus", status="pending"))
    client = TestClient(create_app(db))
    token = (tmp_path / "data" / "token").read_text()
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/today", headers=headers).status_code == 200
    stored = client.post("/api/memory/store", headers=headers, json={"claim_text":"dato verificable", "source_ref":"note-1"})
    assert stored.status_code == 201
    assert client.post("/api/memory/query", headers=headers, json={"query":"verificable"}).json()["source"] == "note-1"
    with client.websocket_connect(f"/ws/focus?token={token}") as ws:
        ws.send_json({"action":"start", "task_id":task.id, "planned_min":1})
        assert ws.receive_json()["state"] == "running"
        ws.send_json({"action":"tick"})
        assert ws.receive_json()["state"] == "running"
        ws.send_json({"action":"pause"})
        assert ws.receive_json()["state"] == "paused"
        ws.send_json({"action":"complete", "reflection":"done"})
        assert ws.receive_json()["state"] == "completed"


def test_export_import_roundtrip(db, tmp_path, monkeypatch):
    monkeypatch.setenv("NEUROPA_DATA_DIR", str(tmp_path / "data"))
    db.create(Task(title="roundtrip"))
    client = TestClient(create_app(db))
    token = (tmp_path / "data" / "token").read_text()
    headers = {"Authorization": f"Bearer {token}"}
    exported = client.get("/api/export", headers=headers).json()
    target = Database(tmp_path / "clean.db")
    target_client = TestClient(create_app(target))
    assert target_client.post("/api/import", headers=headers, json=exported).status_code == 200
    assert [x["title"] for x in target_client.get("/api/export", headers=headers).json()["task"]] == ["roundtrip"]
