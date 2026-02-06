"""Route notifications to subscribers via Discord channels/DMs."""

import discord
import asyncpg
import structlog
from notifications.types import Notification
from notifications.formatter import format_notification
from notifications.filters import NotificationFilter
from config.settings import settings
from storage.repositories.user_repo import UserRepository

log = structlog.get_logger(__name__)


class NotificationDispatcher:
    """Dispatch notifications to the right users via Discord."""

    def __init__(self, bot: discord.Bot, db_pool: asyncpg.Pool) -> None:
        self._bot = bot
        self._pool = db_pool
        self._filter = NotificationFilter(db_pool)
        self._user_repo = UserRepository(db_pool)

    async def dispatch(self, notif: Notification) -> int:
        """Dispatch a notification. Returns count of users notified."""
        # Check for duplicates
        if await self._filter.is_duplicate(notif):
            log.debug("notification_dedup", type=notif.type.value, hash=notif.content_hash)
            return 0

        # Determine target users
        target_users = await self._filter.get_target_users(notif)
        if not target_users:
            return 0

        embed = format_notification(notif)
        sent_count = 0

        for user_id in target_users:
            try:
                # Check user's delivery preference
                profile = await self._user_repo.get_or_create(user_id)
                prefs = profile.get("notification_preferences", {})
                delivery = prefs.get("delivery", "channel")

                if delivery == "dm":
                    await self._send_dm(user_id, embed)
                else:
                    await self._send_channel(embed)
                sent_count += 1
            except Exception as e:
                log.error("notification_send_error", user_id=user_id, error=str(e))

        # Log for dedup
        await self._filter.log_notification(notif)
        log.info("notification_dispatched", type=notif.type.value, users=sent_count)
        return sent_count

    async def broadcast(self, embed: discord.Embed) -> None:
        """Send an embed to the notification channel (no targeting)."""
        await self._send_channel(embed)

    async def _send_channel(self, embed: discord.Embed) -> None:
        """Send to the configured notification channel."""
        channel_id = settings.notification_channel_id
        if not channel_id:
            return

        channel = self._bot.get_channel(channel_id)
        if channel and isinstance(channel, discord.TextChannel):
            await channel.send(embed=embed)

    async def _send_dm(self, user_id: int, embed: discord.Embed) -> None:
        """Send a DM to a user."""
        user = self._bot.get_user(user_id)
        if user is None:
            try:
                user = await self._bot.fetch_user(user_id)
            except discord.NotFound:
                return

        if user:
            try:
                await user.send(embed=embed)
            except discord.Forbidden:
                # User has DMs disabled; fall back to channel
                await self._send_channel(embed)
