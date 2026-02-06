"""FRED (Federal Reserve Economic Data) collector."""

from typing import Any
import structlog
from data.collectors.base import BaseCollector
from data.rate_limiter import RateLimiter
from config.settings import settings

log = structlog.get_logger(__name__)

BASE_URL = "https://api.stlouisfed.org/fred"

# Common FRED series IDs
MACRO_SERIES = {
    "GDP": "GDP",
    "Real GDP": "GDPC1",
    "CPI": "CPIAUCSL",
    "Core CPI": "CPILFESL",
    "Unemployment Rate": "UNRATE",
    "Fed Funds Rate": "FEDFUNDS",
    "10Y Treasury": "DGS10",
    "2Y Treasury": "DGS2",
    "30Y Mortgage": "MORTGAGE30US",
    "VIX": "VIXCLS",
    "S&P 500": "SP500",
    "Industrial Production": "INDPRO",
    "Retail Sales": "RSXFS",
    "PCE": "PCE",
    "Core PCE": "PCEPILFE",
    "Nonfarm Payrolls": "PAYEMS",
    "Initial Claims": "ICSA",
    "Consumer Sentiment": "UMCSENT",
    "Housing Starts": "HOUST",
    "M2 Money Supply": "M2SL",
}


class FredCollector(BaseCollector):
    api_name = "fred"

    def __init__(self, rate_limiter: RateLimiter) -> None:
        super().__init__(rate_limiter)
        self._api_key = settings.fred_api_key

    def _params(self, **kwargs: Any) -> dict[str, Any]:
        return {"api_key": self._api_key, "file_type": "json", **kwargs}

    async def health_check(self) -> bool:
        try:
            data = await self._request(
                f"{BASE_URL}/series", params=self._params(series_id="GDP")
            )
            return "seriess" in data
        except Exception:
            return False

    async def get_series(
        self,
        series_id: str,
        limit: int = 10,
        sort_order: str = "desc",
    ) -> list[dict[str, Any]]:
        """Get observations for a FRED series."""
        data = await self._request(
            f"{BASE_URL}/series/observations",
            params=self._params(
                series_id=series_id,
                limit=limit,
                sort_order=sort_order,
            ),
        )
        return data.get("observations", [])

    async def get_series_info(self, series_id: str) -> dict[str, Any]:
        """Get metadata about a FRED series."""
        data = await self._request(
            f"{BASE_URL}/series", params=self._params(series_id=series_id)
        )
        seriess = data.get("seriess", [])
        return seriess[0] if seriess else {}

    async def search_series(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search FRED series by keyword."""
        data = await self._request(
            f"{BASE_URL}/series/search",
            params=self._params(search_text=query, limit=limit),
        )
        return data.get("seriess", [])

    async def get_macro_snapshot(self) -> dict[str, Any]:
        """Get latest values for key macro indicators."""
        snapshot = {}
        for name, series_id in MACRO_SERIES.items():
            try:
                obs = await self.get_series(series_id, limit=1)
                if obs:
                    snapshot[name] = {
                        "value": obs[0].get("value"),
                        "date": obs[0].get("date"),
                        "series_id": series_id,
                    }
            except Exception as e:
                log.warning("fred_series_error", series_id=series_id, error=str(e))
        return snapshot
