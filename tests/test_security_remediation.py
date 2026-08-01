from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from neuropa.api.app import create_app, validate_lan_cidr
from neuropa.domain import Database, Task
from neuropa.providers.opencode_cli import OpenCodeCLI
from neuropa.services import HarnessService


class Router:
    def __init__(self):
        self.calls = []

    def generate(self, messages, **kwargs):
        self.calls.append(kwargs)
        return {"text": "ok", "provider_used": "local-test", "model": "model-test", "usage": {}}


def auth_client(tmp_path, monkeypatch, router=None):
    data = tmp_path / "data"
    monkeypatch.setenv("NEUROPA_DATA_DIR", str(data))
    db = Database(tmp_path / "db.sqlite")
    client = TestClient(create_app(db, router=router))
    token = (data / "token").read_text().strip()
    return db, client, {"Authorization": f"Bearer {token}"}


def test_session_send_persists_mode_provider_model_and_local_only(tmp_path, monkeypatch):
    router = Router()
    db, client, headers = auth_client(tmp_path, monkeypatch, router)
    modes = client.get("/api/agent-modes", headers=headers).json()
    mode_id = next(mode["id"] for mode in modes if mode["slug"] == "detail")
    session = client.post("/api/sessions", headers=headers, json={"local_only": True}).json()
    response = client.post(f"/api/sessions/{session['id']}/messages", headers=headers, json={"content": "secret", "mode_id": mode_id, "provider": "local", "model": "m1"})
    assert response.status_code == 200
    stored = client.get(f"/api/sessions/{session['id']}", headers=headers).json()
    assert stored["mode_id"] == mode_id
    assert stored["provider_id"] == "local-test"
    assert stored["model"] == "model-test"
    assert router.calls[-1]["privacy_sensitive"] is True
    assert client.post(f"/api/sessions/{session['id']}/messages", headers=headers, json={"content": "x", "mode_id": "not-a-mode"}).status_code == 400
    db.close()


def test_opencode_prompt_is_stdin_and_workspace_is_outside_data_root(tmp_path, monkeypatch):
    script = tmp_path / "opencode"
    script.write_text("#!/usr/bin/env python3\nimport sys\nassert len(sys.argv) == 7, sys.argv\nassert 'TOP_SECRET' not in sys.argv\nassert 'TOP_SECRET' in sys.stdin.read()\nprint('{\\\"type\\\":\\\"text\\\",\\\"part\\\":{\\\"text\\\":\\\"OK\\\"}}')\n")
    script.chmod(0o755)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    result = OpenCodeCLI(str(script)).generate([{"role": "user", "content": "TOP_SECRET"}], workspace=workspace)
    assert result["text"] == "OK"


def test_cidr_policy():
    assert validate_lan_cidr("192.168.1.0/24").prefixlen == 24
    for value in ("0.0.0.0/0", "::/0", "8.8.8.0/24"):
        with pytest.raises(ValueError):
            validate_lan_cidr(value)


def test_pairing_is_one_time_cookie_and_token_endpoint_is_loopback_only(tmp_path, monkeypatch):
    monkeypatch.setenv("NEUROPA_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("NEUROPA_PAIRING_CODE", "pair-me")
    monkeypatch.setenv("NEUROPA_LAN_CIDR", "192.168.1.0/24")
    db = Database(tmp_path / "db.sqlite")
    client = TestClient(create_app(db), client=("192.168.1.50", 50000))
    assert client.get("/api/token").status_code == 403
    paired = client.post("/api/pair", json={"code": "pair-me"})
    assert paired.json() == {"paired": True}
    cookie = paired.headers["set-cookie"]
    assert "httponly" in cookie.lower() and "samesite=strict" in cookie.lower() and "max-age=28800" in cookie.lower()
    assert client.get("/api/sessions").status_code == 200
    assert client.post("/api/pair", json={"code": "pair-me"}).status_code == 403
    db.close()


def test_import_rejects_hostile_payload_without_deleting_existing_data(tmp_path, monkeypatch):
    db, client, headers = auth_client(tmp_path, monkeypatch)
    task = db.create(Task(title="keep"))
    before = client.get("/api/export", headers=headers).json()
    bad = {"replace": True, "entities": {"task": [{"id": "../../escape", "title": "bad"}]}}
    response = client.post("/api/import", headers=headers, json=bad)
    assert response.status_code == 400
    assert client.get("/api/export", headers=headers).json()["entities"]["task"][0]["id"] == task.id
    assert client.post("/api/import", headers=headers, json={"task": []}).status_code == 400
    db.close()


def test_artifact_filename_is_generated_and_contained(tmp_path):
    db = Database(tmp_path / "db.sqlite")
    service = HarnessService(db, Router(), tmp_path)
    session = service.create_session()
    message = db.create(__import__("neuropa.domain", fromlist=["ChatMessage"]).ChatMessage(session_id=session.id, role="assistant", content="answer"))
    artifact = service.create_artifact(message.id)
    target = (tmp_path / artifact.path).resolve()
    assert target.parent == (tmp_path / "artifacts").resolve()
    assert ".." not in artifact.path
    db.close()
