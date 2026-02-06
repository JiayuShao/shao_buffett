"""Conversation repository — thin wrapper, main logic in ai/conversation.py."""

import asyncpg
from typing import Any


class ConversationRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_recent(
        self, discord_id: int, channel_id: int, limit: int = 20
    ) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT role, content, model_used, created_at
                FROM conversations
                WHERE discord_id = $1 AND channel_id = $2
                ORDER BY created_at DESC LIMIT $3
                """,
                discord_id,
                channel_id,
                limit,
            )
        return [dict(r) for r in reversed(rows)]

    async def count(self, discord_id: int) -> int:
        async with self._pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT COUNT(*) FROM conversations WHERE discord_id = $1",
                discord_id,
            )
