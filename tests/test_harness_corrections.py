from __future__ import annotations

from neuropa.api.app import client_allowed_for_token
from neuropa.cli import build_parser
from neuropa.domain import Database
from neuropa.services import HarnessService


class SilentRouter:
    def status(self):
        return {"modes": {}}


def test_harness_defaults_to_clarity_mode(tmp_path):
    db = Database(tmp_path / "neuropa.db")
    service = HarnessService(db, SilentRouter(), tmp_path)
    session = service.create_session()

    mode = db.get("agent_mode", session.mode_id)

    assert mode is not None
    assert mode.slug == "clarity"
    db.close()


def test_token_access_allows_loopback_and_trusted_lan():
    assert client_allowed_for_token("127.0.0.1", None)
    assert client_allowed_for_token("::1", None)
    assert not client_allowed_for_token("192.168.1.50", None)
    assert client_allowed_for_token("192.168.1.50", "192.168.1.0/24")
    assert not client_allowed_for_token("192.168.1.50", "192.168.1.0/24", pairing_required=True)
    assert not client_allowed_for_token("192.168.2.50", "192.168.1.0/24")
    assert not client_allowed_for_token("not-an-ip", "192.168.1.0/24")


def test_cli_exposes_explicit_lan_mode():
    args = build_parser().parse_args(["--lan", "--lan-cidr", "192.168.1.0/24"])
    assert args.lan is True
    assert args.lan_cidr == "192.168.1.0/24"
