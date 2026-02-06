"""Persistent cache repository (survives restarts)."""

import asyncpg
import orjson
from typing import Any
from datetime import datetime, timezone, timedelta


class CacheRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get(self, key: str) -> Any | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT value FROM data_cache WHERE key = $1 AND expires_at > NOW()",
                key,
            )
        if row:
            return orjson.loads(row["value"])
        return None

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        json_value = orjson.dumps(value).decode()
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO data_cache (key, value, expires_at)
                VALUES ($1, $2::jsonb, $3)
                ON CONFLICT (key) DO UPDATE SET value = $2::jsonb, expires_at = $3
                """,
                key,
                json_value,
                expires_at,
            )

    async def delete(self, key: str) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute("DELETE FROM data_cache WHERE key = $1", key)

    async def cleanup_expired(self) -> int:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM data_cache WHERE expires_at < NOW()"
            )
        return int(result.split()[-1])
