"""MarketAux financial news collector with sentiment."""

from typing import Any
import structlog
from data.collectors.base import BaseCollector
from data.rate_limiter import RateLimiter
from config.settings import settings

log = structlog.get_logger(__name__)

BASE_URL = "https://api.marketaux.com/v1"


class MarketAuxCollector(BaseCollector):
    api_name = "marketaux"

    def __init__(self, rate_limiter: RateLimiter) -> None:
        super().__init__(rate_limiter)
        self._api_key = settings.marketaux_api_key

    def _params(self, **kwargs: Any) -> dict[str, Any]:
        return {"api_token": self._api_key, **kwargs}

    async def health_check(self) -> bool:
        try:
            data = await self._request(
                f"{BASE_URL}/news/all", params=self._params(limit=1)
            )
            return "data" in data
        except Exception:
            return False

    async def get_news(
        self,
        symbols: str | None = None,
        sectors: str | None = None,
        limit: int = 10,
        language: str = "en",
    ) -> list[dict[str, Any]]:
        """Get financial news with sentiment scores."""
        params = self._params(limit=limit, language=language)
        if symbols:
            params["symbols"] = symbols
        if sectors:
            params["industries"] = sectors

        data = await self._request(f"{BASE_URL}/news/all", params=params)
        articles = data.get("data", [])

        return [
            {
                "title": a.get("title", ""),
                "description": a.get("description", ""),
                "snippet": a.get("snippet", ""),
                "url": a.get("url", ""),
                "source": a.get("source", ""),
                "published_at": a.get("published_at", ""),
                "symbols": [e.get("symbol") for e in a.get("entities", []) if e.get("symbol")],
                "sentiment": a.get("entities", [{}])[0].get("sentiment_score") if a.get("entities") else None,
                "relevance": a.get("entities", [{}])[0].get("match_score") if a.get("entities") else None,
            }
            for a in articles
        ]

    async def get_news_for_symbol(self, symbol: str, limit: int = 5) -> list[dict[str, Any]]:
        """Get news specifically for one symbol."""
        return await self.get_news(symbols=symbol, limit=limit)
