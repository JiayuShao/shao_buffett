"""Conversational AI chat handler (slash command version)."""

import discord
from discord.ext import commands
from utils.embed_builder import error_embed
from bot.events import _split_message


class ChatCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @discord.slash_command(name="ask", description="Ask Buffet Shao anything about markets")
    async def ask(
        self,
        ctx: discord.ApplicationContext,
        question: discord.Option(str, "Your question about markets, stocks, or economics"),  # type: ignore[valid-type]
    ) -> None:
        await ctx.defer()

        if self.bot.ai_engine is None:
            await ctx.respond(embed=error_embed("AI engine is not ready yet."), ephemeral=True)
            return

        try:
            response = await self.bot.ai_engine.chat(
                user_id=ctx.author.id,
                channel_id=ctx.channel_id,
                content=question,
            )

            chunks = _split_message(response)
            await ctx.respond(chunks[0])
            for chunk in chunks[1:]:
                await ctx.followup.send(chunk)

        except Exception as e:
            await ctx.respond(embed=error_embed(f"Error: {str(e)[:200]}"), ephemeral=True)

    @discord.slash_command(name="clear_chat", description="Clear your conversation history in this channel")
    async def clear_chat(self, ctx: discord.ApplicationContext) -> None:
        if self.bot.ai_engine is None:
            await ctx.respond(embed=error_embed("AI engine is not ready yet."), ephemeral=True)
            return

        count = await self.bot.ai_engine.conversation.clear_history(
            ctx.author.id, ctx.channel_id
        )
        await ctx.respond(f"Cleared {count} messages from conversation history.", ephemeral=True)


def setup(bot: commands.Bot) -> None:
    bot.add_cog(ChatCog(bot))
