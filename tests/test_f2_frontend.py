from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from neuropa.api.app import create_app
from neuropa.domain import Database


def test_root_serves_premium_spa_and_token_is_loopback_only(tmp_path, monkeypatch):
    monkeypatch.setenv("NEUROPA_DATA_DIR", str(tmp_path / "data"))
    client = TestClient(create_app(Database(tmp_path / "api.db")))

    page = client.get("/")
    assert page.status_code == 200
    assert "NeuroPA" in page.text
    assert 'id="capture-input"' in page.text
    assert "fetch('/api/token')" in page.text or 'fetch("/api/token")' in page.text

    token = client.get("/api/token")
    assert token.status_code == 200
    assert token.json()["token"] == (tmp_path / "data" / "token").read_text().strip()


def test_spa_contains_required_views_and_accessibility_contract(tmp_path, monkeypatch):
    monkeypatch.setenv("NEUROPA_DATA_DIR", str(tmp_path / "data"))
    client = TestClient(create_app(Database(tmp_path / "api.db")))
    html = client.get("/").text
    for marker in ("CAPTURE", "TODAY", "FOCUS", "MEMORY", "SETTINGS", "prefers-reduced-motion", "NeuroPA no está corriendo"):
        assert marker in html
    assert "--bg:#0f1117" in html
    assert "--accent:#40E0D0" in html
    assert "C=capturar" in html
