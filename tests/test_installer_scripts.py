from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "scripts"


def run_script(name: str, *args: str, cwd: Path = ROOT, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPTS / name), *args],
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def test_installer_scripts_have_valid_bash_syntax():
    for script in ("install.sh", "run-neuropa.sh", "uninstall.sh"):
        result = subprocess.run(["bash", "-n", str(SCRIPTS / script)], text=True, capture_output=True)
        assert result.returncode == 0, result.stderr


def test_install_check_is_read_only(tmp_path: Path):
    copied_scripts = tmp_path / "scripts"
    shutil.copytree(SCRIPTS, copied_scripts)
    (tmp_path / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
    before = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))

    result = subprocess.run(
        ["bash", str(copied_scripts / "install.sh"), "--check"],
        cwd=tmp_path,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    after = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))
    assert result.returncode == 0
    assert before == after
    assert "Modo check" not in result.stdout or "no se harán cambios" in result.stdout


def test_run_help_is_available_without_environment():
    result = run_script("run-neuropa.sh", "--help")
    assert result.returncode == 0
    assert "--lan" in result.stdout
    assert "--port" in result.stdout


def test_uninstall_dry_run_does_not_delete_repo_environment(tmp_path: Path):
    copied_scripts = tmp_path / "scripts"
    shutil.copytree(SCRIPTS, copied_scripts)
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "marker").write_text("keep", encoding="utf-8")

    result = subprocess.run(
        ["bash", str(copied_scripts / "uninstall.sh"), "--dry-run"],
        cwd=tmp_path,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    assert result.returncode == 0
    assert (tmp_path / ".venv" / "marker").exists()
    assert "dry" in result.stdout.lower()


def test_uninstall_purge_requires_exact_confirmation(tmp_path: Path):
    copied_scripts = tmp_path / "scripts"
    shutil.copytree(SCRIPTS, copied_scripts)
    data_dir = tmp_path / "user-data"
    data_dir.mkdir()
    (data_dir / "keep.txt").write_text("keep", encoding="utf-8")
    env = os.environ | {"NEUROPA_DATA_DIR": str(data_dir)}

    result = subprocess.run(
        ["bash", str(copied_scripts / "uninstall.sh"), "--purge-data"],
        cwd=tmp_path,
        env=env,
        input="no\n",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    assert result.returncode != 0
    assert data_dir.exists()
    assert (data_dir / "keep.txt").exists()
    assert "confirm" in result.stdout.lower()
