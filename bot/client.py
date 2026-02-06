"""Discord bot client with service references."""

import discord
import structlog
from config.settings import settings

log = structlog.get_logger(__name__)


class BuffetShaoBot(discord.Bot):
    """Main Discord bot class with references to all services."""

    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(
            intents=intents,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="the markets 📈",
            ),
        )

        # Service references (set during startup in main.py)
        self.data_manager = None
        self.ai_engine = None
        self.notification_dispatcher = None
        self.scheduler = None
        self.db_pool = None

    async def on_ready(self) -> None:
        log.info(
            "bot_ready",
            user=str(self.user),
            guilds=len(self.guilds),
        )

    async def on_application_command_error(
        self, ctx: discord.ApplicationContext, error: Exception
    ) -> None:
        if isinstance(error, discord.errors.CheckFailure):
            await ctx.respond("You don't have permission to use this command.", ephemeral=True)
            return

        log.error("command_error", command=ctx.command.name if ctx.command else "unknown", error=str(error))
        await ctx.respond(
            "An error occurred processing your request. Please try again.",
            ephemeral=True,
        )
