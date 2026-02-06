"""Dashboard configuration repository."""

import asyncpg
from typing import Any


class DashboardRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get(self, dashboard_id: int) -> dict[str, Any] | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM dashboards WHERE id = $1", dashboard_id
            )
        return dict(row) if row else None

    async def get_by_user(self, discord_id: int) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM dashboards WHERE discord_id = $1 ORDER BY created_at",
                discord_id,
            )
        return [dict(r) for r in rows]

    async def create(
        self,
        discord_id: int,
        name: str,
        config: dict[str, Any],
        channel_id: int | None = None,
    ) -> int:
        async with self._pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO dashboards (discord_id, name, config, channel_id)
                VALUES ($1, $2, $3, $4) RETURNING id
                """,
                discord_id,
                name,
                config,
                channel_id,
            )

    async def update_message(self, dashboard_id: int, message_id: int) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE dashboards SET message_id = $2 WHERE id = $1",
                dashboard_id,
                message_id,
            )

    async def update_config(self, dashboard_id: int, config: dict[str, Any]) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE dashboards SET config = $2 WHERE id = $1",
                dashboard_id,
                config,
            )

    async def delete(self, dashboard_id: int, discord_id: int) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM dashboards WHERE id = $1 AND discord_id = $2",
                dashboard_id,
                discord_id,
            )
        return result.split()[-1] != "0"

    async def get_auto_refresh(self) -> list[dict[str, Any]]:
        """Get dashboards that have auto-refresh enabled."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM dashboards
                WHERE auto_refresh_minutes > 0 AND message_id IS NOT NULL
                """
            )
        return [dict(r) for r in rows]
