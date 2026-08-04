from pathlib import Path


HTML = (Path(__file__).resolve().parents[1] / "neuropa" / "frontend" / "index.html").read_text(encoding="utf-8")


def test_session_restore_and_provider_status_revalidate_state_before_render():
    for marker in (
        "state.model=loaded.model||state.model",
        "state.contextScope=loaded.context_scope||'session'",
        "loaded.context_claim_ids",
        "revalidateModelForProvider();state.sessionRail=false",
        "state.providers=await api('/api/providers/status');revalidateModelForProvider()",
        "recommended_model",
    ):
        assert marker in HTML


def test_control_option_focus_returns_to_new_trigger_after_rerender():
    assert "const triggerId=popover?.previousElementSibling?.id" in HTML
    assert "requestAnimationFrame(()=>{const nextTrigger=triggerId&&document.getElementById(triggerId)" in HTML
    assert "nextTrigger?.focus()" in HTML


def test_supersede_uses_shared_modal_accessibility_contract():
    for marker in (
        "setModal(modal,true)",
        "closeSupersedeModal(modal)",
        "state.modal?.classList.contains('open')",
        "else closeSupersedeModal(state.modal)",
        "app.inert=true",
        "trapFocus(event,state.modal)",
    ):
        assert marker in HTML


def test_memory_graph_encodes_type_status_degree_confidence_and_accumulated_pan():
    for marker in (
        "graphNodeType(node)",
        "graphNodeColor(node)",
        "status-${status}",
        "const degree=new Map",
        "degree.get(node.id)",
        "state.graphPanX",
        "baseX+moveEvent.clientX-startX",
        "graph-edge.neighbor",
        "related.has(node.dataset.source)||related.has(node.dataset.target)",
    ):
        assert marker in HTML


def test_send_payload_contract_remains_exact():
    for marker in (
        "provider:state.provider",
        "model:state.model",
        "context_scope:state.contextScope",
        "memory_claim_ids:state.selectedMemoryClaimIds",
    ):
        assert marker in HTML
