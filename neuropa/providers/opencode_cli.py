from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

DEFAULT_MODEL = "opencode/laguna-s-2.1-free"


def _discover_opencode() -> str:
    """Best-effort discovery of the opencode binary.

    Checks PATH first, then common npm-global install paths on Windows,
    macOS and Linux. Returns the absolute path or an empty string when not
    found so the caller can report a clean unavailability state.
    """
    found = shutil.which("opencode")
    if found:
        return found
    home = Path(os.path.expanduser("~"))
    candidates = [
        home / ".opencode" / "bin" / "opencode",          # macOS / Linux fallback
        home / "AppData" / "Roaming" / "npm" / "opencode.cmd",  # Windows npm-global
        home / "AppData" / "Roaming" / "npm" / "opencode.ps1",
        Path("C:/Program Files/nodejs/opencode.cmd"),
        Path("C:/Program Files (x86)/nodejs/opencode.cmd"),
        Path("/usr/local/bin/opencode"),
        Path("/opt/homebrew/bin/opencode"),
    ]
    for c in candidates:
        try:
            if c.is_file() and os.access(c, os.X_OK):
                return str(c)
        except OSError:
            continue
    return ""


class OpenCodeError(RuntimeError):
    """Safe, user-facing OpenCode failure without command secrets."""


class OpenCodeUnavailable(OpenCodeError):
    pass


class OpenCodeTimeout(OpenCodeError):
    pass


def parse_jsonl(output: str) -> dict[str, Any]:
    """Parse OpenCode JSONL, retaining final text and public usage only."""
    text: list[str] = []
    session_id = None
    usage: dict[str, Any] = {}
    for line in output.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        session_id = event.get("sessionID") or event.get("sessionId") or session_id
        if event.get("type") == "text":
            part = event.get("part") or {}
            value = part.get("text")
            if isinstance(value, str):
                text.append(value)
        if event.get("type") == "step_finish":
            part = event.get("part") or {}
            raw = part.get("tokens") or event.get("tokens") or {}
            if isinstance(raw, dict):
                usage.update({k: raw[k] for k in ("input", "output", "total", "prompt", "completion") if k in raw})
            for key in ("cost", "costUsd", "cost_usd"):
                if key in part or key in event:
                    usage["cost"] = part.get(key, event.get(key))
    return {"content": "".join(text), "session_id": session_id, "usage": usage}


class OpenCodeCLI:
    name = "opencode_free"

    def __init__(self, executable: str | None = None, timeout: int = 120, cache_ttl: int = 60):
        # Allow override via env var so users can point at npm-global opencode
        # without requiring it on PATH (Windows installs it under %LOCALAPPDATA%\npm).
        env_exe = os.environ.get("NEUROPA_OPENCODE_BIN")
        if executable:
            self.executable = executable
        elif env_exe:
            self.executable = env_exe
        else:
            self.executable = _discover_opencode()
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self._models: list[str] | None = None
        self._models_at = 0.0

    def health(self) -> bool:
        if not self.executable:
            return False
        if os.path.isabs(self.executable):
            return os.path.isfile(self.executable) and os.access(self.executable, os.X_OK)
        return shutil.which(self.executable) is not None

    def list_models(self) -> list[str]:
        if self._models is not None and time.monotonic() - self._models_at < self.cache_ttl:
            return self._models
        if not self.health():
            return self._models or []
        try:
            result = subprocess.run([self.executable, "models"], shell=False, capture_output=True, text=True, timeout=self.timeout)
        except (OSError, subprocess.TimeoutExpired):
            return self._models or []
        models: list[str] = []
        # OpenCode CLI output format: one model per line as "provider/model-id"
        # Examples: "opencode/laguna-s-2.1-free", "opencode/big-pickle", "zai-coding-plan/glm-5.2"
        for line in result.stdout.splitlines():
            candidate = line.strip()
            if not candidate or candidate.startswith("#") or " " in candidate:
                continue
            # Accept everything from the free `opencode/` provider, plus legacy big-pickle
            if candidate.startswith("opencode/") or candidate == "big-pickle":
                if candidate not in models:
                    models.append(candidate)
        self._models, self._models_at = models, time.monotonic()
        return models

    def generate(self, messages: list[dict[str, str]], model: str = DEFAULT_MODEL, workspace: str | Path | None = None, timeout: int | None = None, **_: Any) -> dict[str, Any]:
        if not self.health():
            raise OpenCodeUnavailable("OpenCode CLI no está instalado o no está disponible")
        prompt = "\n\n".join(f"{m.get('role', 'user').upper()}: {m.get('content', '')}" for m in messages)
        command = [self.executable, "run", "--pure", "--format", "json", "-m", model or DEFAULT_MODEL]
        try:
            result = subprocess.run(command, input=prompt, shell=False, cwd=str(workspace) if workspace else None, capture_output=True, text=True, timeout=timeout or self.timeout)
        except subprocess.TimeoutExpired as exc:
            raise OpenCodeTimeout("OpenCode agotó el tiempo de espera") from exc
        except OSError as exc:
            raise OpenCodeUnavailable("No se pudo ejecutar OpenCode") from exc
        if result.returncode != 0:
            raise OpenCodeError("OpenCode no pudo completar la solicitud")
        parsed = parse_jsonl(result.stdout)
        if not parsed["content"].strip():
            # Agent gave up without output (e.g. tool permissions auto-rejected in
            # --pure mode). Surface as provider failure so the router can fall back
            # instead of storing an empty assistant bubble.
            raise OpenCodeError("OpenCode devolvió una respuesta vacía")
        return {"text": parsed["content"], "content": parsed["content"], "provider_used": self.name, "model": model or DEFAULT_MODEL, "session_id": parsed["session_id"], "usage": parsed["usage"]}

    def generate_stream(self, messages: list[dict[str, str]], model: str = DEFAULT_MODEL, workspace: str | Path | None = None, timeout: int | None = None, **_: Any):
        """Yield partial content as it arrives from the provider.

        Emits dicts: {"partial": str} for incremental text, then finally
        {"result": dict} with the full structured result. This lets the UI show
        text live instead of blocking until completion.
        """
        if not self.health():
            raise OpenCodeUnavailable("OpenCode CLI no está instalado o no está disponible")
        prompt = "\n\n".join(f"{m.get('role', 'user').upper()}: {m.get('content', '')}" for m in messages)
        command = [self.executable, "run", "--pure", "--format", "json", "-m", model or DEFAULT_MODEL]
        try:
            proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(workspace) if workspace else None)
        except OSError as exc:
            raise OpenCodeUnavailable("No se pudo ejecutar OpenCode") from exc
        try:
            stdout, stderr = proc.communicate(input=prompt, timeout=timeout or self.timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            raise OpenCodeTimeout("OpenCode agotó el tiempo de espera")
        if proc.returncode != 0:
            raise OpenCodeError("OpenCode no pudo completar la solicitud")
        parsed = parse_jsonl(stdout)
        content = parsed["content"]
        if not content.strip():
            raise OpenCodeError("OpenCode devolvió una respuesta vacía")
        # Stream the content in chunks to give immediate visual feedback
        lines = content.split("\n")
        accumulated = ""
        for i, line in enumerate(lines):
            chunk = line + ("\n" if i < len(lines) - 1 else "")
            accumulated += chunk
            yield {"partial": accumulated}
        yield {"result": {"text": content, "content": content, "provider_used": self.name, "model": model or DEFAULT_MODEL, "session_id": parsed["session_id"], "usage": parsed["usage"]}}
