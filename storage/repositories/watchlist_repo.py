"""Watchlist repository."""

import asyncpg
from config.constants import MAX_WATCHLIST_SIZE


class WatchlistRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get(self, discord_id: int) -> list[str]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT symbol FROM watchlists WHERE discord_id = $1 ORDER BY added_at",
                discord_id,
            )
        return [row["symbol"] for row in rows]

    async def add(self, discord_id: int, symbol: str) -> bool:
        """Add a symbol. Returns False if watchlist is full or already exists."""
        async with self._pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM watchlists WHERE discord_id = $1", discord_id
            )
            if count >= MAX_WATCHLIST_SIZE:
                return False
            try:
                await conn.execute(
                    "INSERT INTO watchlists (discord_id, symbol) VALUES ($1, $2)",
                    discord_id,
                    symbol.upper(),
                )
                return True
            except asyncpg.UniqueViolationError:
                return False

    async def remove(self, discord_id: int, symbol: str) -> bool:
        """Remove a symbol. Returns True if it was removed."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM watchlists WHERE discord_id = $1 AND symbol = $2",
                discord_id,
                symbol.upper(),
            )
        return result.split()[-1] != "0"

    async def get_all_users_with_watchlist(self) -> list[int]:
        """Get all discord_ids that have watchlist entries."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT DISTINCT discord_id FROM watchlists"
            )
        return [r["discord_id"] for r in rows]

    async def get_all_symbols(self) -> set[str]:
        """Get all unique symbols across all users' watchlists."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT DISTINCT symbol FROM watchlists")
        return {row["symbol"] for row in rows}

    async def get_users_for_symbol(self, symbol: str) -> list[int]:
        """Get all user IDs watching a given symbol."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT discord_id FROM watchlists WHERE symbol = $1", symbol.upper()
            )
        return [row["discord_id"] for row in rows]
