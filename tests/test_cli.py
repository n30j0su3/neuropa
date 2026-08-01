from __future__ import annotations

import json
import ipaddress
from pathlib import Path

from neuropa import cli
from neuropa.domain import Database, Task


def test_version_prints_package_version(capsys):
    try:
        cli.main(["--version"])
    except SystemExit as exc:
        assert exc.code == 0
    assert capsys.readouterr().out.strip() == "0.1.0"


def test_status_reports_database_and_token_paths(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("NEUROPA_DATA_DIR", str(tmp_path / "data"))

    assert cli.main(["--status"]) == 0

    output = capsys.readouterr().out
    assert str(tmp_path / "data" / "neuropa.db") in output
    assert str(tmp_path / "data" / "token") in output


def test_export_writes_all_entities_to_json(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setenv("NEUROPA_DATA_DIR", str(data_dir))
    database = Database(data_dir / "neuropa.db")
    database.create(Task(title="Remember this"))
    database.close()
    target = tmp_path / "export.json"

    assert cli.main(["--export", str(target)]) == 0

    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["task"][0]["title"] == "Remember this"


def test_export_without_path_prints_json(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("NEUROPA_DATA_DIR", str(tmp_path / "data"))

    assert cli.main(["--export"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert set(payload) >= {"inbox", "task", "memory_claim"}


def test_lan_cidr_requires_private_narrow_network():
    assert cli.validate_lan_cidr("192.168.1.0/24") == ipaddress.ip_network("192.168.1.0/24")
    assert cli.validate_lan_cidr("192.168.1.0/25") == ipaddress.ip_network("192.168.1.0/25")
    assert cli.validate_lan_cidr("fd00::/64") == ipaddress.ip_network("fd00::/64")

    for cidr in ("192.168.0.0/23", "8.8.8.0/24", "0.0.0.0/0", "::/0", "2001:db8::/64"):
        try:
            cli.validate_lan_cidr(cidr)
        except ValueError:
            pass
        else:
            raise AssertionError(f"CIDR should be rejected: {cidr}")


def test_lan_pairing_code_is_url_fragment_safe_and_not_master_token(monkeypatch):
    monkeypatch.setenv("NEUROPA_MASTER_TOKEN", "master-secret")
    code = cli.generate_pairing_code()
    assert len(code) >= 32
    assert all(char.isalnum() or char in "-_" for char in code)
    assert code != "master-secret"
