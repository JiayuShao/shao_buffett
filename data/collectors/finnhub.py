"""Finnhub data collector — quotes, analyst ratings, earnings, news, insider trades."""

import asyncio
import json
from typing import Any
import structlog
import websockets
from data.collectors.base import BaseCollector
from data.rate_limiter import RateLimiter
from config.settings import settings

log = structlog.get_logger(__name__)

BASE_URL = "https://finnhub.io/api/v1"


class FinnhubCollector(BaseCollector):
    api_name = "finnhub"

    def __init__(self, rate_limiter: RateLimiter) -> None:
        super().__init__(rate_limiter)
        self._api_key = settings.finnhub_api_key
        self._ws: Any = None
        self._ws_callbacks: dict[str, Any] = {}

    def _params(self, **kwargs: Any) -> dict[str, Any]:
        return {"token": self._api_key, **kwargs}

    async def health_check(self) -> bool:
        try:
            data = await self._request(f"{BASE_URL}/stock/symbol", params=self._params(exchange="US"))
            return isinstance(data, list) and len(data) > 0
        except Exception:
            return False

    async def get_quote(self, symbol: str) -> dict[str, Any]:
        """Get real-time quote for a symbol."""
        data = await self._request(f"{BASE_URL}/quote", params=self._params(symbol=symbol))
        return {
            "symbol": symbol,
            "price": data.get("c", 0),
            "change": data.get("d", 0),
            "change_pct": data.get("dp", 0),
            "high": data.get("h", 0),
            "low": data.get("l", 0),
            "open": data.get("o", 0),
            "prev_close": data.get("pc", 0),
            "timestamp": data.get("t", 0),
        }

    async def get_company_profile(self, symbol: str) -> dict[str, Any]:
        """Get company profile/info."""
        return await self._request(f"{BASE_URL}/stock/profile2", params=self._params(symbol=symbol))

    async def get_analyst_recommendations(self, symbol: str) -> list[dict[str, Any]]:
        """Get analyst recommendation trends."""
        data = await self._request(
            f"{BASE_URL}/stock/recommendation", params=self._params(symbol=symbol)
        )
        return data if isinstance(data, list) else []

    async def get_price_target(self, symbol: str) -> dict[str, Any]:
        """Get analyst price target consensus."""
        return await self._request(f"{BASE_URL}/stock/price-target", params=self._params(symbol=symbol))

    async def get_earnings(self, symbol: str) -> list[dict[str, Any]]:
        """Get historical earnings surprises."""
        data = await self._request(
            f"{BASE_URL}/stock/earnings", params=self._params(symbol=symbol)
        )
        return data if isinstance(data, list) else []

    async def get_company_news(self, symbol: str, from_date: str, to_date: str) -> list[dict[str, Any]]:
        """Get company news articles."""
        data = await self._request(
            f"{BASE_URL}/company-news",
            params=self._params(symbol=symbol, **{"from": from_date, "to": to_date}),
        )
        return data if isinstance(data, list) else []

    async def get_general_news(self, category: str = "general") -> list[dict[str, Any]]:
        """Get general market news."""
        data = await self._request(
            f"{BASE_URL}/news", params=self._params(category=category)
        )
        return data if isinstance(data, list) else []

    async def get_insider_transactions(self, symbol: str) -> dict[str, Any]:
        """Get insider transactions."""
        return await self._request(
            f"{BASE_URL}/stock/insider-transactions", params=self._params(symbol=symbol)
        )

    async def get_earnings_calendar(self, from_date: str, to_date: str) -> dict[str, Any]:
        """Get earnings calendar."""
        return await self._request(
            f"{BASE_URL}/calendar/earnings",
            params=self._params(**{"from": from_date, "to": to_date}),
        )

    async def get_upgrade_downgrade(self, symbol: str) -> list[dict[str, Any]]:
        """Get recent analyst upgrades/downgrades."""
        data = await self._request(
            f"{BASE_URL}/stock/upgrade-downgrade", params=self._params(symbol=symbol)
        )
        return data if isinstance(data, list) else []

    # WebSocket for real-time prices
    async def start_websocket(self, symbols: list[str], callback: Any) -> None:
        """Start WebSocket connection for real-time price updates."""
        if not self._api_key:
            log.warning("finnhub_ws_no_key")
            return

        uri = f"wss://ws.finnhub.io?token={self._api_key}"
        try:
            self._ws = await websockets.connect(uri)
            for symbol in symbols:
                await self._ws.send(json.dumps({"type": "subscribe", "symbol": symbol}))
                self._ws_callbacks[symbol] = callback

            log.info("finnhub_ws_connected", symbols=len(symbols))

            async for message in self._ws:
                data = json.loads(message)
                if data.get("type") == "trade":
                    for trade in data.get("data", []):
                        sym = trade.get("s")
                        if sym in self._ws_callbacks:
                            await self._ws_callbacks[sym](trade)
        except Exception as e:
            log.error("finnhub_ws_error", error=str(e))

    async def stop_websocket(self) -> None:
        if self._ws:
            for symbol in self._ws_callbacks:
                try:
                    await self._ws.send(json.dumps({"type": "unsubscribe", "symbol": symbol}))
                except Exception:
                    pass
            await self._ws.close()
            self._ws = None
            self._ws_callbacks.clear()
