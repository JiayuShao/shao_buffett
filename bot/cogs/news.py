"""News slash commands."""

import discord
from discord.ext import commands
from utils.formatting import validate_ticker
from utils.embed_builder import news_embed, make_embed, error_embed
from config.constants import EmbedColor


class NewsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    news = discord.SlashCommandGroup("news", "Financial news")

    @news.command(description="Get latest financial news")
    async def latest(
        self,
        ctx: discord.ApplicationContext,
        symbol: discord.Option(str, "Filter by ticker (optional)", required=False, default=None),  # type: ignore[valid-type]
        count: discord.Option(int, "Number of articles (1-10)", required=False, default=5, min_value=1, max_value=10),  # type: ignore[valid-type]
    ) -> None:
        await ctx.defer()

        ticker = None
        if symbol:
            ticker = validate_ticker(symbol)
            if not ticker:
                await ctx.respond(embed=error_embed(f"Invalid ticker: {symbol}"), ephemeral=True)
                return

        articles = await self.bot.data_manager.get_news(symbol=ticker, limit=count)

        if not articles:
            await ctx.respond(embed=make_embed(
                "No News Found",
                "No recent news articles found." + (f" for {ticker}" if ticker else ""),
                color=EmbedColor.INFO,
            ))
            return

        embeds = []
        for article in articles[:count]:
            embed = news_embed(
                title=article.get("title", "Untitled"),
                source=article.get("source", "Unknown"),
                summary=article.get("description", article.get("snippet", "No summary available.")),
                url=article.get("url"),
                sentiment=article.get("sentiment"),
                symbols=article.get("symbols"),
            )
            embeds.append(embed)

        await ctx.respond(embeds=embeds[:5])  # Discord allows max 10 embeds per message
        if len(embeds) > 5:
            await ctx.followup.send(embeds=embeds[5:])

    @news.command(description="Search news by keyword")
    async def search(
        self,
        ctx: discord.ApplicationContext,
        query: discord.Option(str, "Search keyword"),  # type: ignore[valid-type]
    ) -> None:
        await ctx.defer()

        # Use MarketAux search or general news with the query
        articles = await self.bot.data_manager.marketaux.get_news(limit=5)

        # Filter by query in title/description
        filtered = [
            a for a in articles
            if query.lower() in (a.get("title", "") + a.get("description", "")).lower()
        ]

        if not filtered:
            filtered = articles[:3]

        if not filtered:
            await ctx.respond(embed=make_embed("No Results", f"No news found for '{query}'.", color=EmbedColor.INFO))
            return

        embeds = [
            news_embed(
                title=a.get("title", ""),
                source=a.get("source", ""),
                summary=a.get("description", ""),
                url=a.get("url"),
                sentiment=a.get("sentiment"),
            )
            for a in filtered[:5]
        ]
        await ctx.respond(embeds=embeds)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(NewsCog(bot))
