#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd -- "$ROOT_DIR"

DRY_RUN=0
PURGE_DATA=0

usage() {
  cat <<'EOF'
NeuroPA uninstall / desinstalación de NeuroPA

Usage / Uso:
  scripts/uninstall.sh [--dry-run] [--purge-data]

Default: remove only the repository .venv and known repository caches.
Por defecto: sólo elimina .venv y cachés conocidas del repositorio.

--purge-data  Also remove user data, but only after exact confirmation:
              PURGE NEUROPA DATA
--dry-run     Show actions without changing files.
EOF
}

while (($#)); do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --purge-data) PURGE_DATA=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Opción desconocida / unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

# Keep this allowlist literal and repository-scoped: never interpolate arbitrary rm paths.
REPO_TARGETS=(
  "$ROOT_DIR/.venv"
  "$ROOT_DIR/.pytest_cache"
  "$ROOT_DIR/.mypy_cache"
  "$ROOT_DIR/.ruff_cache"
)

for target in "${REPO_TARGETS[@]}"; do
  if [[ -e "$target" || -L "$target" ]]; then
    if (( DRY_RUN )); then
      echo "[dry-run] eliminaría / would remove: $target"
    else
      case "$target" in
        "$ROOT_DIR/.venv"|"$ROOT_DIR/.pytest_cache"|"$ROOT_DIR/.mypy_cache"|"$ROOT_DIR/.ruff_cache") rm -rf -- "$target" ;;
        *) echo "Ruta no permitida / unsafe path: $target" >&2; exit 1 ;;
      esac
      echo "Eliminado / removed: $target"
    fi
  fi
done

if (( PURGE_DATA )); then
  DATA_DIR="${NEUROPA_DATA_DIR:-$HOME/.local/share/neuropa}"
  if [[ -z "$DATA_DIR" || "$DATA_DIR" == "/" || "$DATA_DIR" == "$HOME" || "$DATA_DIR" == "$HOME/" ]]; then
    echo 'Ruta de datos insegura; no se elimina nada / unsafe data path; nothing removed.' >&2
    exit 1
  fi
  echo "ADVERTENCIA: esto elimina datos del usuario / WARNING: this deletes user data: $DATA_DIR"
  if (( DRY_RUN )); then
    echo '[dry-run] no se pide confirmación ni se elimina nada / nothing removed.'
  else
    printf 'Escribe exactamente PURGE NEUROPA DATA para continuar: '
    read -r confirmation
    if [[ "$confirmation" != "PURGE NEUROPA DATA" ]]; then
      echo 'Confirmación incorrecta; no se eliminaron datos / confirmation mismatch; user data kept.' >&2
      exit 1
    fi
    case "$DATA_DIR" in
      ""|/|"$HOME"|"$HOME/" ) echo 'Ruta insegura / unsafe path' >&2; exit 1 ;;
      *) rm -rf -- "$DATA_DIR" ;;
    esac
    echo "Datos eliminados / user data removed: $DATA_DIR"
  fi
else
  echo 'Datos del usuario conservados / user data preserved.'
fi

echo 'Desinstalación terminada / uninstall complete.'
