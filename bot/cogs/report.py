"""Report slash command — structured AI analyst report using Opus."""

import discord
from discord.ext import commands
from utils.formatting import validate_ticker
from utils.embed_builder import make_embed, error_embed
from config.constants import EmbedColor
from bot.events import _split_message


REPORT_PROMPT_TEMPLATE = """Conduct a comprehensive analyst report on {symbol}. Fetch ALL of the following data:

1. get_quote — current price and daily move
2. get_company_profile — business overview and sector
3. get_fundamentals — valuation ratios, margins, growth rates
4. get_factor_grades — quantitative factor grades (Value, Growth, Profitability, Momentum, EPS Revisions) and composite Quant Rating
5. get_analyst_data — Wall Street consensus, price targets, upgrades/downgrades
6. get_earnings — recent quarterly earnings surprises
7. get_news — latest 5 news articles
8. get_technical_indicators — SMA, RSI, MACD trend signals

Structure your report EXACTLY as follows:

## {symbol} Analyst Report

### Executive Summary
2-3 sentence thesis with your Quant Rating and Wall Street consensus side-by-side.

### Business Overview
What the company does, competitive position, sector context.

### Financial Health — Factor Grades
Present the 5 factor grades prominently (Value: X, Growth: X, etc.) with brief commentary on each.
Note where the stock is strongest and weakest relative to sector peers.

### Valuation Assessment
PE, P/S, P/B, EV/EBITDA vs sector. Is it cheap/fair/expensive? Use the Value factor grade as context.

### Growth & Momentum
Revenue/earnings growth trajectory. Price momentum. Are fundamentals improving or deteriorating?

### Wall Street vs. Quant
Compare the analyst consensus (buy/hold/sell, price target) with your Quant Rating.
Highlight any divergence — this is where the interesting insights live.

### Bull Case
3 specific data-backed bullish arguments.

### Bear Case
3 specific data-backed bearish arguments.

### Key Risks
Top 3 risks with likelihood and potential impact.

### Verdict
Clear opinion with confidence rating (1-10). State what would change your view.

After completing the report, save a note summarizing your key findings and verdict for future reference.
"""


class ReportCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @discord.slash_command(description="Generate a structured AI analyst report (uses Opus)")
    async def report(
        self,
        ctx: discord.ApplicationContext,
        symbol: discord.Option(str, "Stock ticker symbol"),  # type: ignore[valid-type]
    ) -> None:
        await ctx.defer()
        ticker = validate_ticker(symbol)
        if not ticker:
            await ctx.respond(embed=error_embed(f"Invalid ticker: {symbol}"), ephemeral=True)
            return

        # Check Opus budget
        from ai.router import get_opus_usage
        used, limit = get_opus_usage()
        if used >= limit:
            await ctx.respond(embed=error_embed(
                f"Opus budget exhausted ({used}/{limit} calls today). Try again tomorrow or use `/research quick`."
            ), ephemeral=True)
            return

        await ctx.respond(embed=make_embed(
            f"Analyst Report — {ticker}",
            "Generating comprehensive analyst report with Opus... This may take 60-90 seconds.",
            color=EmbedColor.RESEARCH,
        ))

        from ai.prompts.system import RESEARCH_SYSTEM_PROMPT
        prompt = REPORT_PROMPT_TEMPLATE.format(symbol=ticker)

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


def setup(bot: commands.Bot) -> None:
    bot.add_cog(ReportCog(bot))
