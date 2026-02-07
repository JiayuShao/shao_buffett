"""Entry point: initialize services, load cogs, start bot."""

import asyncio
import discord
import structlog
from config.settings import settings
from config.logging_config import setup_logging
from config.constants import EmbedColor
from storage.database import get_pool, close_pool, run_migrations
from bot.client import ShaoBuffettBot
from bot.events import setup_events
from data.manager import DataManager
from ai.engine import AIEngine
from notifications.dispatcher import NotificationDispatcher
from scheduler.scheduler import Scheduler
from utils.embed_builder import make_embed

log = structlog.get_logger(__name__)


async def start_bot() -> None:
    """Initialize all services and start the bot."""
    setup_logging()
    log.info("starting_shao_buffett")

    bot = ShaoBuffettBot()

    # Initialize database
    pool = await get_pool()
    await run_migrations()
    bot.db_pool = pool

    # Initialize data layer
    data_manager = DataManager()
    await data_manager.start()
    bot.data_manager = data_manager

    # Wire rate limit notifications to Discord
    async def on_rate_limit(api_name: str, wait_seconds: float) -> None:
        channel_id = settings.notification_channel_id
        if not channel_id:
            return
        channel = bot.get_channel(channel_id)
        if channel and isinstance(channel, discord.TextChannel):
            if wait_seconds > 0:
                desc = f"**{api_name}** hit its rate limit. Throttling for {wait_seconds:.0f}s."
            else:
                desc = f"**{api_name}** returned HTTP 429 — server-side rate limit reached."
            embed = make_embed("API Rate Limit", desc, color=EmbedColor.ALERT)
            usage = data_manager.rate_limiter.get_usage()
            if api_name in usage:
                info = usage[api_name]
                embed.add_field(name="Usage", value=f"{info['used']}/{info['limit']} req/min", inline=True)
            try:
                await channel.send(embed=embed)
            except Exception as e:
                log.error("rate_limit_notify_failed", error=str(e))

    data_manager.rate_limiter.on_rate_limit = on_rate_limit

    # Initialize AI engine
    ai_engine = AIEngine(data_manager=data_manager, db_pool=pool)
    bot.ai_engine = ai_engine

    # Initialize notification dispatcher
    dispatcher = NotificationDispatcher(bot=bot, db_pool=pool)
    bot.notification_dispatcher = dispatcher

    # Initialize scheduler
    scheduler = Scheduler(
        bot=bot,
        data_manager=data_manager,
        dispatcher=dispatcher,
        ai_engine=ai_engine,
    )
    bot.scheduler = scheduler

    # Setup event handlers
    setup_events(bot)

    # Load cogs
    cog_modules = [
        "bot.cogs.watchlist",
        "bot.cogs.alerts",
        "bot.cogs.news",
        "bot.cogs.research",
        "bot.cogs.dashboard",
        "bot.cogs.profile",
        "bot.cogs.market",
        "bot.cogs.briefing",
        "bot.cogs.chat",
        "bot.cogs.admin",
        "bot.cogs.notes",
        "bot.cogs.portfolio",
    ]
    for module in cog_modules:
        try:
            bot.load_extension(module)
            log.info("cog_loaded", module=module)
        except Exception as e:
            log.error("cog_load_failed", module=module, error=str(e))

    # Start scheduler after bot is ready
    @bot.event
    async def on_ready() -> None:
        scheduler.start()
        log.info("scheduler_started")

    try:
        await bot.start(settings.discord_token)
    finally:
        log.info("shutting_down")
        scheduler.stop()
        await data_manager.close()
        await close_pool()


def main() -> None:
    """Run the bot."""
    asyncio.run(start_bot())


if __name__ == "__main__":
    main()
