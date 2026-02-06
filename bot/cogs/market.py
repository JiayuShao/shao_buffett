"""Market overview slash commands."""

import discord
from discord.ext import commands
from utils.formatting import format_currency, format_percent, format_change
from utils.embed_builder import make_embed, error_embed
from utils.time_utils import is_market_open, now_et
from config.constants import EmbedColor


class MarketCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    market = discord.SlashCommandGroup("market", "Market data and overview")

    @market.command(description="Get market overview with key indices and indicators")
    async def overview(self, ctx: discord.ApplicationContext) -> None:
        await ctx.defer()

        # Fetch key market data
        indices = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"]
        market_status = "🟢 Open" if is_market_open() else "🔴 Closed"

        embed = make_embed(
            f"Market Overview — {now_et().strftime('%b %d, %I:%M %p ET')}",
            f"Market Status: {market_status}",
            color=EmbedColor.INFO,
        )

        # Key stock prices
        lines = []
        for symbol in indices:
            try:
                quote = await self.bot.data_manager.get_quote(symbol)
                price = quote.get("price", 0)
                change_pct = quote.get("change_pct", 0)
                lines.append(f"{format_change(change_pct)} **{symbol}** ${price:.2f} ({format_percent(change_pct)})")
            except Exception:
                lines.append(f"⚪ **{symbol}** — unavailable")

        embed.add_field(name="Key Stocks", value="\n".join(lines), inline=False)

        # Sector performance
        try:
            sectors = await self.bot.data_manager.get_sector_performance()
            if sectors:
                sector_lines = []
                for s in sectors[:6]:
                    name = s.get("sector", s.get("name", "Unknown"))
                    change = s.get("changesPercentage", 0)
                    if isinstance(change, str):
                        change = float(change.replace("%", ""))
                    sector_lines.append(f"{format_change(change)} {name}")
                embed.add_field(name="Sectors", value="\n".join(sector_lines), inline=False)
        except Exception:
            pass

        await ctx.respond(embed=embed)

    @market.command(description="Get sector performance")
    async def sector(self, ctx: discord.ApplicationContext) -> None:
        await ctx.defer()

        try:
            sectors = await self.bot.data_manager.get_sector_performance()
        except Exception:
            await ctx.respond(embed=error_embed("Failed to fetch sector data."), ephemeral=True)
            return

        if not sectors:
            await ctx.respond(embed=make_embed("Sector Performance", "No data available.", color=EmbedColor.INFO))
            return

        lines = []
        for s in sectors:
            name = s.get("sector", s.get("name", "Unknown"))
            change = s.get("changesPercentage", 0)
            if isinstance(change, str):
                change = float(change.replace("%", ""))
            lines.append(f"{format_change(change)} **{name}** ({format_percent(change)})")

        embed = make_embed(
            "Sector Performance",
            "\n".join(lines),
            color=EmbedColor.INFO,
        )
        await ctx.respond(embed=embed)

    @market.command(description="Get macroeconomic indicators")
    async def macro(self, ctx: discord.ApplicationContext) -> None:
        await ctx.defer()

        try:
            snapshot = await self.bot.data_manager.get_macro_data()
        except Exception:
            await ctx.respond(embed=error_embed("Failed to fetch macro data."), ephemeral=True)
            return

        embed = make_embed(
            "Macro Economic Indicators",
            "Latest readings from FRED",
            color=EmbedColor.MACRO,
        )

        for name, data in snapshot.items():
            val = data.get("value", "N/A")
            date = data.get("date", "")
            embed.add_field(name=name, value=f"{val}\n_{date}_", inline=True)

        await ctx.respond(embed=embed)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(MarketCog(bot))
