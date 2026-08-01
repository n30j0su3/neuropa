from __future__ import annotations

import argparse
import json
import os
import threading
import webbrowser
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Sequence

from neuropa.domain import ENTITY_TYPES, Database, default_data_dir

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8474


def package_version() -> str:
    try:
        return version("neuropa")
    except PackageNotFoundError:
        return "0.1.0"


def _paths() -> tuple[Path, Path]:
    data_dir = default_data_dir()
    return data_dir / "neuropa.db", data_dir / "token"


def export_data(destination: str | None = None) -> int:
    db_path, _ = _paths()
    database = Database(db_path)
    try:
        payload = {
            entity_type: [obj.to_dict() for obj in database.list(entity_type)]
            for entity_type in ENTITY_TYPES
        }
    finally:
        database.close()

    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if destination in (None, "-"):
        print(rendered, end="")
    else:
        target = Path(destination).expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
        print(f"Exportados {sum(len(rows) for rows in payload.values())} registros a {target}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="neuropa",
        description="Tu asistente personal local para capturar, enfocar y recordar.",
    )
    parser.add_argument("--version", action="version", version=package_version())
    parser.add_argument("--port", type=int, default=int(os.getenv("NEUROPA_PORT", DEFAULT_PORT)), help="Puerto de la API (por defecto: 8474)")
    parser.add_argument("--status", action="store_true", help="Muestra las rutas locales de NeuroPA")
    parser.add_argument("--export", nargs="?", const="-", metavar="ARCHIVO", help="Exporta los datos a JSON; sin ARCHIVO imprime en pantalla")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.status:
        db_path, token_path = _paths()
        print(f"DB: {db_path}")
        print(f"Token: {token_path}")
        return 0

    if args.export is not None:
        return export_data(args.export)

    if not 1 <= args.port <= 65535:
        raise SystemExit("El puerto debe estar entre 1 y 65535")

    import uvicorn
    from neuropa.api.app import create_app

    url = f"http://{DEFAULT_HOST}:{args.port}"
    threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    print(f"NeuroPA está listo en {url}. Pulsa Ctrl+C para salir.")
    try:
        uvicorn.run(create_app(), host=DEFAULT_HOST, port=args.port, log_level="info")
    except KeyboardInterrupt:
        print("\nNeuroPA cerrado. Tus datos siguen en tu equipo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
