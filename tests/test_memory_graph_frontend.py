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
