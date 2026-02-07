"""Central scheduler using discord.ext.tasks for periodic polling and timed events."""

import asyncio
import structlog
from discord.ext import tasks
from bot.client import ShaoBuffettBot
from data.manager import DataManager
from ai.engine import AIEngine
from notifications.dispatcher import NotificationDispatcher
from notifications.types import Notification
from storage.repositories.watchlist_repo import WatchlistRepository
from storage.repositories.alert_repo import AlertRepository
from data.processors.news_processor import process_news_articles
from data.processors.price_processor import check_price_alerts
from data.processors.analyst_processor import process_analyst_data
from data.processors.earnings_processor import process_earnings
from data.processors.macro_processor import process_macro_data
from scheduler.jobs import (
    NEWS_POLL_INTERVAL,
    ANALYST_POLL_INTERVAL,
    PRICE_ALERT_INTERVAL,
    MACRO_POLL_INTERVAL,
    CACHE_CLEANUP_INTERVAL,
)
from utils.time_utils import now_et

log = structlog.get_logger(__name__)


class Scheduler:
    """Central scheduler for all periodic tasks."""

    def __init__(
        self,
        bot: ShaoBuffettBot,
        data_manager: DataManager,
        dispatcher: NotificationDispatcher,
        ai_engine: AIEngine,
    ) -> None:
        self.bot = bot
        self.dm = data_manager
        self.dispatcher = dispatcher
        self.ai_engine = ai_engine

    def start(self) -> None:
        """Start all scheduled tasks."""
        self._poll_news.start()
        self._poll_price_alerts.start()
        self._poll_analyst.start()
        self._poll_macro.start()
        self._check_briefings.start()
        self._cleanup_cache.start()
        self._generate_proactive_insights.start()
        log.info("scheduler_all_tasks_started")

    def stop(self) -> None:
        """Stop all scheduled tasks."""
        for task in [
            self._poll_news,
            self._poll_price_alerts,
            self._poll_analyst,
            self._poll_macro,
            self._check_briefings,
            self._cleanup_cache,
            self._generate_proactive_insights,
        ]:
            if task.is_running():
                task.cancel()

    @tasks.loop(seconds=NEWS_POLL_INTERVAL)
    async def _poll_news(self) -> None:
        """Poll for new financial news per watchlist symbol."""
        try:
            watchlist_repo = WatchlistRepository(self.bot.db_pool)
            all_symbols = await watchlist_repo.get_all_symbols()
            if not all_symbols:
                return

            symbols_list = list(all_symbols)[:5]  # Cap to 5 to save Finnhub budget
            log.info("poll_news_start", symbols=len(symbols_list))

            # Fetch news per symbol so articles come back tagged with symbols + sentiment
            all_articles = []
            for symbol in symbols_list:
                try:
                    articles = await self.dm.get_news(symbol=symbol, limit=5)
                    all_articles.extend(articles)
                except Exception as e:
                    log.debug("poll_news_symbol_error", symbol=symbol, error=str(e))

            log.info("poll_news_fetched", articles=len(all_articles))
            notifications = process_news_articles(all_articles, all_symbols)

            for notif in notifications:
                await self.dispatcher.dispatch(notif)

            if notifications:
                log.info("poll_news_dispatched", count=len(notifications))
        except Exception as e:
            log.error("poll_news_error", error=str(e))

    @tasks.loop(seconds=PRICE_ALERT_INTERVAL)
    async def _poll_price_alerts(self) -> None:
        """Check price alerts against current quotes."""
        try:
            alert_repo = AlertRepository(self.bot.db_pool)
            alerts = await alert_repo.get_all_active()
            if not alerts:
                return

            # Fetch quotes for all alerted symbols
            symbols = {a["symbol"] for a in alerts}
            quotes = {}
            for symbol in symbols:
                try:
                    quotes[symbol] = await self.dm.get_quote(symbol)
                except Exception:
                    pass

            triggered = check_price_alerts(alerts, quotes)
            for notif, alert_id in triggered:
                await self.dispatcher.dispatch(notif)
                await alert_repo.trigger(alert_id)
        except Exception as e:
            log.error("poll_price_alerts_error", error=str(e))

    @tasks.loop(seconds=ANALYST_POLL_INTERVAL)
    async def _poll_analyst(self) -> None:
        """Check for analyst rating changes."""
        try:
            watchlist_repo = WatchlistRepository(self.bot.db_pool)
            all_symbols = await watchlist_repo.get_all_symbols()

            for symbol in all_symbols:
                try:
                    data = await self.dm.get_analyst_data(symbol)
                    notifications = process_analyst_data(symbol, data)
                    for notif in notifications:
                        await self.dispatcher.dispatch(notif)
                except Exception as e:
                    log.warning("analyst_poll_symbol_error", symbol=symbol, error=str(e))
        except Exception as e:
            log.error("poll_analyst_error", error=str(e))

    @tasks.loop(seconds=MACRO_POLL_INTERVAL)
    async def _poll_macro(self) -> None:
        """Poll macro economic data for changes."""
        try:
            snapshot = await self.dm.get_macro_data()
            if isinstance(snapshot, dict):
                notifications = process_macro_data(snapshot)
                for notif in notifications:
                    await self.dispatcher.dispatch(notif)
        except Exception as e:
            log.error("poll_macro_error", error=str(e))

    @tasks.loop(minutes=1)
    async def _check_briefings(self) -> None:
        """Check if it's time for morning briefing or evening summary."""
        from scheduler.morning_briefing import generate_morning_briefing
        from scheduler.evening_summary import generate_evening_summary

        now = now_et()
        current_time = now.strftime("%H:%M")

        if current_time == "09:30" and now.weekday() < 5:
            await generate_morning_briefing(self.ai_engine, self.dm, self.dispatcher)
        elif current_time == "16:15" and now.weekday() < 5:
            await generate_evening_summary(self.ai_engine, self.dm, self.dispatcher)

    @tasks.loop(minutes=15)
    async def _generate_proactive_insights(self) -> None:
        """Generate and dispatch proactive insights for users with portfolios."""
        try:
            from scheduler.proactive import ProactiveInsightGenerator
            generator = ProactiveInsightGenerator(
                db_pool=self.bot.db_pool,
                data_manager=self.dm,
                dispatcher=self.dispatcher,
                ai_engine=self.ai_engine,
            )
            created = await generator.generate_all()
            if created > 0:
                sent = await generator.dispatch_pending()
                log.info("proactive_insights_generated", created=created, sent=sent)
        except Exception as e:
            log.error("proactive_insights_error", error=str(e))

    @tasks.loop(seconds=CACHE_CLEANUP_INTERVAL)
    async def _cleanup_cache(self) -> None:
        """Periodically clean expired cache entries."""
        cleaned = self.dm.cache.cleanup()
        if cleaned > 0:
            log.debug("cache_cleaned", entries=cleaned)

    # Ensure loops don't start until bot is ready.
    # Stagger startups to avoid all pollers hitting Finnhub at t=0.
    @_poll_news.before_loop
    async def _before_poll_news(self) -> None:
        await self.bot.wait_until_ready()
        # News starts first (highest priority for user)

    @_poll_price_alerts.before_loop
    async def _before_poll_alerts(self) -> None:
        await self.bot.wait_until_ready()
        await asyncio.sleep(15)  # Stagger: start 15s after news

    @_poll_analyst.before_loop
    async def _before_poll_analyst(self) -> None:
        await self.bot.wait_until_ready()
        await asyncio.sleep(30)  # Stagger: start 30s after news

    @_poll_macro.before_loop
    async def _before_poll_macro(self) -> None:
        await self.bot.wait_until_ready()
        await asyncio.sleep(45)  # Stagger: start 45s after news

    @_check_briefings.before_loop
    async def _before_check_briefings(self) -> None:
        await self.bot.wait_until_ready()

    @_generate_proactive_insights.before_loop
    async def _before_proactive_insights(self) -> None:
        await self.bot.wait_until_ready()
        await asyncio.sleep(60)  # Stagger: start 60s after news

    @_cleanup_cache.before_loop
    async def _before_cleanup_cache(self) -> None:
        await self.bot.wait_until_ready()
