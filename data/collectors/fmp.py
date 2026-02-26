"""Financial Modeling Prep collector — fundamentals, analyst consensus, earnings transcripts.

Uses the /stable/ API (v3 endpoints were deprecated August 2025).
"""

from typing import Any
import structlog
from data.collectors.base import BaseCollector
from data.rate_limiter import RateLimiter
from config.settings import settings

log = structlog.get_logger(__name__)

BASE_URL = "https://financialmodelingprep.com/stable"


class FMPCollector(BaseCollector):
    api_name = "fmp"

    def __init__(self, rate_limiter: RateLimiter) -> None:
        super().__init__(rate_limiter)
        self._api_key = settings.fmp_api_key

    def _params(self, **kwargs: Any) -> dict[str, Any]:
        return {"apikey": self._api_key, **kwargs}

    async def health_check(self) -> bool:
        try:
            data = await self._request(
                f"{BASE_URL}/quote", params=self._params(symbol="AAPL")
            )
            return isinstance(data, list) and len(data) > 0
        except Exception:
            return False

    async def get_quote(self, symbol: str) -> dict[str, Any]:
        """Get detailed quote."""
        data = await self._request(
            f"{BASE_URL}/quote", params=self._params(symbol=symbol)
        )
        return data[0] if isinstance(data, list) and data else {}

    async def get_profile(self, symbol: str) -> dict[str, Any]:
        """Get company profile with fundamentals."""
        data = await self._request(
            f"{BASE_URL}/profile", params=self._params(symbol=symbol)
        )
        return data[0] if isinstance(data, list) and data else {}

    async def get_income_statement(self, symbol: str, limit: int = 4) -> list[dict[str, Any]]:
        """Get income statements."""
        data = await self._request(
            f"{BASE_URL}/income-statement",
            params=self._params(symbol=symbol, limit=limit, period="annual"),
        )
        return data if isinstance(data, list) else []

    async def get_balance_sheet(self, symbol: str, limit: int = 4) -> list[dict[str, Any]]:
        """Get balance sheets."""
        data = await self._request(
            f"{BASE_URL}/balance-sheet-statement",
            params=self._params(symbol=symbol, limit=limit, period="annual"),
        )
        return data if isinstance(data, list) else []

    async def get_key_metrics(self, symbol: str, limit: int = 4) -> list[dict[str, Any]]:
        """Get key financial metrics (PE, ROE, margins, etc.)."""
        data = await self._request(
            f"{BASE_URL}/key-metrics",
            params=self._params(symbol=symbol, limit=limit, period="annual"),
        )
        return data if isinstance(data, list) else []

    async def get_ratios(self, symbol: str, limit: int = 4) -> list[dict[str, Any]]:
        """Get financial ratios."""
        data = await self._request(
            f"{BASE_URL}/ratios",
            params=self._params(symbol=symbol, limit=limit, period="annual"),
        )
        return data if isinstance(data, list) else []

    async def get_analyst_estimates(self, symbol: str) -> list[dict[str, Any]]:
        """Get analyst estimates."""
        data = await self._request(
            f"{BASE_URL}/analyst-estimates",
            params=self._params(symbol=symbol, period="annual"),
        )
        return data if isinstance(data, list) else []

    async def get_earnings_transcript(self, symbol: str, year: int, quarter: int) -> dict[str, Any]:
        """Get earnings call transcript."""
        data = await self._request(
            f"{BASE_URL}/earning-call-transcript",
            params=self._params(symbol=symbol, year=year, quarter=quarter),
        )
        if isinstance(data, list) and data:
            return data[0]
        return data if isinstance(data, dict) else {}

    async def get_earnings_transcript_list(self, symbol: str) -> list[dict[str, Any]]:
        """Get list of available earnings transcripts."""
        data = await self._request(
            f"{BASE_URL}/earning-call-transcript",
            params=self._params(symbol=symbol),
        )
        return data if isinstance(data, list) else []

    async def get_sector_performance(self) -> list[dict[str, Any]]:
        """Get sector performance data via historical endpoint."""
        # Stable API has /historical-sector-performance per sector.
        # Fetch a broad set of sectors and return aggregated results.
        sectors = [
            "Technology", "Healthcare", "Financial Services", "Energy",
            "Consumer Cyclical", "Industrials", "Communication Services",
            "Consumer Defensive", "Utilities", "Real Estate", "Basic Materials",
        ]
        results = []
        for sector in sectors:
            try:
                data = await self._request(
                    f"{BASE_URL}/historical-sector-performance",
                    params=self._params(sector=sector),
                )
                if isinstance(data, list) and data:
                    latest = data[0]
                    results.append({
                        "sector": sector,
                        "changesPercentage": latest.get("changesPercentage", 0),
                    })
            except Exception:
                continue
        return results

    async def get_dcf(self, symbol: str) -> dict[str, Any]:
        """Get DCF valuation."""
        data = await self._request(
            f"{BASE_URL}/discounted-cash-flow",
            params=self._params(symbol=symbol),
        )
        if isinstance(data, list) and data:
            return data[0]
        return data if isinstance(data, dict) else {}

    async def get_stock_peers(self, symbol: str) -> list[str]:
        """Get peer companies."""
        data = await self._request(
            f"{BASE_URL}/stock-peers", params=self._params(symbol=symbol)
        )
        if isinstance(data, list):
            return [p["symbol"] for p in data if "symbol" in p]
        return []

    async def get_technical_indicator(
        self, symbol: str, indicator_type: str, period: int = 14, limit: int = 1
    ) -> list[dict[str, Any]]:
        """Get a technical indicator (sma, ema, rsi) for a symbol."""
        data = await self._request(
            f"{BASE_URL}/technical-indicators/{indicator_type}",
            params=self._params(symbol=symbol, periodLength=period, timeframe="1day"),
        )
        if isinstance(data, list):
            return data[:limit]
        return []

    async def get_historical_price(self, symbol: str, limit: int = 90) -> list[dict[str, Any]]:
        """Get historical daily price data (OHLCV)."""
        data = await self._request(
            f"{BASE_URL}/historical-price-eod/full",
            params=self._params(symbol=symbol),
        )
        if isinstance(data, list):
            return data[:limit]
        return []
