"""Conversational AI chat handler (slash command version)."""

import time
import discord
from discord.ext import commands
from utils.embed_builder import error_embed
from bot.events import _split_message, TOOL_LABELS


class ChatCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @discord.slash_command(name="ask", description="Ask Shao Buffett anything about markets")
    async def ask(
        self,
        ctx: discord.ApplicationContext,
        question: discord.Option(str, "Your question about markets, stocks, or economics"),  # type: ignore[valid-type]
    ) -> None:
        await ctx.defer()

        if self.bot.ai_engine is None:
            await ctx.respond(embed=error_embed("AI engine is not ready yet."), ephemeral=True)
            return

        interaction = await ctx.respond("Thinking...")
        msg = await interaction.original_response()
        last_edit = 0.0

        async def on_tool_start(name: str, inp: dict) -> None:
            nonlocal last_edit
            now = time.monotonic()
            if now - last_edit < 1.0:
                return
            last_edit = now
            symbol = inp.get("symbol", inp.get("query", ""))
            label = TOOL_LABELS.get(name, name)
            status = f"{label} {symbol}...".strip() if symbol else f"{label}..."
            try:
                await msg.edit(content=status)
            except discord.HTTPException:
                pass

        async def on_text_chunk(text: str) -> None:
            nonlocal last_edit
            now = time.monotonic()
            if now - last_edit < 1.5:
                return
            last_edit = now
            try:
                await msg.edit(content=text[:2000])
            except discord.HTTPException:
                pass

        async def send_file(file: discord.File) -> None:
            try:
                await ctx.channel.send(file=file)
            except discord.HTTPException:
                pass

        try:
            response = await self.bot.ai_engine.chat_stream(
                user_id=ctx.author.id,
                channel_id=ctx.channel_id,
                content=question,
                on_tool_start=on_tool_start,
                on_text_chunk=on_text_chunk,
                send_file=send_file,
            )

            chunks = _split_message(response)
            await msg.edit(content=chunks[0])
            for chunk in chunks[1:]:
                await ctx.followup.send(chunk)

        except Exception as e:
            await msg.edit(content="", embed=error_embed(f"Error: {str(e)[:200]}"))

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
