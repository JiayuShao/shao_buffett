---
name: add-data-collector
description: Integrate a new financial API. Covers the 3-file workflow (data/collectors/ → data/manager.py → config/constants.py) with all gotchas.
---

# Add a Data Collector

Collectors wrap external APIs with rate limiting, retries, circuit breakers, and session management. All collectors extend `BaseCollector`.

## Step 1: Create the collector in `data/collectors/<name>.py`

```python
"""<API Name> data collector — <what it provides>."""

from typing import Any
import structlog
from data.collectors.base import BaseCollector
from data.rate_limiter import RateLimiter
from config.settings import settings

log = structlog.get_logger(__name__)

BASE_URL = "https://api.example.com/v1"


class ExampleCollector(BaseCollector):
    api_name = "example"  # Must match key in API_RATE_LIMITS

    def __init__(self, rate_limiter: RateLimiter) -> None:
        super().__init__(rate_limiter)
        self._api_key = settings.example_api_key  # Add to config/settings.py

    def _params(self, **kwargs: Any) -> dict[str, Any]:
        """Common query params (API key, etc.)."""
        return {"apikey": self._api_key, **kwargs}

    async def health_check(self) -> bool:
        """Required: check if API is reachable."""
        try:
            data = await self._request(
                f"{BASE_URL}/status", params=self._params()
            )
            return isinstance(data, dict)
        except Exception:
            return False

    async def get_data(self, symbol: str) -> dict[str, Any]:
        """Get data for a symbol."""
        data = await self._request(
            f"{BASE_URL}/data/{symbol}",
            params=self._params(),
        )
        # Normalize the response into a clean dict
        return {
            "symbol": symbol,
            "value": data.get("result", {}),
        }
```

### BaseCollector provides
- **`self._request(url, params, headers)`** — rate-limited HTTP GET with automatic retry (3 attempts, exponential backoff). Always use this instead of raw aiohttp.
- **Rate limiting** via `self.rate_limiter.acquire(self.api_name)` — called automatically by `_request()`.
- **Circuit breaker**: 401/402/403 responses open the circuit for 1 hour (no requests to that path). 404 raises `NonRetryableError` immediately.
- **Session management**: `get_session()` creates/reuses an `aiohttp.ClientSession` with 30s timeout. `close()` cleans up.
- **Retry decorator**: retries on `aiohttp.ClientError` and `TimeoutError`, not on `NonRetryableError`.

### `api_name` class attribute
Must match the key in `API_RATE_LIMITS` (config/constants.py). This is how the rate limiter knows which bucket to use.

### `health_check()` is required
Abstract method — must return `True`/`False`. Used by `DataManager.health_check()` and the `/admin health` command.

### If the API needs no key (public API)
Skip `settings` import and `_api_key`. Example: `PolymarketCollector` uses the public Gamma API with no authentication.

### If POST requests are needed
`BaseCollector._request()` only supports GET. For POST, add a method:

```python
async def _post(self, url: str, json_data: dict) -> dict[str, Any]:
    await self.rate_limiter.acquire(self.api_name)
    session = await self.get_session()
    async with session.post(url, json=json_data) as resp:
        resp.raise_for_status()
        return await resp.json()
```

## Step 2: Register in `data/manager.py`

### 2a. Import and initialize

```python
# At top of file:
from data.collectors.example import ExampleCollector

# In __init__():
self.example = ExampleCollector(self.rate_limiter)
```

### 2b. Add to close()

```python
async def close(self) -> None:
    collectors = [
        self.finnhub, self.fred, self.marketaux, self.fmp,
        self.sec_edgar, self.arxiv, self.polymarket,
        self.example,  # <-- add here
    ]
    ...
```

### 2c. Add to health_check()

```python
checks = {
    ...
    "example": self.example,
}
```

### 2d. Add cached data access methods

```python
async def get_example_data(self, symbol: str) -> dict[str, Any]:
    """Get example data with caching."""
    key = f"example:{symbol}"
    cached = self.cache.get(key)
    if cached:
        return cached
    data = await self.example.get_data(symbol)
    self.cache.set(key, data, CACHE_TTL["fundamentals"])  # Pick appropriate TTL
    return data
```

## Step 3: Add rate limits in `config/constants.py`

```python
API_RATE_LIMITS = {
    ...
    "example": 30,  # requests per minute
}
```

Leave headroom below the API's actual limit (e.g., if the limit is 60/min, configure 55).

## Step 4 (optional): Add the API key to settings

In `config/settings.py`, add:

```python
example_api_key: str = os.environ.get("EXAMPLE_API_KEY", "")
```

And in `.env` / Docker env:

```
EXAMPLE_API_KEY=your_key_here
```

## Gotchas

- **Always use `self._request()`** — never call `aiohttp` directly. The base method handles rate limiting, retries, and circuit breaking.
- **Normalize responses** — collectors should return clean dicts with consistent keys, not raw API responses.
- **Type hints**: return `dict[str, Any]` or `list[dict[str, Any]]` — use Python 3.14+ syntax (lowercase `dict`, `list`, `|` for unions).
- **Error handling**: let exceptions propagate from `_request()`. The data manager and engine handle errors at their level.
- **No caching in collectors** — caching lives in `DataManager` methods, not in collectors.
- **Log sparingly**: use `structlog.get_logger(__name__)` and log only notable events (not every request).

## Checklist

- [ ] Collector class in `data/collectors/<name>.py` extending `BaseCollector`
- [ ] `api_name` class attribute set (matches rate limit key)
- [ ] `health_check()` implemented
- [ ] All HTTP via `self._request()` (not raw aiohttp)
- [ ] Registered in `data/manager.py` (init, close, health_check, access methods)
- [ ] Rate limit added in `config/constants.py`
- [ ] API key in `config/settings.py` (if needed)
- [ ] Response data normalized to clean dicts
