from pathlib import Path


HTML = (Path(__file__).resolve().parents[1] / "neuropa" / "frontend" / "index.html").read_text(encoding="utf-8")


def test_memory_graph_contract_uses_native_svg_and_real_api():
    for marker in (
        "/api/memory/graph",
        "<svg",
        "memory-graph-canvas",
        "aria-label",
        "graph-query",
        "graph-source",
        "graph-status",
        "graph-confidence",
        "requestAnimationFrame",
        "resetGraphCamera",
        "neighbor",
    ):
        assert marker in HTML
    assert "innerHTML" not in HTML


def test_memory_graph_has_accessible_inspector_and_context_management():
    for marker in (
        "memory-inspector",
        "source_ref",
        "confidence",
        "created_at",
        "status",
        "Usar como contexto",
        "Corregir memoria",
        "confirm",
        "supersede",
        "memory-graph-list",
        "prefers-reduced-motion",
        "mobile-tabs",
    ):
        assert marker in HTML


def test_memory_graph_refetches_after_confirmed_supersession():
    assert "fetchMemoryGraph" in HTML
    assert "renderMemoryGraph" in HTML
    assert "supersedeClaim" in HTML
    assert "fetchMemoryGraph()" in HTML


def test_memory_graph_uses_svg_namespace_factory():
    """G1 RED: renderMemoryGraph must use createElementNS for SVG elements."""
    assert "http://www.w3.org/2000/svg" in HTML
    assert "createElementNS" in HTML
    assert "makeSvg" in HTML
    # SVG elements must not be built through the HTML make() helper
    graph_start = HTML.index("function renderMemoryGraph")
    graph_end = HTML.index("function highlightNeighborhood")
    graph_body = HTML[graph_start:graph_end]
    # svg, g, line, circle, text must come from makeSvg, not make
    for svg_tag in ("svg", "circle", "line", "text"):
        # Assert the tag appears in a makeSvg call somewhere in the graph body
        assert f"makeSvg('{svg_tag}'" in graph_body or f'makeSvg("{svg_tag}"' in graph_body, (
            f"SVG tag '{svg_tag}' must be created via makeSvg in renderMemoryGraph"
        )


def test_memory_graph_human_language():
    """G1 RED: graph labels must use plain Spanish, not implementation vocabulary."""
    assert "Memoria conectada" in HTML or "memoria conectada" in HTML.lower()
    assert "De dónde viene" in HTML or "De dónde viene" in HTML
    assert "Centrar grafo" in HTML or "centrar grafo" in HTML.lower()


def test_correction_dialog_uses_user_facing_language():
    """C5 RED: correction dialog must not expose 'claim' or 'supersede' jargon."""
    # Find the modal function body
    start = HTML.index("function openSupersedeModal")
    end = HTML.index("function closeSupersedeModal")
    modal_body = HTML[start:end]
    # Primary action must be user-facing
    assert "Guardar corrección" in modal_body
    assert "Confirmar supersede" not in modal_body
    # Must show current memory alongside new input
    assert "Memoria actual" in modal_body
    assert "supersede-columns" in modal_body
    # Labels must be visible, not just aria-labels
    assert "Nueva afirmación" in modal_body
    # Should use 'dato original', not 'claim original'
    assert "claim original" not in modal_body.lower()
