"""Polymarket prediction market data collector."""

import structlog
from typing import Any
from data.collectors.base import BaseCollector
from data.rate_limiter import RateLimiter

log = structlog.get_logger(__name__)

GAMMA_API_BASE = "https://gamma-api.polymarket.com"


class PolymarketCollector(BaseCollector):
    """Collects prediction market data from Polymarket's public CLOB/Gamma API."""

    api_name = "polymarket"

    def __init__(self, rate_limiter: RateLimiter) -> None:
        super().__init__(rate_limiter)

    async def search_markets(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search for prediction markets by keyword."""
        data = await self._request(
            f"{GAMMA_API_BASE}/markets",
            params={
                "limit": limit,
                "active": "true",
                "closed": "false",
                "order": "volume",
                "ascending": "false",
                "tag_slug": "",
                "q": query,
            },
        )
        if not isinstance(data, list):
            return []

        results = []
        for market in data[:limit]:
            results.append({
                "question": market.get("question", ""),
                "description": (market.get("description") or "")[:300],
                "outcome_prices": market.get("outcomePrices", ""),
                "outcomes": market.get("outcomes", ""),
                "volume": market.get("volume", 0),
                "liquidity": market.get("liquidity", 0),
                "end_date": market.get("endDate"),
                "active": market.get("active", False),
                "slug": market.get("slug", ""),
            })
        return results

    async def health_check(self) -> bool:
        """Check if Polymarket API is reachable."""
        try:
            data = await self._request(
                f"{GAMMA_API_BASE}/markets",
                params={"limit": 1, "active": "true"},
            )
            return isinstance(data, list) and len(data) > 0
        except Exception:
            return False
