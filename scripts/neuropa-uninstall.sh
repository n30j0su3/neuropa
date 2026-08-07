#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════
#  NeuroPA · Desinstalador (preserva tus datos)
#  - Borra repo, dependencias Python y OpenCode
#  - PRESERVA: ~/.local/share/neuropa/ (memoria, skills, identidad)
# ════════════════════════════════════════════════════════════════

ROOTDIR="$HOME/neuropa"
DATA="$HOME/.local/share/neuropa"

echo ""
echo "  ╔════════════════════════════════════════════════════════════╗"
echo "  ║  Desinstalador NeuroPA                                  ║"
echo "  ╚════════════════════════════════════════════════════════════╝"
echo ""
echo "  Se eliminará:"
echo "    - Repositorio:       $ROOTDIR"
echo "    - Dependencias (uv):  cache local"
echo "    - OpenCode CLI:       uninstall global npm"
echo ""
echo "  Se CONSERVARÁ:"
echo "    - Tus datos:          $DATA"
echo ""
echo "  Tus datos (memoria, skills, identidad) NO se tocan."
echo ""
read -p "Continuar? [S/n]: " CONFIRM
if [[ "$CONFIRM" != [sSyY]* ]] && [[ -n "$CONFIRM" ]]; then
    echo "Cancelado."
    exit 0
fi

# 1. Borrar repo
if [ -d "$ROOTDIR" ]; then
    echo ""
    echo "  [1/3] Borrando repositorio $ROOTDIR..."
    rm -rf "$ROOTDIR"
    echo "        OK."
fi

# 2. Limpiar cache uv
echo ""
echo "  [2/3] Limpiando cache de dependencias uv..."
if command -v uv >/dev/null 2>&1; then
    uv cache clean 2>/dev/null
fi
echo "        OK."

# 3. Desinstalar OpenCode CLI
echo ""
echo "  [3/3] Desinstalando OpenCode CLI..."
if command -v npm >/dev/null 2>&1; then
    npm uninstall -g opencode-ai 2>/dev/null
    echo "        OK."
else
    echo "        npm no encontrado, omitido."
fi

echo ""
echo "  ╔════════════════════════════════════════════════════════════╗"
echo "  ║  ✓ NeuroPA desinstalado.                               ║"
echo "  ║                                                          ║"
echo "  ║  Tus datos siguen en:                                    ║"
echo "  ║    $DATA"
echo "  ║                                                          ║"
echo "  ║  Para borrarlos tambien:                                 ║"
echo "  ║    rm -rf \"$DATA\""
echo "  ╚════════════════════════════════════════════════════════════╝"
echo ""
read -p "Enter para cerrar..."
