"""Watchlist slash commands."""

import discord
from discord.ext import commands
from storage.repositories.watchlist_repo import WatchlistRepository
from utils.formatting import validate_ticker
from utils.embed_builder import make_embed, error_embed, success_embed
from config.constants import EmbedColor


class WatchlistCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @property
    def repo(self) -> WatchlistRepository:
        return WatchlistRepository(self.bot.db_pool)

    watchlist = discord.SlashCommandGroup("watchlist", "Manage your stock watchlist")

    @watchlist.command(description="Add a stock to your watchlist")
    async def add(
        self,
        ctx: discord.ApplicationContext,
        symbol: discord.Option(str, "Stock ticker symbol (e.g. AAPL)"),  # type: ignore[valid-type]
    ) -> None:
        ticker = validate_ticker(symbol)
        if not ticker:
            await ctx.respond(embed=error_embed(f"Invalid ticker: {symbol}"), ephemeral=True)
            return

        success = await self.repo.add(ctx.author.id, ticker)
        if success:
            await ctx.respond(embed=success_embed(f"Added **{ticker}** to your watchlist."))
        else:
            await ctx.respond(embed=error_embed(f"**{ticker}** is already on your watchlist or watchlist is full."), ephemeral=True)

    @watchlist.command(description="Remove a stock from your watchlist")
    async def remove(
        self,
        ctx: discord.ApplicationContext,
        symbol: discord.Option(str, "Stock ticker symbol"),  # type: ignore[valid-type]
    ) -> None:
        ticker = validate_ticker(symbol)
        if not ticker:
            await ctx.respond(embed=error_embed(f"Invalid ticker: {symbol}"), ephemeral=True)
            return

        removed = await self.repo.remove(ctx.author.id, ticker)
        if removed:
            await ctx.respond(embed=success_embed(f"Removed **{ticker}** from your watchlist."))
        else:
            await ctx.respond(embed=error_embed(f"**{ticker}** is not on your watchlist."), ephemeral=True)

    @watchlist.command(description="Show your watchlist with current prices")
    async def show(self, ctx: discord.ApplicationContext) -> None:
        await ctx.defer()
        symbols = await self.repo.get(ctx.author.id)

        if not symbols:
            await ctx.respond(embed=make_embed(
                "Your Watchlist",
                "Your watchlist is empty. Use `/watchlist add <symbol>` to add stocks.",
                color=EmbedColor.INFO,
            ))
            return

        lines = []
        for symbol in symbols:
            try:
                quote = await self.bot.data_manager.get_quote(symbol)
                price = quote.get("price", 0)
                change_pct = quote.get("change_pct", 0)
                arrow = "🟢" if change_pct >= 0 else "🔴"
                sign = "+" if change_pct >= 0 else ""
                lines.append(f"{arrow} **{symbol}** ${price:.2f} ({sign}{change_pct:.2f}%)")
            except Exception:
                lines.append(f"⚪ **{symbol}** — data unavailable")

        embed = make_embed(
            f"Your Watchlist ({len(symbols)} stocks)",
            "\n".join(lines),
            color=EmbedColor.INFO,
        )
        await ctx.respond(embed=embed)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(WatchlistCog(bot))
