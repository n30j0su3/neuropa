from __future__ import annotations

import json
import os
from typing import Any

from neuropa.core.providers.multi_engine import OllamaEngine, OpenAICompatEngine
from .opencode_cli import DEFAULT_MODEL, OpenCodeCLI


class NoAIProviderAvailable(RuntimeError):
    pass


class ProviderRouter:
    """Honest provider routing: free OpenCode, local Ollama, then explicit cloud."""

    def __init__(self, byok_key: str | None = None, ollama: OllamaEngine | None = None, opencode: OpenCodeCLI | None = None):
        self.byok_key = byok_key or os.getenv("NEUROPA_BYOK_KEY", "")
        self.managed_provider = os.getenv("NEUROPA_MANAGED_PROVIDER", "")
        self.managed_key = os.getenv("NEUROPA_MANAGED_KEY", "")
        self.local = ollama or OllamaEngine(os.getenv("NEUROPA_OLLAMA_URL", "http://localhost:11434"))
        self.opencode = opencode or OpenCodeCLI(timeout=int(os.getenv("NEUROPA_OPENCODE_TIMEOUT", "120")))
        self.timeout = 30

    def _cloud(self, key: str, provider: str) -> OpenAICompatEngine:
        return OpenAICompatEngine(key, base_url=provider if provider.startswith("http") else "https://api.openai.com/v1", models=["gpt-4o-mini"])

    def _call(self, mode: str, messages: list[dict[str, str]], model: str, workspace: str | None = None) -> dict[str, Any]:
        if mode == "opencode_free":
            return self.opencode.generate(messages, model=model or DEFAULT_MODEL, workspace=workspace, timeout=self.timeout)
        if mode == "local":
            selected = model if model and not model.startswith("opencode/") else (self.local.list_models() or ["llama3.2"])[0]
            return self.local.generate(messages, model=selected, timeout=self.timeout)
        if mode == "managed":
            return self._cloud(self.managed_key, self.managed_provider).generate(messages, model=model or "gpt-4o-mini", timeout=self.timeout)
        if mode == "byok":
            return self._cloud(self.byok_key, os.getenv("NEUROPA_BYOK_PROVIDER", "https://api.openai.com/v1")).generate(messages, model=model or "gpt-4o-mini", timeout=self.timeout)
        raise RuntimeError("unknown provider")

    def _available(self, mode: str) -> bool:
        if mode == "opencode_free": return self.opencode.health()
        if mode == "local": return self.local.health()
        return bool((self.managed_key and self.managed_provider) if mode == "managed" else self.byok_key)

    def _validate_model(self, mode: str, model: str) -> None:
        if not model:
            return
        catalog = self.opencode.list_models() if mode == "opencode_free" else self.local.list_models() if mode == "local" else ["gpt-4o-mini"] if (mode == "byok" and self.byok_key) or (mode == "managed" and self.managed_key and self.managed_provider) else []
        if catalog and model not in catalog:
            raise ValueError("model no está disponible en el catálogo del provider")

    def generate(self, messages: list[dict[str, str]], mode: str | None = None, privacy_sensitive: bool = False, model: str = "", workspace: str | None = None) -> dict[str, Any]:
        if privacy_sensitive:
            modes = ["local"]
        elif mode:
            modes = [mode]
        else:
            modes = ["opencode_free", "local", "byok", "managed"]
        last_error: Exception | None = None
        for selected in modes:
            # Preserve compatibility with callers replacing the legacy _call hook in tests/adapters.
            if selected == "opencode_free" and getattr(self._call, "__self__", None) is not self:
                continue
            if selected not in {"opencode_free", "local", "byok", "managed"} or not self._available(selected):
                continue
            try:
                self._validate_model(selected, model)
                raw = self._call(selected, messages, model, workspace) if workspace is not None else self._call(selected, messages, model)
                usage = raw.get("usage", {})
                return {"text": raw.get("text", raw.get("content", "")), "provider_used": raw.get("provider_used", selected), "model": raw.get("model", model), "session_id": raw.get("session_id"), "usage": usage, "tokens_in": usage.get("input", usage.get("prompt_tokens", 0)), "tokens_out": usage.get("output", usage.get("completion_tokens", 0))}
            except Exception as exc:
                last_error = exc
        raise NoAIProviderAvailable("No hay un provider de IA disponible para esta solicitud") from last_error

    def status(self) -> dict[str, Any]:
        op_available = self.opencode.health()
        local_available = self.local.health()
        op_models = self.opencode.list_models() if op_available else []
        local_models = self.local.list_models() if local_available else []
        modes = {
            "opencode_free": {
                "available": op_available, "healthy": op_available,
                "description": "OpenCode CLI con modelos gratuitos",
                "privacy": "remote/free", "privacy_label": "remote/free",
                "cost": "free", "cost_label": "free", "models": op_models,
                "recommended_model": DEFAULT_MODEL if DEFAULT_MODEL in op_models else None,
                "model": DEFAULT_MODEL,
            },
            "local": {
                "available": local_available, "healthy": local_available,
                "description": "Modelos locales vía Ollama",
                "privacy": "local", "privacy_label": "local", "cost": "free", "cost_label": "free",
                "models": local_models,
                "recommended_model": local_models[0] if local_models else None,
            },
            "byok": {
                "available": bool(self.byok_key), "healthy": bool(self.byok_key),
                "description": "Proveedor cloud con clave propia",
                "privacy": "remote/byok", "privacy_label": "remote/byok", "cost": "variable", "cost_label": "variable",
                "models": ["gpt-4o-mini"] if self.byok_key else [],
                "recommended_model": "gpt-4o-mini" if self.byok_key else None,
            },
            "managed": {
                "available": bool(self.managed_key and self.managed_provider),
                "healthy": bool(self.managed_key and self.managed_provider),
                "description": "Proveedor cloud gestionado",
                "privacy": "remote/managed", "privacy_label": "remote/managed", "cost": "variable", "cost_label": "variable",
                "models": ["gpt-4o-mini"] if self.managed_key and self.managed_provider else [],
                "recommended_model": "gpt-4o-mini" if self.managed_key and self.managed_provider else None,
            },
        }
        return {"modes": modes, "providers": modes, "fallback_chain": ["opencode_free", "local", "byok", "managed"]}

    def clarify(self, raw_text: str, mode: str | None = None, privacy_sensitive: bool = False) -> dict[str, Any]:
        system = "Convierte un pensamiento abrumador en UNA siguiente acción pequeña. Responde JSON con next_action, steps (máximo 3), estimate_range. No expongas razonamiento privado."
        result = self.generate([{"role": "system", "content": system}, {"role": "user", "content": raw_text}], mode=mode, privacy_sensitive=privacy_sensitive)
        parsed = json.loads(result["text"])
        return {"next_action": str(parsed["next_action"]), "steps": [str(x) for x in parsed.get("steps", [])][:3], "estimate_range": str(parsed.get("estimate_range", "5-15 min"))}
