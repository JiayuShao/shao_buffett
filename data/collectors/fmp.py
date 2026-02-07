"""Financial Modeling Prep collector — fundamentals, analyst consensus, earnings transcripts."""

from typing import Any
import structlog
from data.collectors.base import BaseCollector
from data.rate_limiter import RateLimiter
from config.settings import settings

log = structlog.get_logger(__name__)

BASE_URL = "https://financialmodelingprep.com/api/v3"


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
                f"{BASE_URL}/quote/AAPL", params=self._params()
            )
            return isinstance(data, list) and len(data) > 0
        except Exception:
            return False

    async def get_quote(self, symbol: str) -> dict[str, Any]:
        """Get detailed quote."""
        data = await self._request(f"{BASE_URL}/quote/{symbol}", params=self._params())
        return data[0] if isinstance(data, list) and data else {}

    async def get_profile(self, symbol: str) -> dict[str, Any]:
        """Get company profile with fundamentals."""
        data = await self._request(f"{BASE_URL}/profile/{symbol}", params=self._params())
        return data[0] if isinstance(data, list) and data else {}

    async def get_income_statement(self, symbol: str, limit: int = 4) -> list[dict[str, Any]]:
        """Get income statements."""
        data = await self._request(
            f"{BASE_URL}/income-statement/{symbol}", params=self._params(limit=limit)
        )
        return data if isinstance(data, list) else []

    async def get_balance_sheet(self, symbol: str, limit: int = 4) -> list[dict[str, Any]]:
        """Get balance sheets."""
        data = await self._request(
            f"{BASE_URL}/balance-sheet-statement/{symbol}", params=self._params(limit=limit)
        )
        return data if isinstance(data, list) else []

    async def get_key_metrics(self, symbol: str, limit: int = 4) -> list[dict[str, Any]]:
        """Get key financial metrics (PE, ROE, margins, etc.)."""
        data = await self._request(
            f"{BASE_URL}/key-metrics/{symbol}", params=self._params(limit=limit)
        )
        return data if isinstance(data, list) else []

    async def get_ratios(self, symbol: str, limit: int = 4) -> list[dict[str, Any]]:
        """Get financial ratios."""
        data = await self._request(
            f"{BASE_URL}/ratios/{symbol}", params=self._params(limit=limit)
        )
        return data if isinstance(data, list) else []

    async def get_analyst_estimates(self, symbol: str) -> list[dict[str, Any]]:
        """Get analyst estimates."""
        data = await self._request(
            f"{BASE_URL}/analyst-estimates/{symbol}", params=self._params()
        )
        return data if isinstance(data, list) else []

    async def get_earnings_transcript(self, symbol: str, year: int, quarter: int) -> dict[str, Any]:
        """Get earnings call transcript."""
        data = await self._request(
            f"{BASE_URL}/earning_call_transcript/{symbol}",
            params=self._params(year=year, quarter=quarter),
        )
        if isinstance(data, list) and data:
            return data[0]
        return data if isinstance(data, dict) else {}

    async def get_earnings_transcript_list(self, symbol: str) -> list[dict[str, Any]]:
        """Get list of available earnings transcripts."""
        data = await self._request(
            f"{BASE_URL}/earning_call_transcript", params=self._params(symbol=symbol)
        )
        return data if isinstance(data, list) else []

    async def get_sector_performance(self) -> list[dict[str, Any]]:
        """Get sector performance data."""
        # Try the v3 sectors-performance endpoint (available on free tier)
        data = await self._request(
            f"{BASE_URL}/sectors-performance", params=self._params()
        )
        if isinstance(data, list) and data:
            return data
        # Fallback to stock_market endpoint
        data = await self._request(
            f"{BASE_URL}/stock_market/sectors-performance", params=self._params()
        )
        return data if isinstance(data, list) else []

    async def get_dcf(self, symbol: str) -> dict[str, Any]:
        """Get DCF valuation."""
        data = await self._request(
            f"{BASE_URL}/discounted-cash-flow/{symbol}", params=self._params()
        )
        if isinstance(data, list) and data:
            return data[0]
        return data if isinstance(data, dict) else {}

    async def get_stock_peers(self, symbol: str) -> list[str]:
        """Get peer companies."""
        data = await self._request(
            f"{BASE_URL}/stock_peers", params=self._params(symbol=symbol)
        )
        if isinstance(data, list) and data:
            return data[0].get("peersList", [])
        return []

    async def get_technical_indicator(
        self, symbol: str, indicator_type: str, period: int = 14, limit: int = 1
    ) -> list[dict[str, Any]]:
        """Get a technical indicator (sma, ema, rsi) for a symbol."""
        data = await self._request(
            f"{BASE_URL}/technical_indicator/daily/{symbol}",
            params=self._params(type=indicator_type, period=period),
        )
        if isinstance(data, list):
            return data[:limit]
        return []

    async def get_historical_price(self, symbol: str, limit: int = 90) -> list[dict[str, Any]]:
        """Get historical daily price data (OHLCV)."""
        data = await self._request(
            f"{BASE_URL}/historical-price-full/{symbol}",
            params=self._params(),
        )
        if isinstance(data, dict):
            historical = data.get("historical", [])
            return historical[:limit]
        return []
