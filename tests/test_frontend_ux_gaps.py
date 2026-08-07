from pathlib import Path


HTML = (Path(__file__).resolve().parents[1] / "neuropa" / "frontend" / "index.html").read_text(encoding="utf-8")


def test_session_restore_and_provider_status_revalidate_state_before_render():
    for marker in (
        "state.model=loaded.model||state.model",
        "state.contextScope=loaded.context_scope||'session'",
        "loaded.context_claim_ids",
        "revalidateModelForProvider();state.sessionRail=false",
        "state.providers=await api('/api/providers/status')",
        "recommended_model",
    ):
        assert marker in HTML


def test_control_option_focus_returns_to_new_trigger_after_rerender():
    assert "state.openControlId=id" in HTML
    assert "state.openPopover=pop" in HTML
    assert "const triggerId=state.openControlId" in HTML
    assert "requestAnimationFrame(()=>{const nextTrigger=triggerId&&document.getElementById(triggerId);nextTrigger?.focus()})" in HTML


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


def test_public_target_labels_and_mobile_origin_contract():
    for marker in (
        "['artifacts','Guardados / Artifacts','A']",
        "text:'Origen'",
        "text:'De dónde viene'",
        "renderModule('Memoria conectada'",
        "text:'Estado'",
        "text:'Confianza'",
        "classList.add('inspector-open')",
        "if(event.target.closest?.('.graph-node'))return",
        "shortGraphLabel",
    ):
        assert marker in HTML
    for leaked in ("text:'Inspector'", "text:'Source'", "text:'Status'", "text:'Confidence'", "text:'Evidence inspector'"):
        assert leaked not in HTML


def test_onboarding_and_settings_use_progressive_human_disclosure():
    for marker in (
        "Usar IA gratuita",
        "Mantener todo en este dispositivo",
        "Conectar otro servicio",
        "id:'provider-settings'",
        "id:'provider-technical-settings'",
        "text:'Detalles técnicos'",
    ):
        assert marker in HTML
    settings_start = HTML.index("function renderSettings")
    settings_end = HTML.index("async function saveCapture", settings_start)
    settings = HTML[settings_start:settings_end]
    assert "value.models" in settings
    assert "provider-technical-settings" in settings


def test_session_title_refresh_waits_for_fresh_sessions():
    send_start = HTML.index("async function sendMessage")
    send_end = HTML.index("async function setupDetect", send_start)
    send = HTML[send_start:send_end]
    assert "await loadSessions()" in send
    assert send.index("await loadSessions()") < send.index("updatedSession")
    assert "state.currentSession={...state.currentSession,title:updatedSession.title}" in send
    create_start = HTML.index("async function createSession")
    create_end = HTML.index("async function loadSessions", create_start)
    assert "state.sessionRail=false;shell();$('composer-input')?.focus()" in HTML[create_start:create_end]


def test_saved_results_use_safe_text_and_human_metadata():
    for marker in (
        "function humanArtifactTitle",
        "function artifactChecksum",
        "source_session",
        "text:'Guardados'",
        "textContent",
    ):
        assert marker in HTML
    assert "innerHTML" not in HTML


def test_primary_rail_toggle_is_persistent_and_a11y_labeled():
    assert "state.primaryRail" in HTML
    assert "localStorage.getItem('primaryRail')" in HTML
    assert "togglePrimaryRail" in HTML
    assert "rail-toggle" in HTML
    assert "aria-pressed" in HTML
    assert "state.primaryRail?'Ocultar barra lateral':'Mostrar barra lateral'" in HTML


def test_session_transcript_export_is_session_scoped_no_artifact_mutation_marker():
    assert "function exportCurrentSessionTranscript" in HTML
    assert "api(`/api/sessions/${encodeURIComponent(state.currentSession.id)}`" in HTML
    assert "toast('Transcripción exportada sin crear artifact.')" in HTML
    assert "function saveArtifact(messageId)" in HTML


def test_composer_exposes_processing_status_and_usage_metrics_summary():
    assert "startProcessingTicker" in HTML
    assert "processing-status" in HTML
    assert "formatDurationMs" in HTML
    assert "assistantUsageSummary" in HTML
    assert "No reportado" in HTML or "contextLabel" in HTML
