#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════
#  NeuroPA · Lanzador fácil para macOS / Linux
#  Doble-click → arranca NeuroPA en tu navegador
# ════════════════════════════════════════════════════════════════

# Localiza el repo
ROOTDIR="$(cd "$(dirname "$0")/.." && pwd)"
if [ ! -f "$ROOTDIR/pyproject.toml" ]; then
    ROOTDIR="$HOME/neuropa"
fi
if [ ! -f "$ROOTDIR/pyproject.toml" ]; then
    echo ""
    echo "  ╔════════════════════════════════════════════════════╗"
    echo "  ║  No encuentro NeuroPA.                             ║"
    echo "  ║  Ejecuta primero el instalador:                    ║"
    echo "  ║  curl -fsSL https://n30j0su3.github.io/neuropa/install.sh | bash"
    echo "  ╚════════════════════════════════════════════════════╝"
    echo ""
    read -p "Enter para cerrar..."
    exit 1
fi

echo ""
echo "  ▶ Iniciando NeuroPA..."
echo ""

cd "$ROOTDIR"

# Abre el navegador tras 3 segundos (en macOS usa 'open', en Linux 'xdg-open')
(sleep 3 && (open "http://127.0.0.1:8474" 2>/dev/null || xdg-open "http://127.0.0.1:8474" 2>/dev/null)) &

# Arranca el servidor. Ctrl+C para detener.
uv run neuropa --port 8474
