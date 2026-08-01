from __future__ import annotations

import json
import os
import random
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from neuropa.core.providers.multi_engine import OllamaEngine, OpenAICompatEngine


class NoAIProviderAvailable(RuntimeError):
    pass


@dataclass
class Circuit:
    failures: int = 0
    opened_until: float = 0.0

    def available(self) -> bool:
        return time.monotonic() >= self.opened_until

    def fail(self) -> None:
        self.failures += 1
        if self.failures >= 3:
            self.opened_until = time.monotonic() + min(60.0, 2 ** min(self.failures - 3, 5))

    def success(self) -> None:
        self.failures = 0
        self.opened_until = 0.0


class ProviderRouter:
    """Managed -> BYOK -> local -> mock router with privacy enforcement."""

    def __init__(self, byok_key: str | None = None, ollama: OllamaEngine | None = None):
        self.byok_key = byok_key or os.getenv("NEUROPA_BYOK_KEY", "")
        self.managed_provider = os.getenv("NEUROPA_MANAGED_PROVIDER", "")
        self.managed_key = os.getenv("NEUROPA_MANAGED_KEY", "")
        self.local = ollama or OllamaEngine(os.getenv("NEUROPA_OLLAMA_URL", "http://localhost:11434"))
        self.circuits = {name: Circuit() for name in ("managed", "byok", "local")}
        self.max_attempts = 2
        self.timeout = 30

    def _cloud(self, key: str, provider: str) -> OpenAICompatEngine:
        base = provider if provider.startswith("http") else "https://api.openai.com/v1"
        return OpenAICompatEngine(key, base_url=base, models=["gpt-4o-mini"])

    def _call(self, mode: str, messages: list[dict[str, str]], model: str) -> dict[str, Any]:
        if mode == "local":
            model = model if model and model != "gpt-4o-mini" else (self.local.list_models() or ["llama3.2"])[0]
            return self.local.generate(messages, model=model, timeout=self.timeout)
        if mode == "managed":
            return self._cloud(self.managed_key, self.managed_provider).generate(messages, model=model or "gpt-4o-mini", timeout=self.timeout)
        if mode == "byok":
            return self._cloud(self.byok_key, os.getenv("NEUROPA_BYOK_PROVIDER", "https://api.openai.com/v1")).generate(messages, model=model or "gpt-4o-mini", timeout=self.timeout)
        raise RuntimeError("unknown provider")

    def _available(self, mode: str) -> bool:
        if not self.circuits[mode].available():
            return False
        if mode == "local":
            return self.local.health()
        return {"managed": bool(self.managed_key and self.managed_provider), "byok": bool(self.byok_key)}[mode]

    def generate(self, messages: list[dict[str, str]], mode: str | None = None, privacy_sensitive: bool = False, model: str = "") -> dict[str, Any]:
        modes = [mode] if mode else ["managed", "byok", "local"]
        if privacy_sensitive:
            modes = ["local"]
        started = time.perf_counter()
        last_error: Exception | None = None
        for selected in modes:
            if selected not in self.circuits or not self._available(selected):
                continue
            for attempt in range(self.max_attempts):
                try:
                    raw = self._call(selected, messages, model)
                    self.circuits[selected].success()
                    usage = raw.get("usage", {})
                    return {"text": raw.get("content", ""), "provider_used": selected, "model": raw.get("model", model), "latency_ms": round((time.perf_counter() - started) * 1000, 2), "tokens_in": usage.get("prompt_tokens", 0), "tokens_out": usage.get("completion_tokens", 0)}
                except Exception as exc:
                    last_error = exc
                    self.circuits[selected].fail()
                    if isinstance(exc, urllib.error.HTTPError) and exc.code not in (429, *range(500, 600)):
                        break
                    if attempt < self.max_attempts - 1:
                        time.sleep(min(0.5, 0.1 * (2**attempt) + random.random() * 0.1))
        raise NoAIProviderAvailable("No AI provider available") from last_error

    def status(self) -> dict[str, Any]:
        result = {}
        for mode in ("managed", "byok", "local"):
            available = self._available(mode)
            result[mode] = {"available": available, "healthy": available and self.circuits[mode].available(), "circuit_open": not self.circuits[mode].available(), "model": "ollama" if mode == "local" else "gpt-4o-mini"}
        return {"modes": result, "fallback_chain": ["managed", "byok", "local", "mock"]}

    def clarify(self, raw_text: str, mode: str | None = None, privacy_sensitive: bool = False) -> dict[str, Any]:
        system = "Eres un compresor de fricción para NeuroPA. Convierte una intención abrumadora en UNA única siguiente acción pequeña y concreta. Devuelve JSON con next_action, steps (máximo 3), estimate_range. Nunca diseñes 20 pasos ni resuelvas todo de una vez."
        result = self.generate([{"role": "system", "content": system}, {"role": "user", "content": raw_text}], mode=mode, privacy_sensitive=privacy_sensitive)
        parsed = json.loads(result["text"])
        return {"next_action": str(parsed["next_action"]), "steps": [str(x) for x in parsed.get("steps", [])][:3], "estimate_range": str(parsed.get("estimate_range", "5-15 min"))}
