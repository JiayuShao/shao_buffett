"""Conversation notes repository — cross-conversation memory."""

import asyncpg
from datetime import datetime, timedelta
from typing import Any


class NotesRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def add(
        self,
        discord_id: int,
        note_type: str,
        content: str,
        symbols: list[str] | None = None,
        expires_days: int | None = None,
    ) -> int:
        """Save a note. Returns the note ID."""
        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)

        async with self._pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO conversation_notes (discord_id, note_type, content, symbols, expires_at)
                VALUES ($1, $2, $3, $4, $5) RETURNING id
                """,
                discord_id,
                note_type,
                content,
                symbols or [],
                expires_at,
            )

    async def get_recent(
        self,
        discord_id: int,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get recent notes for a user."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, note_type, content, symbols, is_resolved, created_at
                FROM conversation_notes
                WHERE discord_id = $1
                  AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY created_at DESC
                LIMIT $2
                """,
                discord_id,
                limit,
            )
        return [dict(r) for r in rows]

    async def get_by_type(
        self,
        discord_id: int,
        note_type: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get notes filtered by type."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, note_type, content, symbols, is_resolved, created_at
                FROM conversation_notes
                WHERE discord_id = $1 AND note_type = $2
                  AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY created_at DESC
                LIMIT $3
                """,
                discord_id,
                note_type,
                limit,
            )
        return [dict(r) for r in rows]

    async def get_for_symbols(
        self,
        discord_id: int,
        symbols: list[str],
    ) -> list[dict[str, Any]]:
        """Get notes mentioning any of the given symbols."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, note_type, content, symbols, is_resolved, created_at
                FROM conversation_notes
                WHERE discord_id = $1 AND symbols && $2
                  AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY created_at DESC
                LIMIT 20
                """,
                discord_id,
                symbols,
            )
        return [dict(r) for r in rows]

    async def search(
        self,
        discord_id: int,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Full-text search on note content."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, note_type, content, symbols, is_resolved, created_at
                FROM conversation_notes
                WHERE discord_id = $1 AND content ILIKE $2
                  AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY created_at DESC
                LIMIT $3
                """,
                discord_id,
                f"%{query}%",
                limit,
            )
        return [dict(r) for r in rows]

    async def get_active_action_items(
        self,
        discord_id: int,
    ) -> list[dict[str, Any]]:
        """Get unresolved action items."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, content, symbols, created_at
                FROM conversation_notes
                WHERE discord_id = $1 AND note_type = 'action_item' AND is_resolved = FALSE
                  AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY created_at DESC
                """,
                discord_id,
            )
        return [dict(r) for r in rows]

    async def resolve_action_item(self, note_id: int, discord_id: int) -> bool:
        """Mark an action item as resolved. Returns True if updated."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE conversation_notes SET is_resolved = TRUE
                WHERE id = $1 AND discord_id = $2 AND note_type = 'action_item'
                """,
                note_id,
                discord_id,
            )
        return result.split()[-1] != "0"

    async def delete(self, note_id: int, discord_id: int) -> bool:
        """Delete a note. Returns True if deleted."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM conversation_notes WHERE id = $1 AND discord_id = $2",
                note_id,
                discord_id,
            )
        return result.split()[-1] != "0"
