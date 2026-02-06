"""User activity and proactive insight repositories."""

import asyncpg
from typing import Any


class ActivityRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def log_activity(
        self,
        discord_id: int,
        query_type: str,
        symbols: list[str] | None = None,
    ) -> None:
        """Log a user interaction."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO user_activity (discord_id, query_type, symbols) VALUES ($1, $2, $3)",
                discord_id,
                query_type,
                symbols or [],
            )

    async def get_frequently_queried_symbols(
        self, discord_id: int, days: int = 30, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get symbols the user queries most often."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT symbol, COUNT(*) as query_count
                FROM user_activity, unnest(symbols) AS symbol
                WHERE discord_id = $1 AND created_at > NOW() - INTERVAL '1 day' * $2
                GROUP BY symbol
                ORDER BY query_count DESC
                LIMIT $3
                """,
                discord_id,
                days,
                limit,
            )
        return [dict(r) for r in rows]

    async def get_activity_summary(
        self, discord_id: int, days: int = 7
    ) -> dict[str, Any]:
        """Get activity summary for a user."""
        async with self._pool.acquire() as conn:
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM user_activity WHERE discord_id = $1 AND created_at > NOW() - INTERVAL '1 day' * $2",
                discord_id,
                days,
            )
            types = await conn.fetch(
                """
                SELECT query_type, COUNT(*) as count
                FROM user_activity
                WHERE discord_id = $1 AND created_at > NOW() - INTERVAL '1 day' * $2
                GROUP BY query_type ORDER BY count DESC
                """,
                discord_id,
                days,
            )
        return {
            "total_queries": total,
            "by_type": {r["query_type"]: r["count"] for r in types},
        }


class ProactiveInsightRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create(
        self,
        discord_id: int,
        insight_type: str,
        title: str,
        content: str,
        symbols: list[str] | None = None,
    ) -> int:
        """Create a proactive insight. Returns the insight ID."""
        async with self._pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO proactive_insights (discord_id, insight_type, title, content, symbols)
                VALUES ($1, $2, $3, $4, $5) RETURNING id
                """,
                discord_id,
                insight_type,
                title,
                content,
                symbols or [],
            )

    async def get_undelivered(self, discord_id: int) -> list[dict[str, Any]]:
        """Get undelivered insights for a user."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, insight_type, title, content, symbols, created_at
                FROM proactive_insights
                WHERE discord_id = $1 AND is_delivered = FALSE
                ORDER BY created_at DESC
                """,
                discord_id,
            )
        return [dict(r) for r in rows]

    async def mark_delivered(self, insight_id: int) -> None:
        """Mark an insight as delivered."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE proactive_insights SET is_delivered = TRUE WHERE id = $1",
                insight_id,
            )

    async def cleanup_old(self, days: int = 7) -> int:
        """Delete delivered insights older than N days."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM proactive_insights WHERE is_delivered = TRUE AND created_at < NOW() - INTERVAL '1 day' * $1",
                days,
            )
        return int(result.split()[-1])
