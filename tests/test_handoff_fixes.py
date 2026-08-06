"""Handoff fix tests: B1 (secret redaction), B2 (profile fallback), H1-H3 (Wiki improvements)."""
import pytest
from pathlib import Path
from neuropa.domain import Database, Workspace, AgentMode, ChatMessage
from neuropa.services import HarnessService
from neuropa.memory.wiki import WikiService
from neuropa.providers import ProviderRouter
from neuropa.api import create_app
from neuropa.api.app import get_token
from fastapi.testclient import TestClient

HTML = (Path(__file__).parents[1] / "neuropa" / "frontend" / "index.html").read_text()


class CapturingRouter:
    """Router that captures the mode kwarg for assertion."""
    def __init__(self):
        self.captured_mode = None
        self.captured_messages = []
    def status(self):
        return {"modes": {"test_provider": {"available": True}, "profile-provider": {"available": True}}}
    def generate(self, messages, **kwargs):
        self.captured_mode = kwargs.get("mode")
        self.captured_messages = messages
        return {"text": "ok", "provider_used": kwargs.get("mode"), "model": kwargs.get("model"), "usage": {}}


@pytest.fixture
def setup(tmp_path):
    db = Database(tmp_path / "db.sqlite")
    router = CapturingRouter()
    svc = HarnessService(db, router, data_dir=tmp_path)
    app = create_app(db, router, svc)
    token = get_token()
    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return svc, client, db, router, tmp_path


# ── B1: Secret redaction in selective export ──

def test_b1_export_redacts_api_key_in_settings(setup):
    svc, client, db, _, _ = setup
    ws = svc.default_workspace()
    db.update(ws, settings={"api_key": "LEAK-ME", "name": "safe-value"})
    resp = client.post("/api/export/selected", json={"sections": ["workspace"]})
    assert resp.status_code == 200
    data = resp.json()
    ws_data = data["entities"]["workspace"][0]
    assert ws_data["settings"]["api_key"] == "[REDACTED]"
    assert ws_data["settings"]["name"] == "safe-value"
    assert "settings.api_key" in data["redacted_keys"]


def test_b1_export_redacts_nested_secrets(setup):
    svc, client, db, _, _ = setup
    ws = svc.default_workspace()
    db.update(ws, settings={"nested": {"token": "secret-val", "safe": "ok"}})
    resp = client.post("/api/export/selected", json={"sections": ["workspace"]})
    data = resp.json()
    ws_data = data["entities"]["workspace"][0]
    assert ws_data["settings"]["nested"]["token"] == "[REDACTED]"
    assert ws_data["settings"]["nested"]["safe"] == "ok"
    assert any("token" in k for k in data["redacted_keys"])


def test_b1_export_hashes_are_on_redacted_data(setup):
    svc, client, db, _, _ = setup
    ws = svc.default_workspace()
    db.update(ws, settings={"secret": "SENSITIVE"})
    resp = client.post("/api/export/selected", json={"sections": ["workspace"]})
    data = resp.json()
    content = __import__("json").dumps(data["entities"]["workspace"], ensure_ascii=False, sort_keys=True)
    expected_hash = __import__("hashlib").sha256(content.encode()).hexdigest()
    assert data["file_hashes"]["workspace"] == expected_hash


# ── B2: AgentProfile governs provider/mode ──

def test_b2_profile_default_provider_used_in_session(setup):
    svc, client, db, router, _ = setup
    p = svc.primary_profile()
    svc.update_profile(p.id, default_provider="profile-provider")
    session = svc.create_session()
    assert session.provider_id == "profile-provider"


def test_b2_profile_provider_used_in_send_message(setup):
    svc, client, db, router, _ = setup
    p = svc.primary_profile()
    svc.update_profile(p.id, default_provider="profile-provider")
    session = svc.create_session()
    svc.send_message(session.id, "hola", model="m")
    assert router.captured_mode == "profile-provider"


def test_b2_explicit_provider_overrides_profile(setup):
    svc, client, db, router, _ = setup
    p = svc.primary_profile()
    svc.update_profile(p.id, default_provider="profile-provider")
    session = svc.create_session()
    svc.send_message(session.id, "hola", provider="test_provider", model="m")
    assert router.captured_mode == "test_provider"


