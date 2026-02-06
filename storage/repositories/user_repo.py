"""User profile repository."""

import asyncpg
from typing import Any


class UserRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_or_create(self, discord_id: int) -> dict[str, Any]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM user_profiles WHERE discord_id = $1", discord_id
            )
            if row:
                return dict(row)
            await conn.execute(
                "INSERT INTO user_profiles (discord_id) VALUES ($1) ON CONFLICT DO NOTHING",
                discord_id,
            )
            row = await conn.fetchrow(
                "SELECT * FROM user_profiles WHERE discord_id = $1", discord_id
            )
            return dict(row) if row else {"discord_id": discord_id}

    async def update_interests(self, discord_id: int, interests: dict[str, Any]) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE user_profiles SET interests = $2, updated_at = NOW()
                WHERE discord_id = $1
                """,
                discord_id,
                interests,
            )

    async def update_metrics(self, discord_id: int, metrics: list[str]) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE user_profiles SET focused_metrics = $2::jsonb, updated_at = NOW()
                WHERE discord_id = $1
                """,
                discord_id,
                metrics,
            )

    async def update_risk_tolerance(self, discord_id: int, risk_tolerance: str) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE user_profiles SET risk_tolerance = $2, updated_at = NOW()
                WHERE discord_id = $1
                """,
                discord_id,
                risk_tolerance,
            )

    async def update_notifications(self, discord_id: int, prefs: dict[str, Any]) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE user_profiles SET notification_preferences = $2, updated_at = NOW()
                WHERE discord_id = $1
                """,
                discord_id,
                prefs,
            )

    async def get_all_users(self) -> list[dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM user_profiles")
        return [dict(r) for r in rows]
