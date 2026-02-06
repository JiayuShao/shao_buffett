"""In-memory TTL cache."""

import time
from typing import Any


class TTLCache:
    """Simple in-memory cache with per-key TTL."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Any | None:
        """Get a cached value, or None if expired/missing."""
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.time() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: int) -> None:
        """Set a value with TTL in seconds."""
        self._store[key] = (value, time.time() + ttl)

    def delete(self, key: str) -> None:
        """Remove a key."""
        self._store.pop(key, None)

    def clear(self) -> None:
        """Clear all entries."""
        self._store.clear()

    def cleanup(self) -> int:
        """Remove expired entries. Returns count of removed entries."""
        now = time.time()
        expired = [k for k, (_, exp) in self._store.items() if now > exp]
        for k in expired:
            del self._store[k]
        return len(expired)