def test_b2_session_context_always_ends_with_current_user_message(setup):
    svc, _, _, router, _ = setup
    session = svc.create_session()
    svc.send_message(session.id, "primera pregunta", context_scope="session")
    svc.send_message(session.id, "pregunta actual", context_scope="session")

    assert router.captured_messages[-1] == {"role": "user", "content": "pregunta actual"}
    assert [m["content"] for m in router.captured_messages if m["role"] == "user"] == ["primera pregunta", "pregunta actual"]


def test_b2_failed_messages_are_not_sent_back_as_context(setup):
    svc, _, db, router, _ = setup
    session = svc.create_session()
    db.create(ChatMessage(session_id=session.id, role="user", content="mensaje fallido anterior", status="failed"))

    svc.send_message(session.id, "mensaje válido actual", context_scope="session")

    contents = [m["content"] for m in router.captured_messages]
    assert "mensaje fallido anterior" not in contents
    assert contents[-1] == "mensaje válido actual"


def test_b2_mode_modifies_style_without_replacing_literal_request(setup):
    svc, _, _, router, _ = setup
    session = svc.create_session()

    svc.send_message(session.id, "¿Sirve esta GPU para IA local?", context_scope="session")

    assert "responde primero a la solicitud literal" in router.captured_messages[0]["content"].lower()


def test_b2_profile_mode_id_used_in_create_session(setup):
    svc, client, db, _, _ = setup
    # Create a custom mode
    modes = db.list("agent_mode")
    custom_mode = modes[0]
    p = svc.primary_profile()
    svc.update_profile(p.id, default_mode_id=custom_mode.id)
    session = svc.create_session()
    assert session.mode_id == custom_mode.id


def test_b2_profile_provider_validates_model_catalog(setup):
    svc, _, _, router, _ = setup
    router.status = lambda: {"modes": {"profile-provider": {"catalog_known": True, "models": ["allowed"]}}}
    profile = svc.primary_profile()
    svc.update_profile(profile.id, default_provider="profile-provider")
    session = svc.create_session()
    with pytest.raises(ValueError, match="catálogo"):
        svc.send_message(session.id, "hola", model="not-allowed")


# ── B3: N30-approved mobile composer ──

def test_b3_mobile_composer_uses_approved_two_state_contract():
    assert "composerRetracted:false" in HTML
    assert "class:`composer${state.composerRetracted?' retracted':''}`" in HTML
    assert "class:'composer-collapse'" in HTML
    assert "class:'composer-row'" in HTML
    assert "class:'composer-input-shell'" in HTML
    assert "class:'dock-settings-icon'" in HTML
    assert "class:'send-btn'" in HTML
    assert "aria-label':'Enviar mensaje'" in HTML


def test_b3_composer_autogrows_and_caps_mobile_height():
    assert "function resizeComposerInput(input)" in HTML
    assert "input.style.height='44px'" in HTML
    assert "window.matchMedia('(max-width: 700px)').matches?132:180" in HTML
    assert "input.scrollHeight>cap?'auto':'hidden'" in HTML


def test_b3_desktop_uses_same_two_state_composer_contract():
    shared = HTML.split("/* N30-approved Composer B", 1)[1].split("@media(max-width:700px)", 1)[0]
    assert ".composer-collapse{position:absolute" in shared
    assert ".composer-collapse{display:none}" not in shared
    assert ".dock-toggle{display:flex" in shared
    assert ".control-dock{display:none" in shared
    assert ".control-dock.expanded{display:grid" in shared


# ── B4: Agent modes are user-customizable ──

def test_b4_agent_modes_support_create_update_and_delete(setup):
    _, client, _, _, _ = setup
    created = client.post("/api/agent-modes", json={
        "name": "Analista",
        "slug": "analyst",
        "description": "Prioriza evidencia.",
        "system_prompt": "Analiza sin sustituir la solicitud literal.",
        "temperature": 0.2,
    })
    assert created.status_code == 201
    mode = created.json()
    updated = client.patch(f"/api/agent-modes/{mode['id']}", json={"name": "Analista riguroso", "enabled": False})
    assert updated.status_code == 200
    assert updated.json()["name"] == "Analista riguroso"
    assert updated.json()["enabled"] is False
    assert client.delete(f"/api/agent-modes/{mode['id']}").status_code == 200
    assert mode["id"] not in {item["id"] for item in client.get("/api/agent-modes").json()}


