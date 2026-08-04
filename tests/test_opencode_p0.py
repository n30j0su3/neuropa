import os
from pathlib import Path
from neuropa.providers.opencode_cli import OpenCodeCLI, parse_jsonl
from neuropa.providers.router import ProviderRouter


def test_parse_jsonl_hides_reasoning_and_extracts_usage():
    result = parse_jsonl('{"type":"reasoning","part":{"text":"secret"}}\n{"sessionID":"s1","type":"text","part":{"text":"Hola"}}\n{"type":"step_finish","part":{"tokens":{"input":3,"output":4},"cost":0}}')
    assert result == {"content":"Hola", "session_id":"s1", "usage":{"input":3,"output":4,"cost":0}}


def test_cli_runs_real_temporary_executable(tmp_path):
    script = tmp_path / "opencode"
    script.write_text("#!/usr/bin/env python3\nimport sys\nif sys.argv[1] == 'models': print('a-free\\nb-free\\nc-free\\nd-free\\ne-free')\nelse: print('{\\\"sessionID\\\":\\\"abc\\\",\\\"type\\\":\\\"text\\\",\\\"part\\\":{\\\"text\\\":\\\"OK\\\"}}')\n")
    script.chmod(0o755)
    cli = OpenCodeCLI(str(script))
    assert cli.health()
    assert len(cli.list_models()) == 5
    assert cli.generate([{"role":"user","content":"x"}])["text"] == "OK"


def test_opencode_catalog_keeps_all_free_models_and_has_safe_recommendation(tmp_path):
    script = tmp_path / "opencode"
    script.write_text("#!/usr/bin/env python3\nprint('one-free\\ntwo-free')\n")
    script.chmod(0o755)
    cli = OpenCodeCLI(str(script))
    assert cli.list_models() == ["one-free", "two-free"]


def test_provider_status_has_catalog_contract_and_safe_recommendation():
    class OpenCode:
        def health(self): return True
        def list_models(self): return ["other-free"]
    class Local:
        def health(self): return False
        def list_models(self): return ["should-not-leak"]
    state = ProviderRouter(ollama=Local(), opencode=OpenCode()).status()
    for provider in state["providers"].values():
        assert {"available", "description", "privacy", "cost", "models", "recommended_model"} <= provider.keys()
    assert state["providers"]["opencode_free"]["models"] == ["other-free"]
    assert state["providers"]["opencode_free"]["recommended_model"] is None
    assert state["providers"]["local"]["models"] == []


def test_legacy_status_model_never_returns_model_absent_from_catalog():
    class OpenCode:
        def health(self): return True
        def list_models(self): return ["other-free"]
    class Local:
        def health(self): return False
        def list_models(self): return ["unused-local"]

    state = ProviderRouter(ollama=Local(), opencode=OpenCode()).status()
    assert state["providers"]["opencode_free"]["model"] is None
    assert state["providers"]["opencode_free"]["catalog_known"] is True
    assert state["providers"]["local"]["catalog_known"] is False
