"""SEC EDGAR filings collector."""

from typing import Any
import structlog
from data.collectors.base import BaseCollector
from data.rate_limiter import RateLimiter

log = structlog.get_logger(__name__)

BASE_URL = "https://efts.sec.gov/LATEST"
SUBMISSIONS_URL = "https://data.sec.gov/submissions"

# Map of common tickers to CIK numbers (can be expanded or fetched dynamically)
TICKER_CIK_MAP: dict[str, str] = {}


class SECEdgarCollector(BaseCollector):
    api_name = "sec_edgar"

    def __init__(self, rate_limiter: RateLimiter) -> None:
        super().__init__(rate_limiter)

    async def health_check(self) -> bool:
        try:
            data = await self._request(
                f"{BASE_URL}/search-index",
                params={"q": "AAPL", "dateRange": "custom", "startdt": "2024-01-01", "enddt": "2024-01-31"},
            )
            return "hits" in data
        except Exception:
            return False

    async def _get_cik(self, symbol: str) -> str | None:
        """Look up CIK number for a ticker symbol."""
        if symbol in TICKER_CIK_MAP:
            return TICKER_CIK_MAP[symbol]
        try:
            data = await self._request(
                "https://efts.sec.gov/LATEST/search-index",
                params={"q": f"\"{symbol}\"", "dateRange": "custom", "startdt": "2024-01-01", "enddt": "2024-12-31", "forms": "10-K"},
            )
            hits = data.get("hits", {}).get("hits", [])
            if hits:
                cik = hits[0].get("_source", {}).get("entity_id", "")
                if cik:
                    TICKER_CIK_MAP[symbol] = cik
                    return cik
        except Exception:
            pass
        return None

    async def search_filings(
        self,
        query: str,
        forms: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Full-text search across SEC filings."""
        params: dict[str, Any] = {"q": query, "from": 0, "size": limit}
        if forms:
            params["forms"] = forms
        if date_from and date_to:
            params["dateRange"] = "custom"
            params["startdt"] = date_from
            params["enddt"] = date_to

        data = await self._request(f"{BASE_URL}/search-index", params=params)
        hits = data.get("hits", {}).get("hits", [])

        return [
            {
                "form_type": h.get("_source", {}).get("form_type", ""),
                "entity_name": h.get("_source", {}).get("entity_name", ""),
                "file_date": h.get("_source", {}).get("file_date", ""),
                "period_of_report": h.get("_source", {}).get("period_of_report", ""),
                "file_url": f"https://www.sec.gov/Archives/edgar/data/{h.get('_source', {}).get('entity_id', '')}/{h.get('_id', '')}",
                "description": h.get("_source", {}).get("display_names", [""])[0] if h.get("_source", {}).get("display_names") else "",
            }
            for h in hits
        ]

    async def get_company_filings(
        self,
        symbol: str,
        form_types: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get recent filings for a company."""
        forms = ",".join(form_types) if form_types else "10-K,10-Q,8-K"
        return await self.search_filings(
            query=f"\"{symbol}\"",
            forms=forms,
            limit=limit,
        )

    async def get_latest_10k(self, symbol: str) -> dict[str, Any] | None:
        """Get the most recent 10-K filing."""
        results = await self.get_company_filings(symbol, form_types=["10-K"], limit=1)
        return results[0] if results else None

    async def get_latest_10q(self, symbol: str) -> dict[str, Any] | None:
        """Get the most recent 10-Q filing."""
        results = await self.get_company_filings(symbol, form_types=["10-Q"], limit=1)
        return results[0] if results else None

    async def get_latest_8k(self, symbol: str, limit: int = 5) -> list[dict[str, Any]]:
        """Get recent 8-K filings."""
        return await self.get_company_filings(symbol, form_types=["8-K"], limit=limit)
