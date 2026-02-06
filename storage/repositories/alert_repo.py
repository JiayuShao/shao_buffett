"""Price alert repository."""

import asyncpg
from typing import Any
from config.constants import MAX_ALERTS_PER_USER


class AlertRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_active(self, discord_id: int) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM price_alerts
                WHERE discord_id = $1 AND is_active = TRUE
                ORDER BY created_at
                """,
                discord_id,
            )
        return [dict(r) for r in rows]

    async def get_all_active(self) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM price_alerts WHERE is_active = TRUE"
            )
        return [dict(r) for r in rows]

    async def create(
        self,
        discord_id: int,
        symbol: str,
        condition: str,
        threshold: float,
    ) -> int | None:
        """Create an alert. Returns alert ID or None if limit reached."""
        async with self._pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM price_alerts WHERE discord_id = $1 AND is_active = TRUE",
                discord_id,
            )
            if count >= MAX_ALERTS_PER_USER:
                return None
            alert_id = await conn.fetchval(
                """
                INSERT INTO price_alerts (discord_id, symbol, condition, threshold)
                VALUES ($1, $2, $3, $4) RETURNING id
                """,
                discord_id,
                symbol.upper(),
                condition,
                threshold,
            )
        return alert_id

    async def trigger(self, alert_id: int) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE price_alerts
                SET is_active = FALSE, triggered_at = NOW()
                WHERE id = $1
                """,
                alert_id,
            )

    async def remove(self, alert_id: int, discord_id: int) -> bool:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM price_alerts WHERE id = $1 AND discord_id = $2",
                alert_id,
                discord_id,
            )
        return result.split()[-1] != "0"
