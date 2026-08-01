#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd -- "$ROOT_DIR"

usage() {
  cat <<'EOF'
NeuroPA runner / lanzador de NeuroPA

Usage / Uso:
  scripts/run-neuropa.sh [--lan] [--lan-cidr CIDR] [--port PORT]

  --lan          Comparte temporalmente en la LAN de confianza / temporary trusted-LAN access
  --lan-cidr CIDR Red privada explícita (mínimo /24 IPv4 o /64 IPv6)
  --port PORT    Puerto HTTP (por defecto 8474) / HTTP port (default 8474)
  -h,--help      Muestra esta ayuda / show this help
EOF
}

args=()
while (($#)); do
  case "$1" in
    --lan) args+=("--lan") ;;
    --lan-cidr)
      (($# >= 2)) || { echo '--lan-cidr requiere un valor / requires a value' >&2; exit 2; }
      args+=("--lan-cidr" "$2"); shift ;;
    --lan-cidr=*) args+=("--lan-cidr" "${1#*=}") ;;
    --port)
      (($# >= 2)) || { echo '--port requiere un valor / requires a value' >&2; exit 2; }
      args+=("--port" "$2"); shift ;;
    --port=*) args+=("--port" "${1#*=}") ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Opción desconocida / unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

if ! command -v uv >/dev/null 2>&1; then
  echo 'Falta uv. Ejecuta primero scripts/install.sh / uv is missing. Run scripts/install.sh first.' >&2
  exit 1
fi

if [[ -d "$ROOT_DIR/.venv" ]]; then
  echo 'Usando el entorno existente .venv / using existing .venv.'
else
  echo 'No hay .venv; uv run preparará el entorno una vez / no .venv; uv run will prepare it once.'
fi

if ((${#args[@]} == 0)); then
  echo 'Iniciando NeuroPA local en http://127.0.0.1:8474'
elif [[ " ${args[*]} " == *' --lan '* ]]; then
  echo 'Iniciando NeuroPA en LAN temporal: usa sólo una red de confianza.'
else
  echo "Iniciando NeuroPA con opciones: ${args[*]}"
fi

exec uv run neuropa "${args[@]}"
