from .router import NoAIProviderAvailable, ProviderRouter

# Compatibility name for callers migrating from the vendored MultiEngine.
MultiEngine = ProviderRouter

__all__ = ["MultiEngine", "NoAIProviderAvailable", "ProviderRouter"]
