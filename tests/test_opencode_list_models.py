"""Tests for the OpenCode list_models parser.

The parser must accept the current `opencode models` output format:
lines like `opencode/laguna-s-2.1-free` and exclude non-opencode providers
(e.g. `zai-coding-plan/glm-5.2`).
"""
from __future__ import annotations

from unittest.mock import patch
import subprocess

from neuropa.providers.opencode_cli import OpenCodeCLI


def _fake_run(stdout: str):
    def _run(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")
    return _run


def test_list_models_accepts_opencode_free_provider():
    """All opencode/* models should be returned."""
    stdout = """\
opencode/big-pickle
opencode/deepseek-v4-flash-free
opencode/laguna-s-2.1-free
opencode/ling-3.0-flash-free
opencode/longcat-2.0-free
"""
    cli = OpenCodeCLI()
    with patch("neuropa.providers.opencode_cli.subprocess.run", _fake_run(stdout)):
        with patch.object(cli, "health", return_value=True):
            models = cli.list_models()
    assert len(models) == 5
    assert all(m.startswith("opencode/") for m in models)
    assert "opencode/laguna-s-2.1-free" in models
    assert "opencode/big-pickle" in models


def test_list_models_excludes_other_providers():
    """Only opencode/* models — not zai-coding-plan/* or others."""
    stdout = """\
opencode/big-pickle
zai-coding-plan/glm-4.7
zai-coding-plan/glm-5-turbo
opencode/laguna-s-2.1-free
"""
    cli = OpenCodeCLI()
    with patch("neuropa.providers.opencode_cli.subprocess.run", _fake_run(stdout)):
        with patch.object(cli, "health", return_value=True):
            models = cli.list_models()
    assert "opencode/big-pickle" in models
    assert "opencode/laguna-s-2.1-free" in models
    assert "zai-coding-plan/glm-4.7" not in models
    assert "zai-coding-plan/glm-5-turbo" not in models
    assert len(models) == 2


def test_list_models_skips_comments_and_blank_lines():
    stdout = """\
# opencode/big-pickle
opencode/big-pickle

# this is a comment line
opencode/laguna-s-2.1-free
"""
    cli = OpenCodeCLI()
    with patch("neuropa.providers.opencode_cli.subprocess.run", _fake_run(stdout)):
        with patch.object(cli, "health", return_value=True):
            models = cli.list_models()
    assert models == ["opencode/big-pickle", "opencode/laguna-s-2.1-free"]


def test_list_models_handles_short_output():
    """The CLI may also print explanatory lines (path, error trace). Skip them."""
    stdout = """\
[skill-registry] refresh failed
Executable not found: gentle-ai
opencode/laguna-s-2.1-free
"""
    cli = OpenCodeCLI()
    with patch("neuropa.providers.opencode_cli.subprocess.run", _fake_run(stdout)):
        with patch.object(cli, "health", return_value=True):
            models = cli.list_models()
    assert models == ["opencode/laguna-s-2.1-free"]


def test_list_models_returns_empty_if_not_healthy():
    cli = OpenCodeCLI()
    with patch.object(cli, "health", return_value=False):
        models = cli.list_models()
    assert models == []
