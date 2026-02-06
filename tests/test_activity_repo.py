"""Tests for storage/repositories/activity_repo.py — activity and insight repos."""

import pytest
from datetime import datetime
from storage.repositories.activity_repo import ActivityRepository, ProactiveInsightRepository


class TestActivityRepository:
    @pytest.fixture
    def repo(self, fake_pool):
        return ActivityRepository(fake_pool)

    async def test_log_activity(self, repo, fake_conn):
        await repo.log_activity(12345, "price_check", ["AAPL", "MSFT"])
        assert len(fake_conn._execute_calls) == 1
        query, args = fake_conn._execute_calls[0]
        assert "INSERT INTO user_activity" in query
        assert args[0] == 12345
        assert args[1] == "price_check"
        assert args[2] == ["AAPL", "MSFT"]

    async def test_log_activity_no_symbols(self, repo, fake_conn):
        await repo.log_activity(12345, "general")
        query, args = fake_conn._execute_calls[0]
        assert args[2] == []

    async def test_get_frequently_queried_symbols(self, repo, fake_conn):
        fake_conn.fetch_results = [[
            {"symbol": "AAPL", "query_count": 15},
            {"symbol": "NVDA", "query_count": 8},
        ]]
        result = await repo.get_frequently_queried_symbols(12345, days=30)
        assert len(result) == 2
        assert result[0]["symbol"] == "AAPL"
        assert result[0]["query_count"] == 15

    async def test_get_activity_summary(self, repo, fake_conn):
        fake_conn.fetchval_result = 42
        fake_conn.fetch_results = [[
            {"query_type": "price_check", "count": 20},
            {"query_type": "analysis", "count": 12},
        ]]
        summary = await repo.get_activity_summary(12345, days=7)
        assert summary["total_queries"] == 42
        assert summary["by_type"]["price_check"] == 20
        assert summary["by_type"]["analysis"] == 12


class TestProactiveInsightRepository:
    @pytest.fixture
    def repo(self, fake_pool):
        return ProactiveInsightRepository(fake_pool)

    async def test_create_insight(self, repo, fake_conn):
        fake_conn.fetchval_result = 99
        insight_id = await repo.create(
            discord_id=12345,
            insight_type="price_movement",
            title="AAPL moved +5%",
            content="Your holding AAPL is up 5%",
            symbols=["AAPL"],
        )
        assert insight_id == 99

    async def test_create_insight_no_symbols(self, repo, fake_conn):
        fake_conn.fetchval_result = 100
        insight_id = await repo.create(
            discord_id=12345,
            insight_type="action_reminder",
            title="Pending action",
            content="Reminder about something",
        )
        assert insight_id == 100

    async def test_get_undelivered(self, repo, fake_conn):
        fake_conn.fetch_results = [[
            {"id": 1, "insight_type": "price_movement", "title": "AAPL +5%",
             "content": "Big move", "symbols": ["AAPL"], "created_at": datetime.utcnow()},
        ]]
        insights = await repo.get_undelivered(12345)
        assert len(insights) == 1
        assert insights[0]["insight_type"] == "price_movement"

    async def test_get_undelivered_empty(self, repo, fake_conn):
        fake_conn.fetch_results = [[]]
        insights = await repo.get_undelivered(12345)
        assert insights == []

    async def test_mark_delivered(self, repo, fake_conn):
        await repo.mark_delivered(1)
        assert len(fake_conn._execute_calls) == 1
        query, args = fake_conn._execute_calls[0]
        assert "is_delivered = TRUE" in query

    async def test_cleanup_old(self, repo, fake_conn):
        fake_conn.execute_results = ["DELETE 5"]
        cleaned = await repo.cleanup_old(days=7)
        assert cleaned == 5

    async def test_cleanup_old_nothing(self, repo, fake_conn):
        fake_conn.execute_results = ["DELETE 0"]
        cleaned = await repo.cleanup_old(days=7)
        assert cleaned == 0
