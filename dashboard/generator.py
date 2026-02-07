"""Dashboard composition — builds multi-chart dashboards."""

import discord
import structlog
from typing import Any
from data.manager import DataManager
from dashboard.charts import comparison_chart, sector_heatmap, earnings_chart, macro_trend_chart, price_chart
from dashboard.renderer import render_to_discord_file

log = structlog.get_logger(__name__)


class DashboardGenerator:
    """Generate dashboard chart images for Discord."""

    def __init__(self, data_manager: DataManager) -> None:
        self.dm = data_manager

    async def generate_watchlist_dashboard(
        self, symbols: list[str]
    ) -> list[discord.File]:
        """Generate a dashboard for a user's watchlist."""
        files = []

        # Comparison chart
        quotes = []
        for symbol in symbols[:10]:
            try:
                q = await self.dm.get_quote(symbol)
                quotes.append(q)
            except Exception:
                pass

        if quotes:
            fig = comparison_chart(symbols, quotes, "Watchlist Performance")
            files.append(render_to_discord_file(fig, "watchlist_comparison.png"))

        return files

    async def generate_sector_dashboard(self) -> list[discord.File]:
        """Generate a sector performance heatmap."""
        files = []

        try:
            sectors = await self.dm.get_sector_performance()
            if sectors:
                fig = sector_heatmap(sectors)
                files.append(render_to_discord_file(fig, "sector_heatmap.png"))
        except Exception as e:
            log.error("sector_dashboard_error", error=str(e))

        return files

    async def generate_earnings_dashboard(
        self, symbol: str
    ) -> list[discord.File]:
        """Generate earnings history chart for a symbol."""
        files = []

        try:
            earnings = await self.dm.get_earnings(symbol)
            if earnings:
                fig = earnings_chart(symbol, earnings)
                files.append(render_to_discord_file(fig, f"{symbol}_earnings.png"))
        except Exception as e:
            log.error("earnings_dashboard_error", symbol=symbol, error=str(e))

        return files

    async def generate_macro_dashboard(
        self, series_id: str, series_name: str
    ) -> list[discord.File]:
        """Generate a macro trend chart."""
        files = []

        try:
            data = await self.dm.fred.get_series(series_id, limit=30)
            if data:
                fig = macro_trend_chart(series_name, data)
                files.append(render_to_discord_file(fig, f"{series_id}_trend.png"))
        except Exception as e:
            log.error("macro_dashboard_error", series_id=series_id, error=str(e))

        return files

    async def generate_price_chart(self, symbol: str, title: str | None = None) -> list[discord.File]:
        """Generate a candlestick price chart for a symbol."""
        files = []
        try:
            prices = await self.dm.get_historical_prices(symbol, limit=90)
            if prices:
                fig = price_chart(symbol, prices, title)
                files.append(render_to_discord_file(fig, f"{symbol}_price.png"))
        except Exception as e:
            log.error("price_chart_error", symbol=symbol, error=str(e))
        return files

    async def generate_chart(
        self, chart_type: str, **kwargs: Any
    ) -> list[discord.File]:
        """Generate a chart by type (used by AI tool calls)."""
        match chart_type:
            case "comparison":
                symbols = kwargs.get("symbols", [])
                return await self.generate_watchlist_dashboard(symbols)
            case "sector_heatmap":
                return await self.generate_sector_dashboard()
            case "earnings_history":
                symbol = kwargs.get("symbols", ["AAPL"])[0]
                return await self.generate_earnings_dashboard(symbol)
            case "macro_trend":
                series_id = kwargs.get("series_id", "GDP")
                return await self.generate_macro_dashboard(series_id, kwargs.get("title", series_id))
            case "price_chart":
                symbols = kwargs.get("symbols", ["AAPL"])
                symbol = symbols[0] if symbols else "AAPL"
                return await self.generate_price_chart(symbol, kwargs.get("title"))
            case _:
                return []
