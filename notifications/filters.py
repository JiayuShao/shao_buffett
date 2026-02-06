"""User interest matching and dedup for notifications."""

import asyncpg
import structlog
from notifications.types import Notification
from storage.repositories.watchlist_repo import WatchlistRepository
from storage.repositories.user_repo import UserRepository

log = structlog.get_logger(__name__)


class NotificationFilter:
    """Filter and match notifications to interested users."""

    def __init__(self, db_pool: asyncpg.Pool) -> None:
        self._pool = db_pool
        self._watchlist_repo = WatchlistRepository(db_pool)
        self._user_repo = UserRepository(db_pool)

    async def get_target_users(self, notif: Notification) -> list[int]:
        """Determine which users should receive this notification."""
        if notif.target_users is not None:
            return notif.target_users

        target_users: set[int] = set()

        # If notification is about a specific symbol, find users watching it
        if notif.symbol:
            users = await self._watchlist_repo.get_users_for_symbol(notif.symbol)
            target_users.update(users)

        # For general notifications (macro, market-wide), send to all users
        if not notif.symbol:
            all_users = await self._user_repo.get_all_users()
            target_users.update(u["discord_id"] for u in all_users)

        return list(target_users)

    async def is_duplicate(self, notif: Notification) -> bool:
        """Check if this notification was recently sent (dedup)."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id FROM notification_log
                WHERE content_hash = $1 AND created_at > NOW() - INTERVAL '6 hours'
                """,
                notif.content_hash,
            )
        return row is not None

    async def log_notification(self, notif: Notification) -> None:
        """Log a sent notification for dedup."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO notification_log (notification_type, content_hash, symbol)
                VALUES ($1, $2, $3)
                """,
                notif.type.value,
                notif.content_hash,
                notif.symbol,
            )
