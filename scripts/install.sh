#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd -- "$ROOT_DIR"

YES=0
CHECK_ONLY=0

usage() {
  cat <<'EOF'
NeuroPA local installer / instalador local de NeuroPA

Usage / Uso:
  scripts/install.sh [--yes] [--check]

  --yes    Accept prompts explicitly (automation) / acepta confirmaciones explícitamente
  --check  Inspect prerequisites without changing files / revisa sin cambiar archivos
  -h,--help Show this help / muestra esta ayuda
EOF
}

has_command() { command -v "$1" >/dev/null 2>&1; }

confirm() {
  local prompt="$1"
  if (( YES )); then
    return 0
  fi
  if [[ ! -t 0 ]]; then
    printf 'No hay terminal interactiva; no se ejecuta: %s\n' "$prompt" >&2
    return 1
  fi
  printf '%s [y/N] ' "$prompt"
  read -r answer
  [[ "$answer" == "y" || "$answer" == "Y" || "$answer" == "yes" || "$answer" == "YES" ]]
}

install_uv() {
  if ! confirm "uv no está instalado. ¿Descargar y ejecutar el instalador oficial visible ahora? / uv is missing. Download and run the official installer now?"; then
    cat >&2 <<'EOF'
Instala uv manualmente desde https://docs.astral.sh/uv/getting-started/installation/
Luego vuelve a ejecutar este script. / Install uv manually, then run this script again.
EOF
    return 1
  fi
  if ! has_command curl; then
    cat >&2 <<'EOF'
No encuentro curl. Descarga el instalador de uv desde la URL oficial y ejecútalo de forma visible.
I could not find curl. Download the uv installer from the official URL and run it visibly.
EOF
    return 1
  fi
  local installer
  installer="$(mktemp "${TMPDIR:-/tmp}/neuropa-uv-installer.XXXXXX")"
  trap 'rm -f -- "$installer"' RETURN
  printf 'Descargando instalador uv en %s (visible; no se ejecuta vía pipe).\n' "$installer"
  curl --fail --location --show-error --output "$installer" https://astral.sh/uv/install.sh
  bash "$installer"
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
  has_command uv || {
    echo "uv se instaló pero no está en PATH; abre una terminal nueva y reintenta." >&2
    return 1
  }
}

while (($#)); do
  case "$1" in
    --yes) YES=1 ;;
    --check) CHECK_ONLY=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Opción desconocida / unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

printf 'NeuroPA installer: %s\n' "$ROOT_DIR"
printf 'Sistema / OS: %s\n' "$(uname -s)"

if has_command uv; then
  printf 'OK: uv %s\n' "$(uv --version 2>/dev/null || true)"
else
  printf 'FALTA: uv / MISSING: uv\n'
  if (( CHECK_ONLY )); then
    echo 'Modo check: no se harán cambios / check mode: no changes will be made.'
    exit 0
  fi
  install_uv
fi

if (( CHECK_ONLY )); then
  if [[ -d "$ROOT_DIR/.venv" ]]; then
    echo 'OK: .venv existe / .venv exists'
  else
    echo 'INFO: .venv aún no existe / .venv is not created yet'
  fi
else
  if [[ -d "$ROOT_DIR/.venv" ]]; then
    echo 'Entorno existente: se reutiliza .venv / existing environment: reusing .venv'
  else
    echo 'Creando entorno con uv sync / creating environment with uv sync'
  fi
  uv sync
  echo 'Validando CLI / validating CLI'
  uv run neuropa --version
fi

if has_command opencode; then
  printf 'OK: OpenCode CLI (%s)\n' "$(command -v opencode)"
elif has_command opencode-ai; then
  printf 'OK: OpenCode CLI (%s)\n' "$(command -v opencode-ai)"
else
  echo 'INFO: OpenCode CLI no detectado / not detected.'
  if (( CHECK_ONLY )); then
    echo 'Recomendado: instala OpenCode gratis con npm install -g opencode-ai (tras revisar el comando).'
  elif has_command npm; then
    if confirm '¿Instalar OpenCode CLI gratis con npm install -g opencode-ai? / Install the free OpenCode CLI now?'; then
      npm install -g opencode-ai
      echo 'OpenCode instalado. Ejecuta opencode para configurarlo.'
    else
      echo 'OpenCode omitido; puedes instalarlo después con: npm install -g opencode-ai'
    fi
  else
    echo 'npm no está disponible. Instala Node.js/npm y luego ejecuta: npm install -g opencode-ai'
  fi
fi

echo 'No se instala Ollama automáticamente / Ollama is never installed automatically.'
echo 'Listo. Ejecuta: scripts/run-neuropa.sh / Ready. Run: scripts/run-neuropa.sh'
