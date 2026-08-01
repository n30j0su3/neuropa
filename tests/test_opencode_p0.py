import os
from pathlib import Path
from neuropa.providers.opencode_cli import OpenCodeCLI, parse_jsonl


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
