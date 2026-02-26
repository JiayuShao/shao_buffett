"""Discord event handlers."""

import time
import discord
import structlog
from bot.client import ShaoBuffettBot

log = structlog.get_logger(__name__)

# Human-readable labels for tool calls
TOOL_LABELS = {
    "get_quote": "Checking price",
    "get_company_profile": "Looking up profile",
    "get_fundamentals": "Pulling financials",
    "get_analyst_data": "Reading analyst views",
    "get_earnings": "Reviewing earnings",
    "get_news": "Scanning news",
    "get_macro_data": "Checking macro data",
    "get_sector_performance": "Reviewing sectors",
    "get_earnings_transcript": "Reading transcript",
    "get_sec_filings": "Checking SEC filings",
    "get_research_papers": "Searching research",
    "get_trending_stocks": "Checking what's trending",
    "get_sentiment": "Analyzing sentiment",
    "get_technical_indicators": "Running technicals",
    "generate_chart": "Generating chart",
    "get_factor_grades": "Computing factor grades",
    "get_portfolio_health": "Analyzing portfolio health",
    "save_note": "Saving note",
    "get_user_notes": "Reading notes",
    "resolve_action_item": "Resolving action item",
    "get_portfolio": "Checking portfolio",
    "update_portfolio": "Updating portfolio",
    "get_financial_profile": "Checking profile",
    "update_financial_profile": "Updating profile",
}


def setup_events(bot: ShaoBuffettBot) -> None:
    """Register event handlers on the bot."""

    @bot.event
    async def on_message(message: discord.Message) -> None:
        # Ignore own messages
        if message.author == bot.user:
            return

        # Ignore messages from other bots
        if message.author.bot:
            return

        # Only respond when @mentioned or in DMs (multi-agent support)
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_mentioned = bot.user is not None and bot.user.mentioned_in(message)
        log.info(
            "on_message_gate",
            author=str(message.author),
            is_dm=is_dm,
            is_mentioned=is_mentioned,
            mentions=[str(u) for u in message.mentions],
            content_preview=message.content[:80],
        )
        if not is_dm and not is_mentioned:
            return

        # Handle as free-form chat via AI engine
        if bot.ai_engine is None:
            await message.reply("I'm still starting up, please try again in a moment.")
            return

        # Strip the mention from the content
        content = message.content
        if bot.user:
            content = content.replace(f"<@{bot.user.id}>", "").strip()
            content = content.replace(f"<@!{bot.user.id}>", "").strip()

        if not content:
            content = "Hello!"

        log.info("chat_request", user=str(message.author), content=content[:80])

        try:
            msg = await message.reply("Thinking...")
        except discord.HTTPException as e:
            log.error("thinking_reply_failed", error=str(e))
            return

        last_edit = 0.0

        async def on_tool_start(name: str, inp: dict) -> None:
            nonlocal last_edit
            now = time.monotonic()
            if now - last_edit < 1.0:
                return  # Rate limit edits
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
                return  # Rate limit edits
            last_edit = now
            try:
                await msg.edit(content=text[:2000])
            except discord.HTTPException:
                pass

        async def send_file(file: discord.File) -> None:
            try:
                await message.channel.send(file=file)
            except discord.HTTPException as e:
                log.error("send_file_error", error=str(e))

        try:
            response = await bot.ai_engine.chat_stream(
                user_id=message.author.id,
                channel_id=message.channel.id,
                content=content,
                attachments=message.attachments,
                on_tool_start=on_tool_start,
                on_text_chunk=on_text_chunk,
                send_file=send_file,
            )

            # Final edit with complete text
            chunks = _split_message(response)
            await msg.edit(content=chunks[0])
            for chunk in chunks[1:]:
                await message.channel.send(chunk)

        except Exception as e:
            log.error("chat_error", error=str(e), user_id=message.author.id)
            try:
                await msg.edit(content="Sorry, I encountered an error processing your message.")
            except discord.HTTPException:
                pass


def _split_message(text: str, limit: int = 2000) -> list[str]:
    """Split a message into chunks respecting Discord's character limit."""
    if len(text) <= limit:
        return [text]

    chunks = []
    while text:
        if len(text) <= limit:
            chunks.append(text)
            break

        # Find a good split point
        split_at = text.rfind("\n", 0, limit)
        if split_at == -1:
            split_at = text.rfind(" ", 0, limit)
        if split_at == -1:
            split_at = limit

        chunks.append(text[:split_at])
        text = text[split_at:].lstrip()

    return chunks
