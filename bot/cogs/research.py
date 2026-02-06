"""Research slash commands — deep analysis, transcripts, filings, compare."""

import discord
from discord.ext import commands
from utils.formatting import validate_ticker
from utils.embed_builder import make_embed, error_embed
from config.constants import EmbedColor
from ai.prompts.templates import (
    stock_analysis_prompt,
    comparison_prompt,
    earnings_analysis_prompt,
    deep_research_prompt,
)
from bot.events import _split_message


class ResearchCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    research = discord.SlashCommandGroup("research", "Research and analysis")

    @research.command(description="Quick analysis of a stock")
    async def quick(
        self,
        ctx: discord.ApplicationContext,
        symbol: discord.Option(str, "Stock ticker symbol"),  # type: ignore[valid-type]
    ) -> None:
        await ctx.defer()
        ticker = validate_ticker(symbol)
        if not ticker:
            await ctx.respond(embed=error_embed(f"Invalid ticker: {symbol}"), ephemeral=True)
            return

        prompt = stock_analysis_prompt(ticker)
        response = await self.bot.ai_engine.chat(
            user_id=ctx.author.id,
            channel_id=ctx.channel_id,
            content=prompt,
        )

        chunks = _split_message(response)
        await ctx.respond(chunks[0])
        for chunk in chunks[1:]:
            await ctx.followup.send(chunk)

    @research.command(description="Deep research analysis (uses Opus)")
    async def deep(
        self,
        ctx: discord.ApplicationContext,
        symbol: discord.Option(str, "Stock ticker symbol"),  # type: ignore[valid-type]
    ) -> None:
        await ctx.defer()
        ticker = validate_ticker(symbol)
        if not ticker:
            await ctx.respond(embed=error_embed(f"Invalid ticker: {symbol}"), ephemeral=True)
            return

        from ai.router import get_opus_usage
        used, limit = get_opus_usage()
        if used >= limit:
            await ctx.respond(embed=error_embed(
                f"Opus budget exhausted ({used}/{limit} calls today). Try again tomorrow or use `/research quick`."
            ), ephemeral=True)
            return

        await ctx.respond(embed=make_embed(
            f"Deep Research — {ticker}",
            "Running institutional-quality analysis with Opus... This may take 30-60 seconds.",
            color=EmbedColor.RESEARCH,
        ))

        from ai.prompts.system import RESEARCH_SYSTEM_PROMPT
        prompt = deep_research_prompt(ticker)
        response = await self.bot.ai_engine.chat(
            user_id=ctx.author.id,
            channel_id=ctx.channel_id,
            content=prompt,
            force_model="opus",
            system_prompt=RESEARCH_SYSTEM_PROMPT,
        )

        chunks = _split_message(response)
        for chunk in chunks:
            await ctx.followup.send(chunk)

    @research.command(description="Compare two or more stocks")
    async def compare(
        self,
        ctx: discord.ApplicationContext,
        symbols: discord.Option(str, "Comma-separated tickers (e.g. AAPL,MSFT,GOOGL)"),  # type: ignore[valid-type]
    ) -> None:
        await ctx.defer()
        tickers = [validate_ticker(s.strip()) for s in symbols.split(",")]
        tickers = [t for t in tickers if t is not None]

        if len(tickers) < 2:
            await ctx.respond(embed=error_embed("Provide at least 2 valid tickers."), ephemeral=True)
            return

        prompt = comparison_prompt(tickers)
        response = await self.bot.ai_engine.chat(
            user_id=ctx.author.id,
            channel_id=ctx.channel_id,
            content=prompt,
        )

        chunks = _split_message(response)
        await ctx.respond(chunks[0])
        for chunk in chunks[1:]:
            await ctx.followup.send(chunk)

    @research.command(description="Get earnings transcript analysis")
    async def transcript(
        self,
        ctx: discord.ApplicationContext,
        symbol: discord.Option(str, "Stock ticker symbol"),  # type: ignore[valid-type]
        year: discord.Option(int, "Year (e.g. 2024)", required=False, default=2024),  # type: ignore[valid-type]
        quarter: discord.Option(int, "Quarter (1-4)", required=False, default=4, min_value=1, max_value=4),  # type: ignore[valid-type]
    ) -> None:
        await ctx.defer()
        ticker = validate_ticker(symbol)
        if not ticker:
            await ctx.respond(embed=error_embed(f"Invalid ticker: {symbol}"), ephemeral=True)
            return

        prompt = earnings_analysis_prompt(ticker, year, quarter)
        response = await self.bot.ai_engine.chat(
            user_id=ctx.author.id,
            channel_id=ctx.channel_id,
            content=prompt,
        )

        chunks = _split_message(response)
        await ctx.respond(chunks[0])
        for chunk in chunks[1:]:
            await ctx.followup.send(chunk)

    @research.command(description="Get recent SEC filings for a company")
    async def filing(
        self,
        ctx: discord.ApplicationContext,
        symbol: discord.Option(str, "Stock ticker symbol"),  # type: ignore[valid-type]
        form_type: discord.Option(str, "Filing type", choices=["10-K", "10-Q", "8-K", "All"], required=False, default="All"),  # type: ignore[valid-type]
    ) -> None:
        await ctx.defer()
        ticker = validate_ticker(symbol)
        if not ticker:
            await ctx.respond(embed=error_embed(f"Invalid ticker: {symbol}"), ephemeral=True)
            return

        types = None if form_type == "All" else [form_type]
        filings = await self.bot.data_manager.get_sec_filings(ticker, form_types=types)

        if not filings:
            await ctx.respond(embed=make_embed(
                f"SEC Filings — {ticker}", "No recent filings found.", color=EmbedColor.INFO
            ))
            return

        lines = []
        for f in filings[:10]:
            ftype = f.get("form_type", "")
            date = f.get("file_date", "")
            name = f.get("entity_name", "")
            lines.append(f"**{ftype}** — {date} — {name}")

        embed = make_embed(
            f"SEC Filings — {ticker}",
            "\n".join(lines),
            color=EmbedColor.RESEARCH,
        )
        await ctx.respond(embed=embed)

    @research.command(description="Search quantitative finance research papers")
    async def papers(
        self,
        ctx: discord.ApplicationContext,
        query: discord.Option(str, "Search query (e.g. 'portfolio optimization')", required=False, default=None),  # type: ignore[valid-type]
    ) -> None:
        await ctx.defer()

        papers = await self.bot.data_manager.get_research_papers(query=query, max_results=5)

        if not papers:
            await ctx.respond(embed=make_embed("Research Papers", "No papers found.", color=EmbedColor.INFO))
            return

        lines = []
        for p in papers:
            title = p.get("title", "Untitled")
            authors = ", ".join(p.get("authors", [])[:2])
            if len(p.get("authors", [])) > 2:
                authors += " et al."
            pdf = p.get("pdf_url", "")
            link = f" [PDF]({pdf})" if pdf else ""
            lines.append(f"**{title}**\n_{authors}_{link}\n")

        embed = make_embed(
            "Quantitative Finance Research",
            "\n".join(lines),
            color=EmbedColor.RESEARCH,
        )
        await ctx.respond(embed=embed)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(ResearchCog(bot))
