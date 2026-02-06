"""Dashboard slash commands."""

import discord
from discord.ext import commands
from dashboard.generator import DashboardGenerator
from storage.repositories.watchlist_repo import WatchlistRepository
from utils.embed_builder import make_embed, error_embed
from config.constants import EmbedColor


class DashboardCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    dashboard = discord.SlashCommandGroup("dashboard", "Generate and manage dashboards")

    @dashboard.command(description="Generate your watchlist dashboard")
    async def watchlist(self, ctx: discord.ApplicationContext) -> None:
        await ctx.defer()

        repo = WatchlistRepository(self.bot.db_pool)
        symbols = await repo.get(ctx.author.id)

        if not symbols:
            await ctx.respond(embed=error_embed(
                "Your watchlist is empty. Add stocks with `/watchlist add`."
            ))
            return

        generator = DashboardGenerator(self.bot.data_manager)
        files = await generator.generate_watchlist_dashboard(symbols)

        if files:
            await ctx.respond(
                embed=make_embed("Watchlist Dashboard", f"Showing {len(symbols)} stocks", color=EmbedColor.INFO),
                files=files,
            )
        else:
            await ctx.respond(embed=error_embed("Failed to generate dashboard."))

    @dashboard.command(description="Generate sector performance heatmap")
    async def sectors(self, ctx: discord.ApplicationContext) -> None:
        await ctx.defer()

        generator = DashboardGenerator(self.bot.data_manager)
        files = await generator.generate_sector_dashboard()

        if files:
            await ctx.respond(
                embed=make_embed("Sector Performance", "", color=EmbedColor.INFO),
                files=files,
            )
        else:
            await ctx.respond(embed=error_embed("Failed to generate sector heatmap."))

    @dashboard.command(description="Generate earnings chart for a stock")
    async def earnings(
        self,
        ctx: discord.ApplicationContext,
        symbol: discord.Option(str, "Stock ticker symbol"),  # type: ignore[valid-type]
    ) -> None:
        await ctx.defer()

        generator = DashboardGenerator(self.bot.data_manager)
        files = await generator.generate_earnings_dashboard(symbol.upper())

        if files:
            await ctx.respond(
                embed=make_embed(f"{symbol.upper()} Earnings History", "", color=EmbedColor.EARNINGS),
                files=files,
            )
        else:
            await ctx.respond(embed=error_embed(f"No earnings data for {symbol.upper()}."))

    @dashboard.command(description="Generate macro trend chart")
    async def macro(
        self,
        ctx: discord.ApplicationContext,
        indicator: discord.Option(
            str,
            "Macro indicator",
            choices=["GDP", "CPI", "Unemployment", "Fed Funds", "10Y Treasury", "VIX"],
        ),  # type: ignore[valid-type]
    ) -> None:
        await ctx.defer()

        series_map = {
            "GDP": ("GDP", "GDP"),
            "CPI": ("CPIAUCSL", "CPI"),
            "Unemployment": ("UNRATE", "Unemployment Rate"),
            "Fed Funds": ("FEDFUNDS", "Fed Funds Rate"),
            "10Y Treasury": ("DGS10", "10Y Treasury Yield"),
            "VIX": ("VIXCLS", "VIX"),
        }

        series_id, name = series_map.get(indicator, ("GDP", "GDP"))
        generator = DashboardGenerator(self.bot.data_manager)
        files = await generator.generate_macro_dashboard(series_id, name)

        if files:
            await ctx.respond(
                embed=make_embed(f"{name} Trend", "", color=EmbedColor.MACRO),
                files=files,
            )
        else:
            await ctx.respond(embed=error_embed(f"Failed to generate {name} chart."))


def setup(bot: commands.Bot) -> None:
    bot.add_cog(DashboardCog(bot))
