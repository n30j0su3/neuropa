from .router import NoAIProviderAvailable, ProviderRouter
from .opencode_cli import DEFAULT_MODEL, OpenCodeCLI, OpenCodeError, OpenCodeTimeout, OpenCodeUnavailable, parse_jsonl

# Compatibility name for callers migrating from the vendored MultiEngine.
MultiEngine = ProviderRouter

__all__ = ["MultiEngine", "NoAIProviderAvailable", "ProviderRouter", "OpenCodeCLI", "OpenCodeError", "OpenCodeTimeout", "OpenCodeUnavailable", "DEFAULT_MODEL", "parse_jsonl"]