def test_b4_settings_exposes_agent_mode_editor():
    assert "id:'agent-mode-settings'" in HTML
    assert "function modeSettingsForm(" in HTML
    assert "async function saveAgentMode(" in HTML
    assert "'/api/agent-modes'" in HTML


def test_b4_database_lists_are_safe_under_parallel_settings_load(setup):
    from concurrent.futures import ThreadPoolExecutor

    _, _, db, _, _ = setup
    db.create(AgentMode(name="Paralelo", slug="parallel"))

    entity_types = ["agent_mode", "workspace", "skill", "mcp_server"] * 100
    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(db.list, entity_types))

    assert all(isinstance(items, list) for items in results)


def test_b5_session_export_offers_offline_html_markdown_and_json():
    assert "Exportar HTML offline" in HTML
    assert "Exportar Markdown" in HTML
    assert "Exportar JSON" in HTML
    assert "function sessionExportHtml" in HTML
    assert "function sessionExportMarkdown" in HTML
    assert "neuropa-session-search" in HTML


def test_b5_settings_exposes_confirmed_json_import():
    assert "Importar backup JSON" in HTML
    assert "id:'workspace-import-file'" in HTML
    assert "function importDataFile" in HTML
    assert "'/api/import'" in HTML


def test_b6_openrouter_byok_prioritizes_free_models(monkeypatch):
    class Offline:
        def health(self): return False
        def list_models(self): return []

    monkeypatch.setenv("NEUROPA_BYOK_KEY", "secret")
    monkeypatch.delenv("NEUROPA_BYOK_PROVIDER", raising=False)
    router = ProviderRouter(ollama=Offline(), opencode=Offline())
    monkeypatch.setattr(router, "_openrouter_catalog", lambda: ["vendor/paid", "vendor/free:free"])

    byok = router.status()["modes"]["byok"]

    assert router.byok_provider == "https://openrouter.ai/api/v1"
    assert byok["models"] == ["vendor/free:free", "vendor/paid"]
    assert byok["recommended_model"] == "vendor/free:free"
    assert "OpenRouter" in byok["description"]


def test_b7_multiplatform_distribution_surfaces_exist():
    root = Path(__file__).parents[1]
    assert (root / "scripts" / "install.ps1").is_file()
    assert (root / "scripts" / "run-neuropa.ps1").is_file()
    assert (root / "Dockerfile").is_file()
    assert (root / "compose.yaml").is_file()
    setup = (root / "docs" / "SETUP.md").read_text()
    for platform in ("Windows PowerShell", "macOS", "Docker", "Android / Termux", "SPA-HTML offline"):
        assert platform in setup


def test_b8_identity_layers_persist_to_soul_and_agents_markdown(setup):
    svc, client, _, router, root = setup
    response = client.put("/api/identity", json={
        "soul_md": "# Soul\nSereno y transparente.",
        "agents_md": "# Agents\nPrioriza evidencia verificable.",
    })
    assert response.status_code == 200
    assert (root / "identity" / "SOUL.md").read_text() == "# Soul\nSereno y transparente.\n"
    assert (root / "identity" / "AGENTS.md").read_text() == "# Agents\nPrioriza evidencia verificable.\n"

    session = svc.create_session(provider_id="test_provider")
    svc.send_message(session.id, "Solicitud literal actual", provider="test_provider")
    prompt = router.captured_messages[0]["content"]
    assert "Sereno y transparente" in prompt
    assert "Prioriza evidencia verificable" in prompt
    assert router.captured_messages[-1] == {"role": "user", "content": "Solicitud literal actual"}
    assert "La solicitud literal actual del usuario tiene prioridad" in prompt


def test_b8_settings_exposes_identity_layer_editor():
    assert "Capas permanentes" in HTML
    assert "id:'identity-soul'" in HTML
    assert "id:'identity-agents'" in HTML
    assert "function saveIdentity" in HTML
    assert "'/api/identity'" in HTML


def test_b8_full_backup_roundtrips_identity_layers(setup):
    svc, client, _, _, _ = setup
    svc.update_identity(soul_md="# Soul\nOriginal", agents_md="# Agents\nOriginal")
    exported = client.get("/api/export").json()
    assert exported["identity"]["soul_md"].startswith("# Soul")

    svc.update_identity(soul_md="# Soul\nChanged", agents_md="# Agents\nChanged")
    response = client.post("/api/import", json=exported)
    assert response.status_code == 200
    assert svc.identity_docs() == exported["identity"]


