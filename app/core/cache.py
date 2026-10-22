"""Simple in-memory TTL cache for TinyFish API results."""

import time
from typing import Any

_cache: dict[str, tuple[float, Any]] = {}

DEFAULT_TTL = 600  # 10 minutes


def cache_get(key: str) -> Any | None:
    """Get a cached value if it exists and hasn't expired."""
    if key in _cache:
        expires_at, value = _cache[key]
        if time.time() < expires_at:
            return value
        del _cache[key]
    return None


def cache_set(key: str, value: Any, ttl: int = DEFAULT_TTL):
    """Store a value in the cache with a TTL in seconds."""
    _cache[key] = (time.time() + ttl, value)


def cache_clear():
    """Clear the entire cache."""
    _cache.clear()
