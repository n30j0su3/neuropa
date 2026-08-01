from pathlib import Path


HTML = (Path(__file__).resolve().parents[1] / "neuropa" / "frontend" / "index.html").read_text(encoding="utf-8")


def test_harness_shell_has_real_navigation_and_workspace_contract():
    required = (
        'data-view="workspace"',
        'data-view="executive"',
        'data-view="projects"',
        'data-view="research"',
        'data-view="memory"',
        'data-view="artifacts"',
        'data-view="skills"',
        'data-view="calendar"',
        'data-view="settings"',
        'id="session-list"',
        'id="composer-input"',
        'id="model-chip"',
        'id="mode-chip"',
        'id="context-chip"',
        'id="artifact-canvas"',
        'id="setup-wizard"',
        'id="command-palette"',
    )
    for marker in required:
        assert marker in HTML


def test_harness_uses_real_api_endpoints_and_safe_runtime_behaviors():
    for endpoint in (
        "/api/token",
        "/api/setup/detect",
        "/api/providers/status",
        "/api/workspaces",
        "/api/sessions",
        "/api/agent-modes",
        "/api/tools",
        "/api/artifacts",
        "/api/messages/",
        "/api/memory/query",
        "/api/memory/store",
        "/api/today",
        "/api/export",
    ):
        assert endpoint in HTML
    assert "AbortController" in HTML
    assert "localStorage" in HTML
    assert "wizard_done" in HTML
    assert "textContent" in HTML
    assert "innerHTML" not in HTML


def test_harness_is_standalone_and_honest_about_roadmap():
    assert "https://" not in HTML
    assert "http://" not in HTML
    assert "Roadmap" in HTML
    assert "OpenCode" in HTML
    assert "Ollama" in HTML
    assert "BYOK" in HTML
    assert "prefers-reduced-motion" in HTML
    assert "Ctrl/Cmd+K" in HTML
    assert "No se expone chain-of-thought" in HTML