def test_b8_invalid_identity_backup_is_rejected_without_mutation(setup):
    svc, client, _, _, _ = setup
    before = svc.identity_docs()
    exported = client.get("/api/export").json()
    exported["identity"] = {"soul_md": "", "agents_md": "valid"}
    response = client.post("/api/import", json=exported)
    assert response.status_code == 400
    assert svc.identity_docs() == before


# ── H1: Wiki backlinks ──

def test_h1_backlinks_derived_from_related_concepts(setup):
    _, _, _, _, tmp_path = setup
    wiki = WikiService(tmp_path / "wiki-test")
    wiki.write_page("concept", "alpha", title="Alpha", body="A concept", related_concepts=["beta"])
    wiki.write_page("concept", "beta", title="Beta", body="B concept")
    bl = wiki.backlinks()
    # backlinks maps target -> list of pages that reference it
    assert bl.get("beta") == ["alpha"]


# ── H2: Lint reports unreadable pages ──

def test_h2_lint_reports_invalid_frontmatter(setup):
    _, _, _, _, tmp_path = setup
    wiki = WikiService(tmp_path / "wiki-test2")
    # Write a valid page
    wiki.write_page("concept", "good", title="Good", body="OK")
    # Write a corrupt page directly
    bad = wiki.bundle_root / "concepts" / "bad.md"
    bad.write_text("---\ntitle: Bad\ntype: invalid_type\n---\n\nBad page\n")
    issues = wiki.lint()
    issue_pages = [i["page"] for i in issues]
    assert "bad" in issue_pages


def test_h2_lint_reports_type_mismatch(setup):
    _, _, _, _, tmp_path = setup
    wiki = WikiService(tmp_path / "wiki-test3")
    # Write page in concepts/ but with type=entity in frontmatter
    target = wiki.bundle_root / "concepts" / "mismatch.md"
    target.write_text("---\ntitle: Mismatch\ntype: entity\n---\n\nMismatched\n")
    issues = wiki.lint()
    mismatch_issues = [i for i in issues if i.get("issue") == "type_mismatch"]
    assert len(mismatch_issues) >= 1
    assert mismatch_issues[0]["page"] == "mismatch"


# ── H3: Wiki contract — type validation ──

def test_h3_list_pages_rejects_invalid_type(setup):
    _, _, _, _, tmp_path = setup
    wiki = WikiService(tmp_path / "wiki-test4")
    with pytest.raises(ValueError, match="tipo inválido"):
        wiki.list_pages("invalid_type")


def test_h3_read_page_rejects_type_mismatch(setup):
    _, _, _, _, tmp_path = setup
    wiki = WikiService(tmp_path / "wiki-test5")
    # Write a page in entities/ but with frontmatter type=concept
    target = wiki.bundle_root / "entities" / "mismatch-page.md"
    target.write_text("---\ntitle: Mismatch\ntype: concept\n---\n\nMismatched\n")
    with pytest.raises(ValueError, match="no coincide"):
        wiki.read_page("entity", "mismatch-page")


def test_h3_all_page_types_are_listed_and_backlinked(setup):
    _, _, _, _, tmp_path = setup
    wiki = WikiService(tmp_path / "wiki-all-types")
    wiki.write_page("concept", "target", title="Target", body="OK")
    for page_type in ("entity", "query", "note"):
        wiki.write_page(page_type, f"{page_type}-source", title=page_type, body="OK", related_concepts=["target"])
    listed = {(page["type"], page["slug"]) for page in wiki.list_pages()}
    assert ("entity", "entity-source") in listed
    assert ("query", "query-source") in listed
    assert ("note", "note-source") in listed
    assert wiki.backlinks()["target"] == ["entity-source", "query-source", "note-source"]


def test_h2_lint_reports_malformed_yaml_without_crashing(setup):
    _, _, _, _, tmp_path = setup
    wiki = WikiService(tmp_path / "wiki-malformed")
    bad = wiki.bundle_root / "concepts" / "malformed.md"
    bad.write_text("---\ntitle: [unterminated\ntype: concept\n---\nbody\n")
    issues = wiki.lint()
    assert any(issue["page"] == "malformed" and issue["issue"] == "invalid_frontmatter" for issue in issues)
