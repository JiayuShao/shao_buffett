"""Briefing slash commands — on-demand morning/evening briefings."""

import discord
from discord.ext import commands
from utils.embed_builder import make_embed, error_embed
from config.constants import EmbedColor
from bot.events import _split_message


class BriefingCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    briefing = discord.SlashCommandGroup("briefing", "Market briefings")

    @briefing.command(description="Get a morning market briefing")
    async def morning(self, ctx: discord.ApplicationContext) -> None:
        await ctx.defer()

        from scheduler.morning_briefing import generate_morning_briefing

        prompt = (
            "Generate a morning market briefing. Use your tools to fetch:\n"
            "1. Current quotes for the major tech stocks\n"
            "2. Latest market news (top 5 stories)\n"
            "3. Key macro indicators (VIX, 10Y yield, Fed funds rate)\n"
            "4. Sector performance\n\n"
            "Format as a scannable morning briefing."
        )

        from ai.prompts.system import BRIEFING_SYSTEM_PROMPT

        try:
            response = await self.bot.ai_engine.analyze(
                prompt=prompt,
                force_model="sonnet",
                system_prompt=BRIEFING_SYSTEM_PROMPT,
            )

            chunks = _split_message(response)
            await ctx.respond(chunks[0])
            for chunk in chunks[1:]:
                await ctx.followup.send(chunk)
        except Exception as e:
            await ctx.respond(embed=error_embed(f"Error generating briefing: {str(e)[:200]}"))

    @briefing.command(description="Get an evening market summary")
    async def evening(self, ctx: discord.ApplicationContext) -> None:
        await ctx.defer()

        prompt = (
            "Generate an evening market close summary. Use your tools to fetch:\n"
            "1. Closing prices for major tech stocks\n"
            "2. Today's biggest market news\n"
            "3. Any analyst actions today\n"
            "4. Sector performance\n\n"
            "Format as a close-of-day recap."
        )

        from ai.prompts.system import BRIEFING_SYSTEM_PROMPT

        try:
            response = await self.bot.ai_engine.analyze(
                prompt=prompt,
                force_model="sonnet",
                system_prompt=BRIEFING_SYSTEM_PROMPT,
            )

            chunks = _split_message(response)
            await ctx.respond(chunks[0])
            for chunk in chunks[1:]:
                await ctx.followup.send(chunk)
        except Exception as e:
            await ctx.respond(embed=error_embed(f"Error generating summary: {str(e)[:200]}"))

    @briefing.command(description="Get a macro economic briefing")
    async def macro(self, ctx: discord.ApplicationContext) -> None:
        await ctx.defer()

        from ai.prompts.templates import macro_analysis_prompt

        try:
            response = await self.bot.ai_engine.chat(
                user_id=ctx.author.id,
                channel_id=ctx.channel_id,
                content=macro_analysis_prompt(),
            )

            chunks = _split_message(response)
            await ctx.respond(chunks[0])
            for chunk in chunks[1:]:
                await ctx.followup.send(chunk)
        except Exception as e:
            await ctx.respond(embed=error_embed(f"Error: {str(e)[:200]}"))


def setup(bot: commands.Bot) -> None:
    bot.add_cog(BriefingCog(bot))
