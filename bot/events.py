"""Discord event handlers."""

import discord
import structlog
from bot.client import BuffetShaoBot

log = structlog.get_logger(__name__)


def setup_events(bot: BuffetShaoBot) -> None:
    """Register event handlers on the bot."""

    @bot.event
    async def on_message(message: discord.Message) -> None:
        # Ignore own messages
        if message.author == bot.user:
            return

        # Ignore messages from other bots
        if message.author.bot:
            return

        # Check if the bot is mentioned or message is a DM
        is_mentioned = bot.user in message.mentions if bot.user else False
        is_dm = isinstance(message.channel, discord.DMChannel)

        if not is_mentioned and not is_dm:
            return

        # Handle as free-form chat via AI engine
        if bot.ai_engine is None:
            await message.reply("I'm still starting up, please try again in a moment.")
            return

        async with message.channel.typing():
            # Strip the mention from the content
            content = message.content
            if bot.user:
                content = content.replace(f"<@{bot.user.id}>", "").strip()
                content = content.replace(f"<@!{bot.user.id}>", "").strip()

            if not content:
                content = "Hello!"

            try:
                response = await bot.ai_engine.chat(
                    user_id=message.author.id,
                    channel_id=message.channel.id,
                    content=content,
                    attachments=message.attachments,
                )

                # Split long responses for Discord's 2000 char limit
                for chunk in _split_message(response):
                    await message.reply(chunk)

            except Exception as e:
                log.error("chat_error", error=str(e), user_id=message.author.id)
                await message.reply("Sorry, I encountered an error processing your message.")


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
