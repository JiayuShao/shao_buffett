"""Tests for storage/repositories/notes_repo.py — notes CRUD."""

import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from storage.repositories.notes_repo import NotesRepository


class TestNotesRepository:
    @pytest.fixture
    def repo(self, fake_pool):
        return NotesRepository(fake_pool)

    async def test_add_returns_note_id(self, repo, fake_conn):
        fake_conn.fetchval_result = 42
        note_id = await repo.add(
            discord_id=12345,
            note_type="concern",
            content="Worried about NVDA PE",
            symbols=["NVDA"],
        )
        assert note_id == 42
        assert len(fake_conn._execute_calls) == 0  # Uses fetchval, not execute

    async def test_add_with_expiry(self, repo, fake_conn):
        fake_conn.fetchval_result = 1
        note_id = await repo.add(
            discord_id=12345,
            note_type="action_item",
            content="Check AAPL earnings",
            expires_days=7,
        )
        assert note_id == 1

    async def test_add_without_symbols(self, repo, fake_conn):
        fake_conn.fetchval_result = 5
        note_id = await repo.add(
            discord_id=12345,
            note_type="insight",
            content="Market looking bullish",
        )
        assert note_id == 5

    async def test_get_recent(self, repo, fake_conn):
        fake_conn.fetch_results = [[
            {"id": 1, "note_type": "concern", "content": "Test", "symbols": ["AAPL"], "is_resolved": False, "created_at": datetime.now(UTC)},
            {"id": 2, "note_type": "insight", "content": "Test2", "symbols": [], "is_resolved": False, "created_at": datetime.now(UTC)},
        ]]
        notes = await repo.get_recent(12345, limit=10)
        assert len(notes) == 2
        assert notes[0]["note_type"] == "concern"

    async def test_get_by_type(self, repo, fake_conn):
        fake_conn.fetch_results = [[
            {"id": 1, "note_type": "concern", "content": "Worried", "symbols": [], "is_resolved": False, "created_at": datetime.now(UTC)},
        ]]
        notes = await repo.get_by_type(12345, "concern")
        assert len(notes) == 1
        assert notes[0]["note_type"] == "concern"

    async def test_get_for_symbols(self, repo, fake_conn):
        fake_conn.fetch_results = [[
            {"id": 1, "note_type": "concern", "content": "NVDA PE high", "symbols": ["NVDA"], "is_resolved": False, "created_at": datetime.now(UTC)},
        ]]
        notes = await repo.get_for_symbols(12345, ["NVDA"])
        assert len(notes) == 1

    async def test_search(self, repo, fake_conn):
        fake_conn.fetch_results = [[
            {"id": 1, "note_type": "insight", "content": "PE ratio is elevated", "symbols": [], "is_resolved": False, "created_at": datetime.now(UTC)},
        ]]
        notes = await repo.search(12345, "PE ratio")
        assert len(notes) == 1
        assert "PE ratio" in notes[0]["content"]

    async def test_get_active_action_items(self, repo, fake_conn):
        fake_conn.fetch_results = [[
            {"id": 3, "content": "Review AAPL position", "symbols": ["AAPL"], "created_at": datetime.now(UTC)},
        ]]
        items = await repo.get_active_action_items(12345)
        assert len(items) == 1
        assert items[0]["content"] == "Review AAPL position"

    async def test_resolve_action_item_success(self, repo, fake_conn):
        fake_conn.execute_results = ["UPDATE 1"]
        resolved = await repo.resolve_action_item(3, 12345)
        assert resolved is True

    async def test_resolve_action_item_not_found(self, repo, fake_conn):
        fake_conn.execute_results = ["UPDATE 0"]
        resolved = await repo.resolve_action_item(999, 12345)
        assert resolved is False

    async def test_delete_success(self, repo, fake_conn):
        fake_conn.execute_results = ["DELETE 1"]
        deleted = await repo.delete(3, 12345)
        assert deleted is True

    async def test_delete_not_found(self, repo, fake_conn):
        fake_conn.execute_results = ["DELETE 0"]
        deleted = await repo.delete(999, 12345)
        assert deleted is False

    async def test_get_recent_empty(self, repo, fake_conn):
        fake_conn.fetch_results = [[]]
        notes = await repo.get_recent(12345)
        assert notes == []
