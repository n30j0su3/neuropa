import os
from pathlib import Path
from neuropa.providers.opencode_cli import DEFAULT_MODEL, OpenCodeCLI, parse_jsonl
from neuropa.providers.router import ProviderRouter


def test_parse_jsonl_hides_reasoning_and_extracts_usage():
    result = parse_jsonl('{"type":"reasoning","part":{"text":"secret"}}\n{"sessionID":"s1","type":"text","part":{"text":"Hola"}}\n{"type":"step_finish","part":{"tokens":{"input":3,"output":4},"cost":0}}')
    assert result == {"content":"Hola", "session_id": "s1", "usage": {"input": 3, "output": 4, "cost": 0}}


def test_cli_runs_real_temporary_executable(tmp_path):
    script = tmp_path / "opencode"
    body = (
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "if sys.argv[1] == 'models':\n"
        "    print('opencode/a-free\\nopencode/b-free\\nopencode/c-free\\nopencode/d-free\\nopencode/e-free')\n"
        "else:\n"
        "    print('{\"sessionID\":\"abc\",\"type\":\"text\",\"part\":{\"text\":\"OK\"}}')\n"
    )
    script.write_text(body)
    script.chmod(0o755)
    cli = OpenCodeCLI(str(script))
    assert cli.health()
    assert len(cli.list_models()) == 5
    assert cli.generate([{"role": "user", "content": "x"}])["text"] == "OK"


def test_opencode_catalog_keeps_all_free_models_and_has_safe_recommendation(tmp_path):
    script = tmp_path / "opencode"
    script.write_text(
        "#!/usr/bin/env python3\n"
        "print('opencode/one-free\\nopencode/two-free')\n"
    )
    script.chmod(0o755)
    cli = OpenCodeCLI(str(script))
    assert cli.list_models() == ["opencode/one-free", "opencode/two-free"]


def test_provider_status_has_catalog_contract_and_safe_recommendation():
    from neuropa.providers.opencode_cli import OpenCodeCLI as _OC
    from neuropa.core.providers.multi_engine import OllamaEngine as _OL

    class OpenCode(_OC):
        def __init__(self):
            pass
        def health(self): return True
        def list_models(self): return ["other-free"]
    class Local(_OL):
        def __init__(self):
            pass
        def health(self): return False

    router = ProviderRouter()
    router.opencode = OpenCode()
    router.local = Local()
    state = router.status()
    assert state["providers"]["opencode_free"]["models"] == ["other-free"]
    assert "recommended_model" in state["providers"]["opencode_free"]


def test_router_uses_local_only_when_no_safe_recommendation():
    from neuropa.providers.opencode_cli import OpenCodeCLI as _OC
    from neuropa.core.providers.multi_engine import OllamaEngine as _OL

    class OpenCode(_OC):
        def __init__(self):
            pass
        def health(self): return True
        def list_models(self): return ["should-not-leak"]
    class Local(_OL):
        def __init__(self):
            pass
        def health(self): return True
        def list_models(self): return ["unused-local"]

    router = ProviderRouter()
    router.opencode = OpenCode()
    router.local = Local()
    state = router.status()
    assert "opencode_free" in state["providers"]
    assert DEFAULT_MODEL == "opencode/laguna-s-2.1-free"
