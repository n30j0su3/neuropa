from pathlib import Path


HTML = (Path(__file__).resolve().parents[1] / "neuropa" / "frontend" / "index.html").read_text(encoding="utf-8")


def test_control_dock_has_separate_accessible_controls_and_no_native_prompts():
    for marker in (
        'id="provider-control"',
        'id="model-control"',
        'id="mode-control"',
        'id="context-control"',
        'role:\'combobox\'',
        'role:\'listbox\'',
        'role:\'dialog\'',
        'aria-expanded',
        'aria-controls',
        'context_scope',
        'memory_claim_ids',
        'state.providers.modes[provider].models',
    ):
        assert marker in HTML
    assert "window.prompt(" not in HTML


def test_control_dock_supports_provider_revalidation_and_keyboard_mobile_contract():
    for marker in (
        "revalidateModelForProvider",
        "selectionPopover",
        "contextScope",
        "session_memory",
        "Escape",
        "ArrowDown",
        "ArrowUp",
        "bottom-sheet",
        "modeDescription",
    ):
        assert marker in HTML


def test_send_payload_contains_control_dock_state():
    assert "provider:state.provider" in HTML
    assert "model:state.model" in HTML
    assert "context_scope:state.contextScope" in HTML
    assert "memory_claim_ids:state.selectedMemoryClaimIds" in HTML
