"""Base collector with retry, backoff, circuit breaker, and rate limiting."""

import time
import aiohttp
import structlog
from abc import ABC, abstractmethod
from typing import Any
from urllib.parse import urlparse
from data.rate_limiter import RateLimiter
from utils.retry import async_retry

log = structlog.get_logger(__name__)

# Circuit breaker: skip URLs that returned 403 for 1 hour
_CIRCUIT_OPEN: dict[str, float] = {}  # url_path -> expiry timestamp
_CIRCUIT_TTL = 3600.0  # 1 hour


class NonRetryableError(Exception):
    """Raised for HTTP errors that should NOT be retried (403, 401, 404)."""

    def __init__(self, status: int, message: str) -> None:
        self.status = status
        super().__init__(message)


class BaseCollector(ABC):
    """Abstract base class for all data collectors."""

    api_name: str = "unknown"

    def __init__(self, rate_limiter: RateLimiter) -> None:
        self.rate_limiter = rate_limiter
        self._session: aiohttp.ClientSession | None = None

    async def get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"User-Agent": "ShaoBuffett/0.1 (Financial Agent)"},
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    @async_retry(max_retries=3, base_delay=1.0, exceptions=(aiohttp.ClientError, TimeoutError))
    async def _request(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any] | list[Any]:
        """Make a rate-limited HTTP GET request with retry."""
        # Circuit breaker: skip URLs known to 403
        url_path = f"{self.api_name}:{urlparse(url).path}"
        if url_path in _CIRCUIT_OPEN:
            if time.monotonic() < _CIRCUIT_OPEN[url_path]:
                raise NonRetryableError(403, f"Circuit open for {url_path}")
            else:
                del _CIRCUIT_OPEN[url_path]

        await self.rate_limiter.acquire(self.api_name)
        session = await self.get_session()

        async with session.get(url, params=params, headers=headers) as resp:
            if resp.status == 429:
                log.warning("rate_limited_by_server", api=self.api_name, url=url)
                if self.rate_limiter.on_rate_limit:
                    try:
                        await self.rate_limiter.on_rate_limit(self.api_name, 0.0)
                    except Exception:
                        pass
                raise aiohttp.ClientError("Rate limited")
            if resp.status in (401, 402, 403):
                log.warning("non_retryable_http_error", api=self.api_name, status=resp.status, url=url)
                _CIRCUIT_OPEN[url_path] = time.monotonic() + _CIRCUIT_TTL
                raise NonRetryableError(resp.status, f"HTTP {resp.status} for {url}")
            if resp.status == 404:
                raise NonRetryableError(resp.status, f"HTTP 404 for {url}")
            resp.raise_for_status()
            return await resp.json()

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the API is reachable."""
        ...
