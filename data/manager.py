"""Data manager — orchestrates collectors and cache."""

import asyncio
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
from data.collectors.polymarket import PolymarketCollector
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
        self.polymarket = PolymarketCollector(self.rate_limiter)

    async def start(self) -> None:
        """Initialize all collectors."""
        log.info("data_manager_starting")

    async def close(self) -> None:
        """Close all collector sessions."""
        collectors = [self.finnhub, self.fred, self.marketaux, self.fmp, self.sec_edgar, self.arxiv, self.polymarket]
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
            "polymarket": self.polymarket,
        }
        for name, collector in checks.items():
            try:
                results[name] = await collector.health_check()
            except Exception:
                results[name] = False
        return results

    # ── Cached data access methods ──

    async def get_quote(self, symbol: str) -> dict[str, Any]:
        """Get stock quote with caching. Uses FMP (saves Finnhub budget)."""
        key = f"quote:{symbol}"
        cached = self.cache.get(key)
        if cached:
            return cached
        try:
            data = await self.fmp.get_quote(symbol)
        except Exception:
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
        """Get analyst recommendations (Finnhub) + estimates (FMP)."""
        key = f"analyst:{symbol}"
        cached = self.cache.get(key)
        if cached:
            return cached

        # Finnhub: recommendations (free). FMP: estimates (free tier).
        # upgrade-downgrade and price-target are Finnhub premium — skipped.
        recs, estimates = await asyncio.gather(
            self.finnhub.get_analyst_recommendations(symbol),
            self.fmp.get_analyst_estimates(symbol),
            return_exceptions=True,
        )
        data = {
            "recommendations": (recs[:5] if isinstance(recs, list) else []),
            "estimates": (estimates[:3] if isinstance(estimates, list) else []),
            "upgrades_downgrades": [],
        }
        self.cache.set(key, data, CACHE_TTL["analyst"])
        return data

    async def get_earnings(self, symbol: str) -> list[dict[str, Any]]:
        """Get earnings history. Falls back Finnhub → FMP."""
        key = f"earnings:{symbol}"
        cached = self.cache.get(key)
        if cached:
            return cached
        try:
            data = await self.finnhub.get_earnings(symbol)
        except Exception:
            data = []
        self.cache.set(key, data, CACHE_TTL["earnings"])
        return data

    async def get_news(
        self, symbol: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get news, optionally filtered by symbol. Falls back MarketAux → Finnhub."""
        key = f"news:{symbol or 'general'}:{limit}"
        cached = self.cache.get(key)
        if cached:
            return cached

        data: list[dict[str, Any]] = []
        # Try MarketAux first (richer sentiment data)
        try:
            if symbol:
                data = await self.marketaux.get_news_for_symbol(symbol, limit=limit)
            else:
                data = await self.marketaux.get_news(limit=limit)
        except Exception:
            pass

        # Fallback to Finnhub company news if MarketAux failed
        if not data and symbol:
            try:
                from datetime import datetime, timedelta
                to_date = datetime.utcnow().strftime("%Y-%m-%d")
                from_date = (datetime.utcnow() - timedelta(days=2)).strftime("%Y-%m-%d")
                finnhub_articles = await self.finnhub.get_company_news(symbol, from_date, to_date)
                log.info("finnhub_news_fallback", symbol=symbol, articles=len(finnhub_articles))
                data = [
                    {
                        "title": a.get("headline", ""),
                        "description": a.get("summary", ""),
                        "snippet": a.get("summary", "")[:200],
                        "url": a.get("url", ""),
                        "source": a.get("source", ""),
                        "published_at": a.get("datetime", ""),
                        "symbols": [symbol],
                        "sentiment": None,
                        "relevance": None,
                    }
                    for a in finnhub_articles[:limit]
                ]
            except Exception:
                pass

        # Fallback to Finnhub general news if no symbol
        if not data and not symbol:
            try:
                finnhub_articles = await self.finnhub.get_general_news()
                log.info("finnhub_general_news_fallback", articles=len(finnhub_articles))
                data = [
                    {
                        "title": a.get("headline", ""),
                        "description": a.get("summary", ""),
                        "snippet": a.get("summary", "")[:200],
                        "url": a.get("url", ""),
                        "source": a.get("source", ""),
                        "published_at": a.get("datetime", ""),
                        "symbols": [],
                        "sentiment": None,
                        "relevance": None,
                    }
                    for a in finnhub_articles[:limit]
                ]
            except Exception:
                pass

        if data:
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

    async def get_news_batch(
        self, symbols: list[str], limit: int = 15
    ) -> list[dict[str, Any]]:
        """Get news for multiple symbols in a single MarketAux API call.

        Falls back to per-symbol Finnhub if MarketAux fails.
        """
        key = f"news:batch:{','.join(sorted(symbols))}:{limit}"
        cached = self.cache.get(key)
        if cached:
            return cached

        data: list[dict[str, Any]] = []
        # MarketAux supports comma-separated symbols in one call
        try:
            joined = ",".join(symbols)
            data = await self.marketaux.get_news(symbols=joined, limit=limit)
            log.info("marketaux_batch_news", symbols=len(symbols), articles=len(data))
        except Exception:
            pass

        # Fallback: per-symbol Finnhub (more expensive but always works)
        if not data:
            from datetime import datetime, timedelta
            to_date = datetime.utcnow().strftime("%Y-%m-%d")
            from_date = (datetime.utcnow() - timedelta(days=2)).strftime("%Y-%m-%d")
            for symbol in symbols:
                try:
                    finnhub_articles = await self.finnhub.get_company_news(symbol, from_date, to_date)
                    log.info("finnhub_news_fallback", symbol=symbol, articles=len(finnhub_articles))
                    data.extend(
                        {
                            "title": a.get("headline", ""),
                            "description": a.get("summary", ""),
                            "snippet": a.get("summary", "")[:200],
                            "url": a.get("url", ""),
                            "source": a.get("source", ""),
                            "published_at": a.get("datetime", ""),
                            "symbols": [symbol],
                            "sentiment": None,
                            "relevance": None,
                        }
                        for a in finnhub_articles[:5]
                    )
                except Exception:
                    pass

        if data:
            self.cache.set(key, data, CACHE_TTL["news"])
        return data

    async def get_news_for_sectors(
        self, sectors: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get news filtered by MarketAux industry sectors."""
        key = f"news:sectors:{sectors}:{limit}"
        cached = self.cache.get(key)
        if cached:
            return cached
        data = await self.marketaux.get_news(sectors=sectors, limit=limit)
        self.cache.set(key, data, CACHE_TTL["news"])
        return data

    async def get_polymarket(
        self, query: str, limit: int = 5
    ) -> list[dict[str, Any]]:
        """Get prediction market data from Polymarket."""
        key = f"polymarket:{query}:{limit}"
        cached = self.cache.get(key)
        if cached:
            return cached
        data = await self.polymarket.search_markets(query, limit=limit)
        self.cache.set(key, data, CACHE_TTL["news"])  # Same TTL as news (5 min)
        return data

    async def get_technical_indicators(self, symbol: str) -> dict[str, Any]:
        """Get technical analysis indicators: SMA, RSI, EMA, MACD."""
        key = f"technicals:{symbol}"
        cached = self.cache.get(key)
        if cached:
            return cached

        # Fetch all indicators in parallel
        sma_20, sma_50, sma_200, rsi_14, ema_12, ema_26 = await asyncio.gather(
            self.fmp.get_technical_indicator(symbol, "sma", period=20),
            self.fmp.get_technical_indicator(symbol, "sma", period=50),
            self.fmp.get_technical_indicator(symbol, "sma", period=200),
            self.fmp.get_technical_indicator(symbol, "rsi", period=14),
            self.fmp.get_technical_indicator(symbol, "ema", period=12),
            self.fmp.get_technical_indicator(symbol, "ema", period=26),
        )

        # Compute MACD from EMA-12 and EMA-26
        ema12_val = ema_12[0].get("ema") if ema_12 else None
        ema26_val = ema_26[0].get("ema") if ema_26 else None
        macd = (ema12_val - ema26_val) if ema12_val is not None and ema26_val is not None else None

        data = {
            "symbol": symbol,
            "sma_20": sma_20[0].get("sma") if sma_20 else None,
            "sma_50": sma_50[0].get("sma") if sma_50 else None,
            "sma_200": sma_200[0].get("sma") if sma_200 else None,
            "rsi_14": rsi_14[0].get("rsi") if rsi_14 else None,
            "ema_12": ema12_val,
            "ema_26": ema26_val,
            "macd": macd,
        }
        self.cache.set(key, data, CACHE_TTL["macro"])  # 30 min TTL
        return data

    async def get_historical_prices(self, symbol: str, limit: int = 90) -> list[dict[str, Any]]:
        """Get historical daily OHLCV data."""
        key = f"hist_prices:{symbol}:{limit}"
        cached = self.cache.get(key)
        if cached:
            return cached
        data = await self.fmp.get_historical_price(symbol, limit=limit)
        self.cache.set(key, data, CACHE_TTL["quote"])
        return data

    async def get_insider_transactions(self, symbol: str) -> dict[str, Any]:
        """Get insider transactions from Finnhub."""
        key = f"insider:{symbol}"
        cached = self.cache.get(key)
        if cached:
            return cached
        data = await self.finnhub.get_insider_transactions(symbol)
        self.cache.set(key, data, CACHE_TTL["analyst"])  # 6 hour TTL
        return data
