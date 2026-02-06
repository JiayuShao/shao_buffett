"""Per-API sliding window rate limiter."""

import asyncio
import time
from collections import defaultdict


class RateLimiter:
    """Sliding window rate limiter for API calls."""

    def __init__(self) -> None:
        self._windows: dict[str, list[float]] = defaultdict(list)
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._limits: dict[str, int] = {}

    def configure(self, api_name: str, requests_per_minute: int) -> None:
        """Set rate limit for an API."""
        self._limits[api_name] = requests_per_minute

    async def acquire(self, api_name: str) -> None:
        """Wait until a request slot is available."""
        limit = self._limits.get(api_name, 60)
        async with self._locks[api_name]:
            now = time.monotonic()
            window = self._windows[api_name]

            # Remove entries older than 60 seconds
            window[:] = [t for t in window if now - t < 60.0]

            if len(window) >= limit:
                # Wait until the oldest entry expires
                wait_time = 60.0 - (now - window[0])
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    # Clean up again after waiting
                    now = time.monotonic()
                    window[:] = [t for t in window if now - t < 60.0]

            window.append(time.monotonic())
