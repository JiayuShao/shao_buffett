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

    async def get_trending_entities(
        self,
        entity_types: str = "equity",
        countries: str = "us",
        limit: int = 10,
        published_after: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get trending entities by news volume and sentiment."""
        params = self._params(
            entity_types=entity_types,
            countries=countries,
            limit=limit,
            language="en",
            sort="total_documents",
            sort_order="desc",
        )
        if published_after:
            params["published_after"] = published_after

        data = await self._request(f"{BASE_URL}/entity/trending/aggregation", params=params)
        entities = data.get("data", [])

        return [
            {
                "symbol": e.get("key", ""),
                "name": e.get("name", ""),
                "type": e.get("type", ""),
                "industry": e.get("industry", ""),
                "country": e.get("country", ""),
                "total_documents": e.get("total_documents", 0),
                "sentiment_avg": e.get("sentiment_avg"),
                "sentiment_positive": e.get("doc_count_sentiment_positive", 0),
                "sentiment_negative": e.get("doc_count_sentiment_negative", 0),
                "sentiment_neutral": e.get("doc_count_sentiment_neutral", 0),
            }
            for e in entities
        ]

    async def get_sentiment_stats(
        self,
        symbols: str,
        interval: str = "day",
        limit: int = 7,
    ) -> dict[str, Any]:
        """Get sentiment time series for symbols."""
        params = self._params(
            symbols=symbols,
            interval=interval,
            limit=limit,
            language="en",
        )

        data = await self._request(f"{BASE_URL}/entity/stats/intraday", params=params)
        entities = data.get("data", [])

        result: dict[str, Any] = {}
        for entity in entities:
            symbol = entity.get("key", "")
            result[symbol] = {
                "name": entity.get("name", ""),
                "total_documents": entity.get("total_documents", 0),
                "sentiment_avg": entity.get("sentiment_avg"),
                "timeline": [
                    {
                        "date": point.get("date", ""),
                        "articles": point.get("total_documents", 0),
                        "sentiment_avg": point.get("sentiment_avg"),
                        "positive": point.get("doc_count_sentiment_positive", 0),
                        "negative": point.get("doc_count_sentiment_negative", 0),
                        "neutral": point.get("doc_count_sentiment_neutral", 0),
                    }
                    for point in entity.get("data", [])
                ],
            }
        return result
