"""Entry point: initialize services, load cogs, start bot."""

import asyncio
import structlog
from config.settings import settings
from config.logging_config import setup_logging
from storage.database import get_pool, close_pool, run_migrations
from bot.client import BuffetShaoBot
from bot.events import setup_events
from data.manager import DataManager
from ai.engine import AIEngine
from notifications.dispatcher import NotificationDispatcher
from scheduler.scheduler import Scheduler

log = structlog.get_logger(__name__)


async def start_bot() -> None:
    """Initialize all services and start the bot."""
    setup_logging()
    log.info("starting_buffet_shao")

    bot = BuffetShaoBot()

    # Initialize database
    pool = await get_pool()
    await run_migrations()
    bot.db_pool = pool

    # Initialize data layer
    data_manager = DataManager()
    await data_manager.start()
    bot.data_manager = data_manager

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
