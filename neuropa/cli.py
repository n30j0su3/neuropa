from __future__ import annotations

import argparse
import json
import os
import ipaddress
import secrets
import socket
import threading
import webbrowser
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Sequence

from neuropa.domain import ENTITY_TYPES, Database, default_data_dir

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8474


def validate_lan_cidr(value: str) -> ipaddress.IPv4Network | ipaddress.IPv6Network:
    """Validate an explicitly trusted, private LAN network before binding."""
    try:
        network = ipaddress.ip_network(value, strict=False)
    except ValueError as exc:
        raise ValueError(f"CIDR LAN inválido: {value}") from exc
    minimum_prefix = 24 if network.version == 4 else 64
    if network.prefixlen < minimum_prefix:
        raise ValueError(f"La red LAN debe ser como mínimo /{minimum_prefix}: {network}")
    private = network.is_private and (
        network.version == 4
        or network.is_link_local
        or network.network_address in ipaddress.ip_network("fc00::/7")
    )
    if not network.is_private or network.is_reserved or network.is_loopback or network.is_unspecified or network.is_multicast or (network.version == 6 and not (network.network_address.exploded.startswith("fd") or network.network_address.exploded.startswith("fe80"))):
        raise ValueError(f"La red LAN debe ser privada y no especial: {network}")
    return network


def generate_pairing_code() -> str:
    """Return a one-time, URL-fragment-safe LAN pairing code."""
    return secrets.token_urlsafe(24)


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
        description="AI workspace local para pensar, crear y trabajar con memoria persistente.",
    )
    parser.add_argument("--version", action="version", version=package_version())
    parser.add_argument("--port", type=int, default=int(os.getenv("NEUROPA_PORT", DEFAULT_PORT)), help="Puerto de la API (por defecto: 8474)")
    parser.add_argument("--status", action="store_true", help="Muestra las rutas locales de NeuroPA")
    parser.add_argument("--export", nargs="?", const="-", metavar="ARCHIVO", help="Exporta los datos a JSON; sin ARCHIVO imprime en pantalla")
    parser.add_argument("--lan", action="store_true", help="Comparte temporalmente NeuroPA en tu red local de confianza")
    parser.add_argument("--lan-cidr", metavar="CIDR", help="Red autorizada, por ejemplo 192.168.1.0/24 (se detecta automáticamente con --lan)")
    parser.add_argument("--pairing", action="store_true", help="Exige emparejamiento de un solo uso al compartir por LAN")
    return parser


def local_lan_address() -> tuple[str, str]:
    """Return the routed LAN address and a conservative /24 pairing network."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        address = sock.getsockname()[0]
    finally:
        sock.close()
    return address, str(ipaddress.ip_network(f"{address}/24", strict=False))


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
    if args.pairing and not args.lan:
        raise SystemExit("--pairing requiere --lan")

    import uvicorn
    from neuropa.api.app import create_app

    host = DEFAULT_HOST
    browser_url = f"http://{DEFAULT_HOST}:{args.port}"
    display_url = browser_url
    if args.lan:
        from neuropa.api.app import create_app, validate_lan_cidr
        address, detected_cidr = local_lan_address()
        cidr = args.lan_cidr or detected_cidr
        network = validate_lan_cidr(cidr)
        os.environ["NEUROPA_LAN_CIDR"] = str(network)
        host = "0.0.0.0"
        display_url = f"http://{address}:{args.port}"
        print(f"LAN temporal habilitada para {network}. Úsala sólo en una red de confianza.")
        if args.pairing:
            pairing_code = generate_pairing_code()
            os.environ["NEUROPA_PAIRING_CODE"] = pairing_code
            browser_url = f"{display_url}#pair={pairing_code}"
            print(f"Enlace LAN de emparejamiento: {browser_url}")
            print(f"Código de emparejamiento de un solo uso: {pairing_code}")
        else:
            os.environ.pop("NEUROPA_PAIRING_CODE", None)
            print("Acceso directo habilitado para dispositivos dentro de la red autorizada.")
    threading.Timer(0.5, webbrowser.open, args=(browser_url,)).start()
    print(f"NeuroPA está listo en {display_url}. Pulsa Ctrl+C para salir.")
    try:
        uvicorn.run(create_app(), host=host, port=args.port, log_level="info")
    except KeyboardInterrupt:
        print("\nNeuroPA cerrado. Tus datos siguen en tu equipo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
