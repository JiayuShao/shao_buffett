"""Conversation context manager — history and user profile."""

import asyncpg
import structlog
from typing import Any
from config.constants import MAX_CONVERSATION_HISTORY

log = structlog.get_logger(__name__)


class ConversationManager:
    """Manages conversation history and user context."""

    def __init__(self, db_pool: asyncpg.Pool) -> None:
        self._pool = db_pool

    async def get_history(
        self,
        user_id: int,
        channel_id: int,
        limit: int = MAX_CONVERSATION_HISTORY,
    ) -> list[dict[str, str]]:
        """Get recent conversation history for a user in a channel."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT role, content FROM conversations
                WHERE discord_id = $1 AND channel_id = $2
                ORDER BY created_at DESC LIMIT $3
                """,
                user_id,
                channel_id,
                limit,
            )
        # Reverse to get chronological order
        # Summaries are stored with role='system' but the API only accepts user/assistant
        return [
            {"role": "user" if row["role"] == "system" else row["role"], "content": row["content"]}
            for row in reversed(rows)
        ]

    async def save_message(
        self,
        user_id: int,
        channel_id: int,
        role: str,
        content: str,
        model_used: str | None = None,
    ) -> None:
        """Save a message to conversation history."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO conversations (discord_id, channel_id, role, content, model_used)
                VALUES ($1, $2, $3, $4, $5)
                """,
                user_id,
                channel_id,
                role,
                content[:10000],  # Truncate very long messages
                model_used,
            )

    async def get_user_profile(self, user_id: int) -> dict[str, Any]:
        """Get user profile for context injection."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM user_profiles WHERE discord_id = $1", user_id
            )
            if row:
                return dict(row)

            # Create default profile
            await conn.execute(
                "INSERT INTO user_profiles (discord_id) VALUES ($1) ON CONFLICT DO NOTHING",
                user_id,
            )
            return {
                "discord_id": user_id,
                "interests": {},
                "focused_metrics": ["pe_ratio", "revenue_growth", "eps", "dividend_yield"],
                "notification_preferences": {"delivery": "channel", "quiet_hours": None},
                "risk_tolerance": "moderate",
            }

    async def get_user_watchlist(self, user_id: int) -> list[str]:
        """Get user's watchlist symbols."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT symbol FROM watchlists WHERE discord_id = $1 ORDER BY added_at",
                user_id,
            )
        return [row["symbol"] for row in rows]

    async def clear_history(self, user_id: int, channel_id: int) -> int:
        """Clear conversation history for a user in a channel."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM conversations WHERE discord_id = $1 AND channel_id = $2",
                user_id,
                channel_id,
            )
        count = int(result.split()[-1])
        return count

    async def summarize_if_needed(self, user_id: int, channel_id: int, ai_engine: Any) -> None:
        """Summarize old messages when conversation exceeds 15 messages.

        Keeps the most recent 10 messages intact and compresses the rest
        into a summary stored as a special message.
        """
        async with self._pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM conversations WHERE discord_id = $1 AND channel_id = $2",
                user_id, channel_id,
            )
            if count is None or count <= 20:
                return

            # Get all messages ordered chronologically
            all_rows = await conn.fetch(
                """
                SELECT id, role, content, is_summary FROM conversations
                WHERE discord_id = $1 AND channel_id = $2
                ORDER BY created_at ASC
                """,
                user_id, channel_id,
            )

        # Keep the most recent 10, summarize the rest
        to_summarize = all_rows[:-10]
        if not to_summarize:
            return

        # Build text from old messages (skip existing summaries' meta, include their content)
        text_parts = []
        for row in to_summarize:
            text_parts.append(f"{row['role']}: {row['content']}")
        text = "\n".join(text_parts)

        try:
            summary = await ai_engine.analyze(
                prompt=(
                    "Summarize this conversation in 2-3 sentences, focusing on key topics, "
                    "decisions, and any stocks/positions discussed:\n\n" + text
                ),
                force_model="haiku",
            )
        except Exception as e:
            log.warning("summarization_failed", error=str(e))
            return

        # Delete old messages and insert summary
        ids_to_delete = [row["id"] for row in to_summarize]
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    "DELETE FROM conversations WHERE id = ANY($1::int[])",
                    ids_to_delete,
                )
                await conn.execute(
                    """
                    INSERT INTO conversations (discord_id, channel_id, role, content, is_summary)
                    VALUES ($1, $2, 'system', $3, TRUE)
                    """,
                    user_id, channel_id,
                    f"[Previous conversation summary] {summary}",
                )
