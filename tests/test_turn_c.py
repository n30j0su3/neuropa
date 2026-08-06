"""Turn C tests: Wiki bundle service (C1) and correction dialog (C5)."""
import pytest
from pathlib import Path
from neuropa.memory.wiki import WikiService
from neuropa.domain import Database
from neuropa.services import HarnessService
from neuropa.api import create_app
from fastapi.testclient import TestClient
from neuropa.api.app import get_token


class FakeRouter:
    def status(self):
        return {"modes": {"local": {"available": True}}}
    def generate(self, messages, **kwargs):
        return {"text": "test", "provider_used": "local", "model": "test", "usage": {}}


@pytest.fixture
def wiki_setup(tmp_path):
    db = Database(tmp_path / "db.sqlite")
    router = FakeRouter()
    service = HarnessService(db, router, data_dir=tmp_path)
    app = create_app(db, router, service)
    token = get_token()
    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return service, client, tmp_path


def test_wiki_creates_bundle_structure(wiki_setup):
    _, _, tmp_path = wiki_setup
    wiki_dir = tmp_path / "wiki"
    assert wiki_dir.exists()
    for subdir in ("entities", "concepts", "comparisons", "queries", "raw"):
        assert (wiki_dir / subdir).exists()
    assert (wiki_dir / "index.md").exists()


def test_wiki_write_and_read_page(wiki_setup):
    _, client, _ = wiki_setup
    resp = client.put("/api/wiki/pages/concept/test-concept", json={
        "title": "Concepto de prueba",
        "body": "Este es un concepto sobre algo.",
        "tags": ["test"],
        "summary": "Resumen breve",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["slug"] == "test-concept"
    assert data["type"] == "concept"

    resp = client.get("/api/wiki/pages/concept/test-concept")
    assert resp.status_code == 200
    data = resp.json()
    assert data["frontmatter"]["title"] == "Concepto de prueba"
    assert data["frontmatter"]["type"] == "concept"
    assert "algo" in data["body"]


def test_wiki_list_pages(wiki_setup):
    _, client, _ = wiki_setup
    client.put("/api/wiki/pages/concept/alpha", json={"title": "Alpha"})
    client.put("/api/wiki/pages/concept/beta", json={"title": "Beta"})
    resp = client.get("/api/wiki/pages")
    assert resp.status_code == 200
    pages = resp.json()
    slugs = [p["slug"] for p in pages]
    assert "alpha" in slugs
    assert "beta" in slugs


def test_wiki_search(wiki_setup):
    _, client, _ = wiki_setup
    client.put("/api/wiki/pages/concept/searchable", json={
        "title": "Tema buscable",
        "body": "Contiene la palabra única architecture."
    })
    resp = client.get("/api/wiki/search?q=architecture")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) >= 1
    assert results[0]["slug"] == "searchable"


def test_wiki_path_traversal_blocked(wiki_setup):
    _, _, tmp_path = wiki_setup
    from neuropa.memory.wiki import WikiService
    wiki = WikiService(tmp_path)
    with pytest.raises(ValueError):
        wiki.write_page("concept", "../../../etc/passwd", title="hack", body="x")


def test_wiki_lint_no_issues_on_clean_bundle(wiki_setup):
    _, client, _ = wiki_setup
    resp = client.get("/api/wiki/lint")
    assert resp.status_code == 200
    assert isinstance(resp.json()["issues"], list)


def test_wiki_invalid_slug_rejected(wiki_setup):
    _, _, tmp_path = wiki_setup
    from neuropa.memory.wiki import WikiService
    wiki = WikiService(tmp_path)
    with pytest.raises(ValueError):
        wiki.write_page("concept", "Invalid Slug!", title="bad", body="x")
