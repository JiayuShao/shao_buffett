"""Proactive insight generator — anticipates user needs."""

import structlog
from typing import Any
from data.manager import DataManager
from storage.repositories.portfolio_repo import PortfolioRepository
from storage.repositories.notes_repo import NotesRepository
from storage.repositories.activity_repo import ActivityRepository, ProactiveInsightRepository
from storage.repositories.watchlist_repo import WatchlistRepository
from notifications.dispatcher import NotificationDispatcher
from notifications.types import Notification
from config.constants import NotificationType

log = structlog.get_logger(__name__)

# Thresholds
SIGNIFICANT_MOVE_PCT = 3.0  # >3% daily move triggers alert


class ProactiveInsightGenerator:
    """Cross-references user data with market data to generate proactive insights."""

    def __init__(
        self,
        db_pool: Any,
        data_manager: DataManager,
        dispatcher: NotificationDispatcher,
    ) -> None:
        self.pool = db_pool
        self.dm = data_manager
        self.dispatcher = dispatcher
        self.portfolio_repo = PortfolioRepository(db_pool)
        self.notes_repo = NotesRepository(db_pool)
        self.activity_repo = ActivityRepository(db_pool)
        self.insight_repo = ProactiveInsightRepository(db_pool)
        self.watchlist_repo = WatchlistRepository(db_pool)

    async def generate_all(self) -> int:
        """Generate proactive insights for all users. Returns count of insights created."""
        users = await self.portfolio_repo.get_all_users_with_holdings()
        total = 0

        for user_id in users:
            try:
                count = await self._generate_for_user(user_id)
                total += count
            except Exception as e:
                log.error("proactive_user_error", user_id=user_id, error=str(e))

        return total

    async def _generate_for_user(self, user_id: int) -> int:
        """Generate insights for a specific user."""
        count = 0
        holdings = await self.portfolio_repo.get_holdings(user_id)
        held_symbols = [h["symbol"] for h in holdings]

        if not held_symbols:
            return 0

        # Check for significant price movements on held positions
        count += await self._check_price_movements(user_id, held_symbols)

        # Check for upcoming earnings on held stocks
        count += await self._check_upcoming_earnings(user_id, held_symbols)

        # Check frequently queried symbols not in portfolio/watchlist
        count += await self._suggest_watchlist_additions(user_id, held_symbols)

        # Check for stale action items
        count += await self._check_stale_action_items(user_id)

        return count

    async def _check_price_movements(self, user_id: int, symbols: list[str]) -> int:
        """Check for significant price moves on held positions."""
        count = 0
        for symbol in symbols:
            try:
                quote = await self.dm.get_quote(symbol)
                change_pct = quote.get("dp", quote.get("change_percent", 0))
                if change_pct is None:
                    continue
                change_pct = float(change_pct)

                if abs(change_pct) >= SIGNIFICANT_MOVE_PCT:
                    direction = "up" if change_pct > 0 else "down"
                    price = quote.get("c", quote.get("price", 0))
                    await self.insight_repo.create(
                        discord_id=user_id,
                        insight_type="price_movement",
                        title=f"{symbol} moved {change_pct:+.1f}% today",
                        content=f"Your holding **{symbol}** is {direction} **{change_pct:+.1f}%** today (${price:.2f}). This is a significant move worth monitoring.",
                        symbols=[symbol],
                    )
                    count += 1
            except Exception as e:
                log.debug("price_check_error", symbol=symbol, error=str(e))
        return count

    async def _check_upcoming_earnings(self, user_id: int, symbols: list[str]) -> int:
        """Check for upcoming earnings on held stocks."""
        count = 0
        for symbol in symbols:
            try:
                earnings = await self.dm.get_earnings(symbol)
                if not earnings:
                    continue
                # Check if there's an upcoming earnings date
                latest = earnings[0] if isinstance(earnings, list) and earnings else None
                if latest and latest.get("date"):
                    from datetime import datetime, timedelta
                    try:
                        earn_date = datetime.fromisoformat(str(latest["date"]).replace("Z", "+00:00"))
                        now = datetime.utcnow()
                        days_until = (earn_date.replace(tzinfo=None) - now).days
                        if 0 < days_until <= 7:
                            await self.insight_repo.create(
                                discord_id=user_id,
                                insight_type="earnings_upcoming",
                                title=f"{symbol} earnings in {days_until} day(s)",
                                content=f"Your holding **{symbol}** reports earnings in **{days_until} day(s)**. Consider reviewing your position and setting expectations.",
                                symbols=[symbol],
                            )
                            count += 1
                    except (ValueError, TypeError):
                        pass
            except Exception as e:
                log.debug("earnings_check_error", symbol=symbol, error=str(e))
        return count

    async def _suggest_watchlist_additions(self, user_id: int, held_symbols: list[str]) -> int:
        """Suggest adding frequently queried symbols to watchlist."""
        count = 0
        freq = await self.activity_repo.get_frequently_queried_symbols(user_id, days=14, limit=5)
        watchlist = await self.watchlist_repo.get(user_id)
        tracked = set(held_symbols) | set(watchlist)

        for entry in freq:
            symbol = entry["symbol"]
            query_count = entry["query_count"]
            if symbol not in tracked and query_count >= 3:
                await self.insight_repo.create(
                    discord_id=user_id,
                    insight_type="symbol_suggestion",
                    title=f"You frequently ask about {symbol}",
                    content=f"You've asked about **{symbol}** {query_count} times recently but it's not in your watchlist or portfolio. Want to add it to your watchlist?",
                    symbols=[symbol],
                )
                count += 1
        return count

    async def _check_stale_action_items(self, user_id: int) -> int:
        """Remind about old unresolved action items."""
        count = 0
        items = await self.notes_repo.get_active_action_items(user_id)
        from datetime import datetime, timedelta
        now = datetime.utcnow()

        for item in items:
            created = item["created_at"].replace(tzinfo=None)
            days_old = (now - created).days
            if days_old >= 3:
                symbols = item.get("symbols", [])
                await self.insight_repo.create(
                    discord_id=user_id,
                    insight_type="action_reminder",
                    title=f"Action item pending ({days_old} days)",
                    content=f"Reminder: {item['content']} (noted {days_old} days ago)",
                    symbols=symbols if symbols else [],
                )
                count += 1
        return count

    async def dispatch_pending(self) -> int:
        """Dispatch all undelivered insights as notifications."""
        users = await self.portfolio_repo.get_all_users_with_holdings()
        sent = 0

        for user_id in users:
            insights = await self.insight_repo.get_undelivered(user_id)
            for insight in insights:
                notif = Notification(
                    type=NotificationType.PROACTIVE_INSIGHT,
                    title=insight["title"],
                    description=insight["content"],
                    symbol=insight["symbols"][0] if insight["symbols"] else None,
                    target_users=[user_id],
                    data={"insight_type": insight["insight_type"], "symbols": insight["symbols"]},
                    urgency="medium",
                )
                delivered = await self.dispatcher.dispatch(notif)
                if delivered > 0:
                    await self.insight_repo.mark_delivered(insight["id"])
                    sent += 1

        return sent
