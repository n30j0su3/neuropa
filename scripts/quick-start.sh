#!/usr/bin/env bash
set -euo pipefail

# ═══════════════════════════════════════════════════════════════════
# NeuroPA — Instalador de 1 comando para macOS y Linux
# Revisa lo que tienes, instala lo que falta (con tu permiso) y arranca.
# Uso:  curl -fsSL https://raw.githubusercontent.com/n30j0su3/neuropa/main/scripts/quick-start.sh | bash
#   o:  bash scripts/quick-start.sh
# ═══════════════════════════════════════════════════════════════════

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." 2>/dev/null && pwd -P || pwd)"
OS="$(uname -s)"
ARCH="$(uname -m)"
NEUROPA_CLONE=""

# ── Colors ──
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ok()    { printf "${GREEN}✓${NC} %s\n" "$1"; }
info()  { printf "${CYAN}→${NC} %s\n" "$1"; }
warn()  { printf "${YELLOW}⚠${NC} %s\n" "$1"; }
fail()  { printf "${RED}✗${NC} %s\n" "$1"; }
has()   { command -v "$1" >/dev/null 2>&1; }

confirm() {
  local prompt="$1"
  if [[ ! -t 0 ]]; then return 0; fi  # non-interactive: proceed
  printf '%s [S/n] ' "$prompt"
  read -r ans
  [[ "$ans" == "" || "$ans" == "s" || "$ans" == "S" || "$ans" == "y" || "$ans" == "Y" ]]
}

printf "\n${CYAN}╔══════════════════════════════════════╗${NC}\n"
printf "${CYAN}║   NeuroPA — Instalador automático   ║${NC}\n"
printf "${CYAN}╚══════════════════════════════════════╝${NC}\n\n"
printf "Sistema: %s (%s)\n\n" "$OS" "$ARCH"

# ── Step 1: Detect or clone the repo ──
if [[ ! -f "$ROOT_DIR/pyproject.toml" ]] && ! has neuropa; then
  info "No estás dentro del repo de NeuroPA. Lo clonaré a ~/neuropa"
  if confirm "¿Clonar NeuroPA desde GitHub?"; then
    git clone --depth 1 https://github.com/n30j0su3/neuropa.git "$HOME/neuropa" 2>/dev/null || {
      fail "No pude clonar. Verifica tu conexión o clona manualmente:"
      echo "  git clone https://github.com/n30j0su3/neuropa.git"
      exit 1
    }
    ROOT_DIR="$HOME/neuropa"
    NEUROPA_CLONE=1
    ok "Repo clonado en $ROOT_DIR"
  else
    fail "Necesitas el repo. Clona manualmente: git clone https://github.com/n30j0su3/neuropa.git"
    exit 1
  fi
fi
cd -- "$ROOT_DIR"

# ── Step 2: Python (no asumimos que lo tiene) ──
printf "\n${CYAN}── Python ──${NC}\n"
PYTHON_OK=0
if has python3 && python3 --version | grep -qE '3\.(1[0-9]|[89])'; then
  ok "Python $(python3 --version 2>&1)"
  PYTHON_OK=1
else
  warn "Python 3.8+ no detectado"
  if [[ "$OS" == "Darwin" ]]; then
    if has brew; then
      if confirm "¿Instalar Python con Homebrew?"; then
        brew install python@3.13 2>/dev/null && PYTHON_OK=1
      fi
    else
      warn "Homebrew no está instalado. Instálalo desde https://brew.sh"
    fi
  elif [[ "$OS" == "Linux" ]]; then
    if has apt-get; then
      if confirm "¿Instalar Python con apt?"; then
        sudo apt-get update -qq && sudo apt-get install -y python3 python3-pip 2>/dev/null && PYTHON_OK=1
      fi
    elif has dnf; then
      if confirm "¿Instalar Python con dnf?"; then
        sudo dnf install -y python3 2>/dev/null && PYTHON_OK=1
      fi
    elif has pacman; then
      if confirm "¿Instalar Python con pacman?"; then
        sudo pacman -S --noconfirm python 2>/dev/null && PYTHON_OK=1
      fi
    fi
  fi
  [[ $PYTHON_OK -eq 1 ]] && ok "Python instalado" || fail "No pude instalar Python automáticamente. Descárgalo desde https://python.org"
fi

# ── Step 3: uv (gestiona el entorno virtual sin que el usuario se preocupe) ──
printf "\n${CYAN}── uv (gestor de entorno) ──${NC}\n"
if has uv; then
  ok "uv $(uv --version 2>/dev/null || echo 'instalado')"
else
  info "uv no detectado. Es lo que evita que tengas que pelear con pip/venv."
  if confirm "¿Instalar uv automáticamente?"; then
    if has curl; then
      curl -LsSf https://astral.sh/uv/install.sh | sh 2>/dev/null
    elif has wget; then
      wget -qO- https://astral.sh/uv/install.sh | sh 2>/dev/null
    fi
    # Activate uv for this session
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    if has uv; then
      ok "uv instalado"
    else
      fail "No pude instalar uv. Instálalo desde https://docs.astral.sh/uv/getting-started/installation/"
      exit 1
    fi
  else
    fail "uv es necesario. Instálalo desde https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
  fi
