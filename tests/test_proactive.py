"""Tests for scheduler/proactive.py — proactive insight generation."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from scheduler.proactive import ProactiveInsightGenerator, SIGNIFICANT_MOVE_PCT


class TestProactiveInsightGenerator:
    @pytest.fixture
    def generator(self, mock_data_manager, mock_dispatcher, fake_pool):
        gen = ProactiveInsightGenerator(
            db_pool=fake_pool,
            data_manager=mock_data_manager,
            dispatcher=mock_dispatcher,
        )
        # Mock repos
        gen.portfolio_repo = MagicMock()
        gen.notes_repo = MagicMock()
        gen.activity_repo = MagicMock()
        gen.insight_repo = MagicMock()
        gen.watchlist_repo = MagicMock()
        return gen


class TestCheckPriceMovements(TestProactiveInsightGenerator):
    async def test_creates_insight_for_big_move(self, generator, mock_data_manager):
        mock_data_manager.get_quote = AsyncMock(return_value={"dp": 5.2, "c": 195.0})
        generator.insight_repo.create = AsyncMock(return_value=1)

        count = await generator._check_price_movements(12345, ["AAPL"])
        assert count == 1
        generator.insight_repo.create.assert_awaited_once()
        call_kwargs = generator.insight_repo.create.call_args[1]
        assert call_kwargs["insight_type"] == "price_movement"
        assert "AAPL" in call_kwargs["symbols"]
        assert "+5.2%" in call_kwargs["title"]

    async def test_creates_insight_for_big_drop(self, generator, mock_data_manager):
        mock_data_manager.get_quote = AsyncMock(return_value={"dp": -4.1, "c": 170.0})
        generator.insight_repo.create = AsyncMock(return_value=1)

        count = await generator._check_price_movements(12345, ["NVDA"])
        assert count == 1
        call_kwargs = generator.insight_repo.create.call_args[1]
        assert "down" in call_kwargs["content"]

    async def test_no_insight_for_small_move(self, generator, mock_data_manager):
        mock_data_manager.get_quote = AsyncMock(return_value={"dp": 1.5, "c": 186.0})
        generator.insight_repo.create = AsyncMock()

        count = await generator._check_price_movements(12345, ["AAPL"])
        assert count == 0
        generator.insight_repo.create.assert_not_awaited()

    async def test_handles_none_change_pct(self, generator, mock_data_manager):
        mock_data_manager.get_quote = AsyncMock(return_value={"dp": None, "c": 100.0})
        generator.insight_repo.create = AsyncMock()

        count = await generator._check_price_movements(12345, ["XYZ"])
        assert count == 0

    async def test_handles_quote_error(self, generator, mock_data_manager):
        mock_data_manager.get_quote = AsyncMock(side_effect=Exception("API error"))
        generator.insight_repo.create = AsyncMock()

        count = await generator._check_price_movements(12345, ["AAPL"])
        assert count == 0

    async def test_multiple_symbols(self, generator, mock_data_manager):
        async def mock_quote(symbol):
            if symbol == "AAPL":
                return {"dp": 5.0, "c": 195.0}
            else:
                return {"dp": 1.0, "c": 380.0}

        mock_data_manager.get_quote = AsyncMock(side_effect=mock_quote)
        generator.insight_repo.create = AsyncMock(return_value=1)

        count = await generator._check_price_movements(12345, ["AAPL", "MSFT"])
        assert count == 1  # Only AAPL triggered

    async def test_uses_change_percent_fallback(self, generator, mock_data_manager):
        mock_data_manager.get_quote = AsyncMock(return_value={"change_percent": 4.0, "price": 200.0})
        generator.insight_repo.create = AsyncMock(return_value=1)

        count = await generator._check_price_movements(12345, ["AAPL"])
        assert count == 1


class TestCheckUpcomingEarnings(TestProactiveInsightGenerator):
    async def test_creates_insight_for_upcoming_earnings(self, generator, mock_data_manager):
        future_date = (datetime.utcnow() + timedelta(days=3)).isoformat()
        mock_data_manager.get_earnings = AsyncMock(return_value=[{"date": future_date}])
        generator.insight_repo.create = AsyncMock(return_value=1)

        count = await generator._check_upcoming_earnings(12345, ["AAPL"])
        assert count == 1
        call_kwargs = generator.insight_repo.create.call_args[1]
        assert call_kwargs["insight_type"] == "earnings_upcoming"
        assert "day" in call_kwargs["title"]
        assert "AAPL" in call_kwargs["title"]

    async def test_no_insight_for_distant_earnings(self, generator, mock_data_manager):
        future_date = (datetime.utcnow() + timedelta(days=30)).isoformat()
        mock_data_manager.get_earnings = AsyncMock(return_value=[{"date": future_date}])
        generator.insight_repo.create = AsyncMock()

        count = await generator._check_upcoming_earnings(12345, ["AAPL"])
        assert count == 0

    async def test_no_insight_for_past_earnings(self, generator, mock_data_manager):
        past_date = (datetime.utcnow() - timedelta(days=5)).isoformat()
        mock_data_manager.get_earnings = AsyncMock(return_value=[{"date": past_date}])
        generator.insight_repo.create = AsyncMock()

        count = await generator._check_upcoming_earnings(12345, ["AAPL"])
        assert count == 0

    async def test_no_earnings_data(self, generator, mock_data_manager):
        mock_data_manager.get_earnings = AsyncMock(return_value=[])
        count = await generator._check_upcoming_earnings(12345, ["AAPL"])
        assert count == 0

    async def test_handles_earnings_error(self, generator, mock_data_manager):
        mock_data_manager.get_earnings = AsyncMock(side_effect=Exception("err"))
        count = await generator._check_upcoming_earnings(12345, ["AAPL"])
        assert count == 0


class TestSuggestWatchlistAdditions(TestProactiveInsightGenerator):
    async def test_suggests_frequently_queried_symbol(self, generator):
        generator.activity_repo.get_frequently_queried_symbols = AsyncMock(return_value=[
            {"symbol": "TSLA", "query_count": 5},
        ])
        generator.watchlist_repo.get = AsyncMock(return_value=["AAPL"])
        generator.insight_repo.create = AsyncMock(return_value=1)

        count = await generator._suggest_watchlist_additions(12345, ["AAPL"])
        assert count == 1
        call_kwargs = generator.insight_repo.create.call_args[1]
        assert call_kwargs["insight_type"] == "symbol_suggestion"
        assert "TSLA" in call_kwargs["title"]

    async def test_no_suggestion_for_tracked_symbol(self, generator):
        generator.activity_repo.get_frequently_queried_symbols = AsyncMock(return_value=[
            {"symbol": "AAPL", "query_count": 10},  # Already in portfolio
        ])
        generator.watchlist_repo.get = AsyncMock(return_value=[])
        generator.insight_repo.create = AsyncMock()

        count = await generator._suggest_watchlist_additions(12345, ["AAPL"])
        assert count == 0

    async def test_no_suggestion_for_watchlisted_symbol(self, generator):
        generator.activity_repo.get_frequently_queried_symbols = AsyncMock(return_value=[
            {"symbol": "TSLA", "query_count": 5},
        ])
        generator.watchlist_repo.get = AsyncMock(return_value=["TSLA"])  # Already watched
        generator.insight_repo.create = AsyncMock()

        count = await generator._suggest_watchlist_additions(12345, ["AAPL"])
        assert count == 0

    async def test_no_suggestion_below_threshold(self, generator):
        generator.activity_repo.get_frequently_queried_symbols = AsyncMock(return_value=[
            {"symbol": "TSLA", "query_count": 2},  # Below threshold of 3
        ])
        generator.watchlist_repo.get = AsyncMock(return_value=[])
        generator.insight_repo.create = AsyncMock()

        count = await generator._suggest_watchlist_additions(12345, ["AAPL"])
        assert count == 0


class TestCheckStaleActionItems(TestProactiveInsightGenerator):
    async def test_creates_reminder_for_old_item(self, generator):
        old_time = datetime.utcnow() - timedelta(days=5)
        generator.notes_repo.get_active_action_items = AsyncMock(return_value=[
            {"id": 1, "content": "Review AAPL position", "symbols": ["AAPL"], "created_at": old_time},
        ])
        generator.insight_repo.create = AsyncMock(return_value=1)

        count = await generator._check_stale_action_items(12345)
        assert count == 1
        call_kwargs = generator.insight_repo.create.call_args[1]
        assert call_kwargs["insight_type"] == "action_reminder"
        assert "5 days" in call_kwargs["title"]

    async def test_no_reminder_for_recent_item(self, generator):
        recent_time = datetime.utcnow() - timedelta(days=1)
        generator.notes_repo.get_active_action_items = AsyncMock(return_value=[
            {"id": 1, "content": "Check something", "symbols": [], "created_at": recent_time},
        ])
        generator.insight_repo.create = AsyncMock()

        count = await generator._check_stale_action_items(12345)
        assert count == 0

    async def test_no_action_items(self, generator):
        generator.notes_repo.get_active_action_items = AsyncMock(return_value=[])
        count = await generator._check_stale_action_items(12345)
        assert count == 0


class TestGenerateAll(TestProactiveInsightGenerator):
    async def test_generates_for_all_users(self, generator):
        generator.portfolio_repo.get_all_users_with_holdings = AsyncMock(return_value=[111, 222])
        generator.portfolio_repo.get_holdings = AsyncMock(return_value=[{"symbol": "AAPL"}])
        generator.notes_repo.get_active_action_items = AsyncMock(return_value=[])
        generator.activity_repo.get_frequently_queried_symbols = AsyncMock(return_value=[])
        generator.watchlist_repo.get = AsyncMock(return_value=[])
        generator.insight_repo.create = AsyncMock(return_value=1)

        # Mock small moves to skip price check
        generator.dm.get_quote = AsyncMock(return_value={"dp": 0.5, "c": 185.0})
        generator.dm.get_earnings = AsyncMock(return_value=[])

        count = await generator.generate_all()
        assert count == 0  # No significant moves/earnings/stale items

    async def test_handles_user_error(self, generator):
        generator.portfolio_repo.get_all_users_with_holdings = AsyncMock(return_value=[111])
        generator.portfolio_repo.get_holdings = AsyncMock(side_effect=Exception("DB error"))

        count = await generator.generate_all()
        assert count == 0  # Error caught, didn't crash

    async def test_no_users(self, generator):
        generator.portfolio_repo.get_all_users_with_holdings = AsyncMock(return_value=[])
        count = await generator.generate_all()
        assert count == 0


class TestDispatchPending(TestProactiveInsightGenerator):
    async def test_dispatches_undelivered(self, generator, mock_dispatcher):
        generator.portfolio_repo.get_all_users_with_holdings = AsyncMock(return_value=[111])
        generator.insight_repo.get_undelivered = AsyncMock(return_value=[
            {"id": 1, "insight_type": "price_movement", "title": "AAPL +5%",
             "content": "Big move", "symbols": ["AAPL"], "created_at": datetime.utcnow()},
        ])
        generator.insight_repo.mark_delivered = AsyncMock()

        sent = await generator.dispatch_pending()
        assert sent == 1
        mock_dispatcher.dispatch.assert_awaited_once()
        generator.insight_repo.mark_delivered.assert_awaited_once_with(1)

    async def test_no_pending_insights(self, generator, mock_dispatcher):
        generator.portfolio_repo.get_all_users_with_holdings = AsyncMock(return_value=[111])
        generator.insight_repo.get_undelivered = AsyncMock(return_value=[])

        sent = await generator.dispatch_pending()
        assert sent == 0
        mock_dispatcher.dispatch.assert_not_awaited()

    async def test_dispatch_failure_does_not_mark_delivered(self, generator, mock_dispatcher):
        generator.portfolio_repo.get_all_users_with_holdings = AsyncMock(return_value=[111])
        generator.insight_repo.get_undelivered = AsyncMock(return_value=[
            {"id": 1, "insight_type": "price_movement", "title": "AAPL +5%",
             "content": "Big move", "symbols": ["AAPL"], "created_at": datetime.utcnow()},
        ])
        mock_dispatcher.dispatch = AsyncMock(return_value=0)  # No one received it
        generator.insight_repo.mark_delivered = AsyncMock()

        sent = await generator.dispatch_pending()
        assert sent == 0
        generator.insight_repo.mark_delivered.assert_not_awaited()
