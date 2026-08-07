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
echo "  Tus datos (memoria, skills, identidad) NO se tocan."
echo "  Si tambien quieres borrarlos, elige la opcion al final."
echo ""

echo "  Que quieres desinstalar?"
echo ""
echo "    [1] Solo NeuroPA  (repo + cache uv)         [RECOMENDADO]"
echo "    [2] NeuroPA + OpenCode (IA gratuita via npm)"
echo "    [3] Todo lo de arriba + Node.js"
echo "    [4] TODO + uv + Python (desinstalacion completa)"
echo "    [5] Cancelar"
echo ""
read -p "  Elige opcion (1-5): " OPT

if [[ "$OPT" == "5" || -z "$OPT" ]]; then
    echo "Cancelado."
    exit 0
fi

# ── 1. Borrar repo ───────────────────────────────────────────────
echo ""
if [ -d "$ROOTDIR" ]; then
    echo "  [1] Borrando repositorio $ROOTDIR..."
    rm -rf "$ROOTDIR"
    echo "        OK."
else
    echo "  [1] Repositorio no encontrado ($ROOTDIR) - omitido."
fi

# ── 2. Limpiar cache uv ─────────────────────────────────────────
echo ""
echo "  [2] Limpiando cache de dependencias uv..."
if command -v uv >/dev/null 2>&1; then
    uv cache clean 2>/dev/null
fi
echo "        OK."

# ── 3. OpenCode ─────────────────────────────────────────────────
if [[ "$OPT" == "2" || "$OPT" == "3" || "$OPT" == "4" ]]; then
    echo ""
    echo "  [3] Desinstalando OpenCode CLI..."
    if command -v npm >/dev/null 2>&1; then
        npm uninstall -g opencode-ai 2>/dev/null
        echo "        OK."
    else
        echo "        npm no encontrado, omitido."
    fi
else
    echo ""
    echo "  [3] OpenCode omitido (opcion $OPT)."
fi

# ── 4. Node.js ───────────────────────────────────────────────────
if [[ "$OPT" == "3" || "$OPT" == "4" ]]; then
    echo ""
    echo "  [4] Desinstalando Node.js..."
    echo "        ADVERTENCIA: esto afecta todo tu sistema, no solo NeuroPA."
    if command -v brew >/dev/null 2>&1; then
        read -p "        Confirmar desinstalacion via brew? (s/N): " YN
        if [[ "$YN" == "s" || "$YN" == "S" ]]; then
            brew uninstall node 2>/dev/null
            echo "        OK."
        else
            echo "        Omitido."
        fi
    elif command -v apt >/dev/null 2>&1; then
        read -p "        Confirmar desinstalacion via apt? (s/N): " YN
        if [[ "$YN" == "s" || "$YN" == "S" ]]; then
            sudo apt remove -y nodejs npm 2>/dev/null
            echo "        OK."
        else
            echo "        Omitido."
        fi
    else
        echo "        Gestor de paquetes no detectado. Desinstala Node.js manualmente."
    fi
else
    echo ""
    echo "  [4] Node.js omitido (opcion $OPT)."
fi

# ── 5. uv + Python ──────────────────────────────────────────────
if [[ "$OPT" == "4" ]]; then
    echo ""
    echo "  [5a] Desinstalando uv..."
    if command -v uv >/dev/null 2>&1; then
        read -p "        Confirmar desinstalacion de uv? (s/N): " YN
        if [[ "$YN" == "s" || "$YN" == "S" ]]; then
            if command -v brew >/dev/null 2>&1; then
                brew uninstall uv 2>/dev/null
            elif command -v apt >/dev/null 2>&1; then
                sudo apt remove -y uv 2>/dev/null
            else
                echo "        Gestor de paquetes no detectado. Desinstala uv manualmente."
            fi
            echo "         OK."
        else
            echo "         Omitido."
        fi
    else
        echo "        uv no instalado, omitido."
    fi
    echo ""
    echo "  [5b] ADVERTENCIA sobre Python:"
    echo "        Desinstalar Python puede romper otras apps. Recomendamos dejarlo."
    echo "        Para desinstalar manualmente usa tu gestor de paquetes."
else
    echo ""
    echo "  [5] uv/Python omitido (opcion $OPT)."
fi

# ── 6. Datos del usuario ────────────────────────────────────────
echo ""
echo "  ╔════════════════════════════════════════════════════════════╗"
echo "  ║  Desinstalacion de app terminada.                        ║"
echo "  ╚════════════════════════════════════════════════════════════╝"
echo ""
echo "  Tus datos siguen en:"
echo "    $DATA"
echo ""
read -p "  Quieres borrar TAMBIEN tus datos (memoria, skills, identidad)? (s/N): " ERASE
if [[ "$ERASE" == "s" || "$ERASE" == "S" ]]; then
    if [ -d "$DATA" ]; then
        rm -rf "$DATA"
        echo "  Datos borrados."
    else
        echo "  No hay carpeta de datos."
    fi
else
    echo "  Datos preservados en: $DATA"
    echo "  Para borrarlos despues: rm -rf \"$DATA\""
fi

echo ""
echo "  Variable NEUROPA_OPENCODE_BIN (si fue creada por el installer):"
if [[ -n "${NEUROPA_OPENCODE_BIN:-}" ]]; then
    read -p "  Eliminarla tambien? (s/N): " RMENV
    if [[ "$RMENV" == "s" || "$RMENV" == "S" ]]; then
        unset NEUROPA_OPENCODE_BIN
        # Tambien intentar removerla de archivos de perfil
        for f in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
            [ -f "$f" ] && sed -i.bak '/^export NEUROPA_OPENCODE_BIN=/d' "$f" 2>/dev/null
        done
        echo "  Variable eliminada de esta sesion y archivos de perfil."
    fi
else
    echo "  No establecida."
fi

echo ""
echo "  ✓ Listo."
echo ""
read -p "Enter para cerrar..."