fi

# ── Step 4: git (necesario para clonar) ──
printf "\n${CYAN}── Git ──${NC}\n"
if has git; then
  ok "git $(git --version 2>/dev/null)"
else
  warn "git no detectado"
  if [[ "$OS" == "Darwin" ]] && has brew; then
    if confirm "¿Instalar git con Homebrew?"; then brew install git 2>/dev/null && ok "git instalado"; fi
  elif [[ "$OS" == "Linux" ]] && has apt-get; then
    if confirm "¿Instalar git con apt?"; then sudo apt-get install -y git 2>/dev/null && ok "git instalado"; fi
  elif [[ "$OS" == "Linux" ]] && has dnf; then
    if confirm "¿Instalar git con dnf?"; then sudo dnf install -y git 2>/dev/null && ok "git instalado"; fi
  else
    fail "git no está instalado. Descárgalo desde https://git-scm.com"
  fi
fi

# ── Step 5: Crear entorno e instalar NeuroPA ──
printf "\n${CYAN}── Configurando NeuroPA ──${NC}\n"
info "Creando entorno virtual y dependencias (esto puede tardar 1-2 min)…"
uv sync --quiet 2>/dev/null || uv sync
ok "Dependencias instaladas"
uv run neuropa --version >/dev/null 2>&1 && ok "NeuroPA CLI listo" || { fail "Algo falló en la instalación"; exit 1; }

# ── Step 6: OpenCode (opcional pero recomendado para IA gratis) ──
printf "\n${CYAN}── OpenCode (IA gratuita) ──${NC}\n"
if has opencode || has opencode-ai; then
  ok "OpenCode detectado"
else
  if has node && has npm; then
    NODE_VER=$(node --version 2>/dev/null | sed 's/v//' | cut -d. -f1)
    if [[ "${NODE_VER:-0}" -ge 18 ]]; then
      if confirm "¿Instalar OpenCode (IA gratuita) con npm?"; then
        npm install -g opencode-ai 2>/dev/null && ok "OpenCode instalado" || warn "Falló la instalación de OpenCode. Puedes seguir sin IA local."
      else
        info "OpenCode omitido. NeuroPA funcionará sin IA hasta que lo instales."
      fi
    else
      warn "Node.js < 18. Actualiza Node si quieres OpenCode."
    fi
  else
    warn "Node.js/npm no detectado. OpenCode es opcional."
    info "Para IA gratis más tarde: instala Node.js desde https://nodejs.org y ejecuta: npm install -g opencode-ai"
  fi
fi

# ── Step 7: Arrancar ──
printf "\n${CYAN}── Creando acceso directo 'NeuroPA' ──${NC}\n"
DEST_DIR="$HOME/Desktop"
[ -d "$DEST_DIR" ] || DEST_DIR="$HOME"
EASY_SH="$ROOT_DIR/scripts/neuropa-easy.sh"
UNINSTALL_SH="$ROOT_DIR/scripts/neuropa-uninstall.sh"

if [ -f "$EASY_SH" ]; then
  EASY_SHORTCUT="$DEST_DIR/NeuroPA.command"
  cp "$EASY_SH" "$EASY_SHORTCUT" 2>/dev/null
  chmod +x "$EASY_SHORTCUT" 2>/dev/null
  ok "Acceso directo creado: $EASY_SHORTCUT (doble-click)"
else
  warn "No encontre $EASY_SH"
fi

if [ -f "$UNINSTALL_SH" ]; then
  printf "\n"
  info "Desinstalador (cuando lo necesites): scripts/neuropa-uninstall.sh"
fi

printf "\n${GREEN}╔══════════════════════════════════════════╗${NC}\n"
printf "${GREEN}║   ¡NeuroPA está listo!                   ║${NC}\n"
printf "${GREEN}╚══════════════════════════════════════════╝${NC}\n\n"
printf "Para arrancar: doble-click en 'NeuroPA.command' de tu escritorio\n"
printf "O desde terminal:  cd %s && uv run neuropa\n" "$ROOT_DIR"
printf "URL:               ${CYAN}http://127.0.0.1:8474${NC}\n\n"
printf "  cd %s\n" "$ROOT_DIR"
printf "  uv run neuropa\n\n"
printf "Se abrirá en: ${CYAN}http://127.0.0.1:8474${NC}\n\n"
printf "¿Arrancar NeuroPA ahora? [S/n] "
read -r ans
if [[ "$ans" == "" || "$ans" == "s" || "$ans" == "S" ]]; then
  exec uv run neuropa
fi
printf "\nCuando quieras: cd %s && uv run neuropa\n" "$ROOT_DIR"
