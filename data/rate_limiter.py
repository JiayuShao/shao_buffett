"""Per-API sliding window rate limiter with limit notifications."""

import asyncio
import time
from collections import defaultdict
from typing import Callable, Awaitable


class RateLimiter:
    """Sliding window rate limiter for API calls."""

    def __init__(self) -> None:
        self._windows: dict[str, list[float]] = defaultdict(list)
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._limits: dict[str, int] = {}
        # Track when we last notified about a throttle per API (avoid spam)
        self._last_throttle_notify: dict[str, float] = {}
        # Callback for rate limit events: async fn(api_name, wait_seconds)
        self.on_rate_limit: Callable[[str, float], Awaitable[None]] | None = None

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
                    await self._notify_rate_limit(api_name, wait_time)
                    await asyncio.sleep(wait_time)
                    # Clean up again after waiting
                    now = time.monotonic()
                    window[:] = [t for t in window if now - t < 60.0]

            window.append(time.monotonic())

    async def _notify_rate_limit(self, api_name: str, wait_seconds: float) -> None:
        """Fire the rate limit callback, but debounce to once per 5 minutes per API."""
        if self.on_rate_limit is None:
            return
        now = time.monotonic()
        last = self._last_throttle_notify.get(api_name, 0.0)
        if now - last < 300.0:  # 5 min debounce
            return
        self._last_throttle_notify[api_name] = now
        try:
            await self.on_rate_limit(api_name, wait_seconds)
        except Exception:
            pass  # Don't let notification failures break the rate limiter

    def get_usage(self) -> dict[str, dict[str, int]]:
        """Get current usage stats for all APIs."""
        now = time.monotonic()
        stats = {}
        for api_name, limit in self._limits.items():
            window = self._windows.get(api_name, [])
            active = sum(1 for t in window if now - t < 60.0)
            stats[api_name] = {"used": active, "limit": limit}
        return stats
