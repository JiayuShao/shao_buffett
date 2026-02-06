"""Data manager — orchestrates collectors and cache."""

from typing import Any
import structlog
from data.cache import TTLCache
from data.rate_limiter import RateLimiter
from data.collectors.finnhub import FinnhubCollector
from data.collectors.fred import FredCollector
from data.collectors.marketaux import MarketAuxCollector
from data.collectors.fmp import FMPCollector
from data.collectors.sec_edgar import SECEdgarCollector
from data.collectors.arxiv_research import ArxivCollector
from config.constants import API_RATE_LIMITS, CACHE_TTL

log = structlog.get_logger(__name__)


class DataManager:
    """Central orchestrator for all data collectors with caching."""

    def __init__(self) -> None:
        self.cache = TTLCache()
        self.rate_limiter = RateLimiter()

        # Configure rate limits
        for api_name, limit in API_RATE_LIMITS.items():
            self.rate_limiter.configure(api_name, limit)

        # Initialize collectors
        self.finnhub = FinnhubCollector(self.rate_limiter)
        self.fred = FredCollector(self.rate_limiter)
        self.marketaux = MarketAuxCollector(self.rate_limiter)
        self.fmp = FMPCollector(self.rate_limiter)
        self.sec_edgar = SECEdgarCollector(self.rate_limiter)
        self.arxiv = ArxivCollector(self.rate_limiter)

    async def start(self) -> None:
        """Initialize all collectors."""
        log.info("data_manager_starting")

    async def close(self) -> None:
        """Close all collector sessions."""
        collectors = [self.finnhub, self.fred, self.marketaux, self.fmp, self.sec_edgar, self.arxiv]
        for collector in collectors:
            await collector.close()
        await self.finnhub.stop_websocket()
        log.info("data_manager_closed")

    async def health_check(self) -> dict[str, bool]:
        """Check health of all APIs."""
        results = {}
        checks = {
            "finnhub": self.finnhub,
            "fred": self.fred,
            "marketaux": self.marketaux,
            "fmp": self.fmp,
            "sec_edgar": self.sec_edgar,
            "arxiv": self.arxiv,
        }
        for name, collector in checks.items():
            try:
                results[name] = await collector.health_check()
            except Exception:
                results[name] = False
        return results

    # ── Cached data access methods ──

    async def get_quote(self, symbol: str) -> dict[str, Any]:
        """Get stock quote with caching."""
        key = f"quote:{symbol}"
        cached = self.cache.get(key)
        if cached:
            return cached
        data = await self.finnhub.get_quote(symbol)
        self.cache.set(key, data, CACHE_TTL["quote"])
        return data

    async def get_company_profile(self, symbol: str) -> dict[str, Any]:
        """Get company profile with caching."""
        key = f"profile:{symbol}"
        cached = self.cache.get(key)
        if cached:
            return cached
        # Try FMP first for richer data, fall back to Finnhub
        try:
            data = await self.fmp.get_profile(symbol)
        except Exception:
            data = await self.finnhub.get_company_profile(symbol)
        self.cache.set(key, data, CACHE_TTL["profile"])
        return data

    async def get_fundamentals(self, symbol: str) -> dict[str, Any]:
        """Get key financial metrics."""
        key = f"fundamentals:{symbol}"
        cached = self.cache.get(key)
        if cached:
            return cached
        try:
            metrics = await self.fmp.get_key_metrics(symbol, limit=1)
            ratios = await self.fmp.get_ratios(symbol, limit=1)
            data = {
                "metrics": metrics[0] if metrics else {},
                "ratios": ratios[0] if ratios else {},
            }
        except Exception:
            data = {"metrics": {}, "ratios": {}}
        self.cache.set(key, data, CACHE_TTL["fundamentals"])
        return data

    async def get_analyst_data(self, symbol: str) -> dict[str, Any]:
        """Get analyst recommendations and price targets."""
        key = f"analyst:{symbol}"
        cached = self.cache.get(key)
        if cached:
            return cached
        recs = await self.finnhub.get_analyst_recommendations(symbol)
        target = await self.finnhub.get_price_target(symbol)
        upgrades = await self.finnhub.get_upgrade_downgrade(symbol)
        data = {
            "recommendations": recs[:5] if recs else [],
            "price_target": target,
            "upgrades_downgrades": upgrades[:10] if upgrades else [],
        }
        self.cache.set(key, data, CACHE_TTL["analyst"])
        return data

    async def get_earnings(self, symbol: str) -> list[dict[str, Any]]:
        """Get earnings history."""
        key = f"earnings:{symbol}"
        cached = self.cache.get(key)
        if cached:
            return cached
        data = await self.finnhub.get_earnings(symbol)
        self.cache.set(key, data, CACHE_TTL["earnings"])
        return data

    async def get_news(
        self, symbol: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get news, optionally filtered by symbol."""
        key = f"news:{symbol or 'general'}:{limit}"
        cached = self.cache.get(key)
        if cached:
            return cached
        if symbol:
            data = await self.marketaux.get_news_for_symbol(symbol, limit=limit)
        else:
            data = await self.marketaux.get_news(limit=limit)
        self.cache.set(key, data, CACHE_TTL["news"])
        return data

    async def get_macro_data(self, series_id: str | None = None) -> Any:
        """Get macro economic data."""
        if series_id:
            key = f"macro:{series_id}"
            cached = self.cache.get(key)
            if cached:
                return cached
            data = await self.fred.get_series(series_id)
            self.cache.set(key, data, CACHE_TTL["macro"])
            return data
        else:
            key = "macro:snapshot"
            cached = self.cache.get(key)
            if cached:
                return cached
            data = await self.fred.get_macro_snapshot()
            self.cache.set(key, data, CACHE_TTL["macro"])
            return data

    async def get_earnings_transcript(
        self, symbol: str, year: int, quarter: int
    ) -> dict[str, Any]:
        """Get earnings call transcript."""
        key = f"transcript:{symbol}:{year}:{quarter}"
        cached = self.cache.get(key)
        if cached:
            return cached
        data = await self.fmp.get_earnings_transcript(symbol, year, quarter)
        self.cache.set(key, data, CACHE_TTL["transcript"])
        return data

    async def get_sec_filings(
        self, symbol: str, form_types: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Get SEC filings for a company."""
        key = f"filings:{symbol}:{form_types}"
        cached = self.cache.get(key)
        if cached:
            return cached
        data = await self.sec_edgar.get_company_filings(symbol, form_types=form_types)
        self.cache.set(key, data, CACHE_TTL["filing"])
        return data

    async def get_sector_performance(self) -> list[dict[str, Any]]:
        """Get sector performance data."""
        key = "sector_perf"
        cached = self.cache.get(key)
        if cached:
            return cached
        data = await self.fmp.get_sector_performance()
        self.cache.set(key, data, CACHE_TTL["fundamentals"])
        return data

    async def get_research_papers(
        self, query: str | None = None, max_results: int = 10
    ) -> list[dict[str, Any]]:
        """Get quantitative finance research papers."""
        if query:
            return await self.arxiv.search_papers(query=query, max_results=max_results)
        return await self.arxiv.get_recent_papers(max_results=max_results)
