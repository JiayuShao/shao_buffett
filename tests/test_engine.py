"""Tests for ai/engine.py — AI engine tool execution and context injection."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from ai.engine import AIEngine


# ── Tool Execution Tests ──

class TestExecuteToolFinancial:
    """Test _execute_tool for financial data tools."""

    @pytest.fixture
    def engine(self, mock_data_manager, fake_pool):
        with patch("ai.engine.settings") as mock_settings:
            mock_settings.anthropic_api_key = "test-key"
            with patch("ai.engine.ConversationManager"):
                e = AIEngine(data_manager=mock_data_manager, db_pool=fake_pool)
                return e

    async def test_get_quote(self, engine, mock_data_manager):
        result = await engine._execute_tool("get_quote", {"symbol": "AAPL"})
        mock_data_manager.get_quote.assert_awaited_once_with("AAPL")
        assert result["c"] == 185.50

    async def test_get_company_profile(self, engine, mock_data_manager):
        result = await engine._execute_tool("get_company_profile", {"symbol": "AAPL"})
        mock_data_manager.get_company_profile.assert_awaited_once_with("AAPL")
        assert result["name"] == "Apple Inc."

    async def test_get_fundamentals(self, engine, mock_data_manager):
        result = await engine._execute_tool("get_fundamentals", {"symbol": "AAPL"})
        mock_data_manager.get_fundamentals.assert_awaited_once_with("AAPL")

    async def test_get_analyst_data(self, engine, mock_data_manager):
        result = await engine._execute_tool("get_analyst_data", {"symbol": "AAPL"})
        mock_data_manager.get_analyst_data.assert_awaited_once_with("AAPL")

    async def test_get_earnings(self, engine, mock_data_manager):
        result = await engine._execute_tool("get_earnings", {"symbol": "AAPL"})
        mock_data_manager.get_earnings.assert_awaited_once_with("AAPL")

    async def test_get_news_with_symbol(self, engine, mock_data_manager):
        result = await engine._execute_tool("get_news", {"symbol": "AAPL", "limit": 3})
        mock_data_manager.get_news.assert_awaited_once_with(symbol="AAPL", limit=3)

    async def test_get_news_default_limit(self, engine, mock_data_manager):
        result = await engine._execute_tool("get_news", {})
        mock_data_manager.get_news.assert_awaited_once_with(symbol=None, limit=5)

    async def test_get_macro_data(self, engine, mock_data_manager):
        result = await engine._execute_tool("get_macro_data", {"series_id": "GDP"})
        mock_data_manager.get_macro_data.assert_awaited_once_with(series_id="GDP")

    async def test_get_sector_performance(self, engine, mock_data_manager):
        result = await engine._execute_tool("get_sector_performance", {})
        mock_data_manager.get_sector_performance.assert_awaited_once()

    async def test_get_earnings_transcript(self, engine, mock_data_manager):
        result = await engine._execute_tool("get_earnings_transcript", {"symbol": "AAPL", "year": 2024, "quarter": 4})
        mock_data_manager.get_earnings_transcript.assert_awaited_once_with("AAPL", 2024, 4)

    async def test_get_sec_filings(self, engine, mock_data_manager):
        result = await engine._execute_tool("get_sec_filings", {"symbol": "AAPL", "form_types": ["10-K"]})
        mock_data_manager.get_sec_filings.assert_awaited_once_with("AAPL", form_types=["10-K"])

    async def test_get_research_papers(self, engine, mock_data_manager):
        result = await engine._execute_tool("get_research_papers", {"query": "portfolio optimization"})
        mock_data_manager.get_research_papers.assert_awaited_once_with(query="portfolio optimization", max_results=10)

    async def test_generate_chart_no_send_file(self, engine):
        result = await engine._execute_tool("generate_chart", {"chart_type": "comparison", "symbols": ["AAPL", "MSFT"]})
        assert result["status"] == "charts unavailable in this context"

    async def test_unknown_tool(self, engine):
        result = await engine._execute_tool("nonexistent_tool", {})
        assert "error" in result
        assert "Unknown tool" in result["error"]

    async def test_tool_error_handling(self, engine, mock_data_manager):
        mock_data_manager.get_quote.side_effect = Exception("API down")
        result = await engine._execute_tool("get_quote", {"symbol": "AAPL"})
        assert "error" in result
        assert "failed" in result["error"]


# ── Personal Analyst Tool Tests ──

class TestExecuteToolNotes:
    """Test _execute_tool for note-taking tools."""

    @pytest.fixture
    def engine(self, mock_data_manager, fake_pool):
        with patch("ai.engine.settings") as mock_settings:
            mock_settings.anthropic_api_key = "test-key"
            with patch("ai.engine.ConversationManager"):
                e = AIEngine(data_manager=mock_data_manager, db_pool=fake_pool)
                e.notes_repo = MagicMock()
                e.notes_repo.add = AsyncMock(return_value=42)
                e.notes_repo.get_recent = AsyncMock(return_value=[
                    {"id": 1, "note_type": "concern", "content": "Worried about PE", "symbols": ["NVDA"]},
                ])
                e.notes_repo.get_by_type = AsyncMock(return_value=[])
                e.notes_repo.get_for_symbols = AsyncMock(return_value=[])
                e.notes_repo.search = AsyncMock(return_value=[])
                e.notes_repo.resolve_action_item = AsyncMock(return_value=True)
                return e

    async def test_save_note(self, engine):
        result = await engine._execute_tool("save_note", {
            "note_type": "concern",
            "content": "Worried about NVDA PE ratio",
            "symbols": ["NVDA"],
        }, user_id=12345)
        assert result["status"] == "saved"
        assert result["note_id"] == 42
        engine.notes_repo.add.assert_awaited_once()

    async def test_save_note_no_user(self, engine):
        result = await engine._execute_tool("save_note", {
            "note_type": "insight", "content": "test",
        }, user_id=None)
        assert "error" in result

    async def test_get_user_notes_default(self, engine):
        result = await engine._execute_tool("get_user_notes", {}, user_id=12345)
        engine.notes_repo.get_recent.assert_awaited_once_with(12345)

    async def test_get_user_notes_by_type(self, engine):
        await engine._execute_tool("get_user_notes", {"note_type": "concern"}, user_id=12345)
        engine.notes_repo.get_by_type.assert_awaited_once_with(12345, "concern")

    async def test_get_user_notes_by_symbols(self, engine):
        await engine._execute_tool("get_user_notes", {"symbols": ["AAPL"]}, user_id=12345)
        engine.notes_repo.get_for_symbols.assert_awaited_once_with(12345, ["AAPL"])

    async def test_get_user_notes_by_query(self, engine):
        await engine._execute_tool("get_user_notes", {"query": "PE ratio"}, user_id=12345)
        engine.notes_repo.search.assert_awaited_once_with(12345, "PE ratio")

    async def test_get_user_notes_no_user(self, engine):
        result = await engine._execute_tool("get_user_notes", {}, user_id=None)
        assert "error" in result

    async def test_resolve_action_item(self, engine):
        result = await engine._execute_tool("resolve_action_item", {"note_id": 7}, user_id=12345)
        assert result["resolved"] is True
        engine.notes_repo.resolve_action_item.assert_awaited_once_with(7, 12345)

    async def test_resolve_action_item_no_user(self, engine):
        result = await engine._execute_tool("resolve_action_item", {"note_id": 7}, user_id=None)
        assert "error" in result


class TestExecuteToolPortfolio:
    """Test _execute_tool for portfolio tools."""

    @pytest.fixture
    def engine(self, mock_data_manager, fake_pool):
        with patch("ai.engine.settings") as mock_settings:
            mock_settings.anthropic_api_key = "test-key"
            with patch("ai.engine.ConversationManager"):
                e = AIEngine(data_manager=mock_data_manager, db_pool=fake_pool)
                e.notes_repo = MagicMock()
                e.notes_repo.get_recent = AsyncMock(return_value=[])
                e.notes_repo.get_active_action_items = AsyncMock(return_value=[])
                return e

    @patch("storage.repositories.portfolio_repo.PortfolioRepository")
    async def test_get_portfolio(self, MockRepo, engine):
        mock_repo = MockRepo.return_value
        mock_repo.get_holdings = AsyncMock(return_value=[{"symbol": "AAPL", "shares": 100}])
        result = await engine._execute_tool("get_portfolio", {}, user_id=12345)
        assert result == [{"symbol": "AAPL", "shares": 100}]

    async def test_get_portfolio_no_user(self, engine):
        result = await engine._execute_tool("get_portfolio", {}, user_id=None)
        assert "error" in result

    @patch("storage.repositories.portfolio_repo.PortfolioRepository")
    async def test_update_portfolio_add(self, MockRepo, engine):
        mock_repo = MockRepo.return_value
        mock_repo.upsert = AsyncMock()
        result = await engine._execute_tool("update_portfolio", {
            "action": "add", "symbol": "AAPL", "shares": 100, "cost_basis": 185.0,
        }, user_id=12345)
        assert result["status"] == "updated"
        assert result["symbol"] == "AAPL"
        mock_repo.upsert.assert_awaited_once()

    @patch("storage.repositories.portfolio_repo.PortfolioRepository")
    async def test_update_portfolio_remove(self, MockRepo, engine):
        mock_repo = MockRepo.return_value
        mock_repo.remove = AsyncMock(return_value=True)
        result = await engine._execute_tool("update_portfolio", {
            "action": "remove", "symbol": "TSLA",
        }, user_id=12345)
        assert result["status"] == "removed"

    @patch("storage.repositories.portfolio_repo.PortfolioRepository")
    async def test_update_portfolio_remove_not_found(self, MockRepo, engine):
        mock_repo = MockRepo.return_value
        mock_repo.remove = AsyncMock(return_value=False)
        result = await engine._execute_tool("update_portfolio", {
            "action": "remove", "symbol": "XYZ",
        }, user_id=12345)
        assert result["status"] == "not_found"

    async def test_update_portfolio_no_user(self, engine):
        result = await engine._execute_tool("update_portfolio", {
            "action": "add", "symbol": "AAPL", "shares": 10,
        }, user_id=None)
        assert "error" in result

    @patch("storage.repositories.portfolio_repo.FinancialProfileRepository")
    async def test_get_financial_profile(self, MockRepo, engine):
        mock_repo = MockRepo.return_value
        mock_repo.get = AsyncMock(return_value={"annual_income": 150000, "tax_bracket": "24%"})
        result = await engine._execute_tool("get_financial_profile", {}, user_id=12345)
        assert result["annual_income"] == 150000

    @patch("storage.repositories.portfolio_repo.FinancialProfileRepository")
    async def test_get_financial_profile_empty(self, MockRepo, engine):
        mock_repo = MockRepo.return_value
        mock_repo.get = AsyncMock(return_value=None)
        result = await engine._execute_tool("get_financial_profile", {}, user_id=12345)
        assert result["status"] == "no_profile"

    @patch("storage.repositories.portfolio_repo.FinancialProfileRepository")
    async def test_update_financial_profile(self, MockRepo, engine):
        mock_repo = MockRepo.return_value
        mock_repo.upsert = AsyncMock()
        result = await engine._execute_tool("update_financial_profile", {
            "annual_income": 200000, "investment_horizon": "10+ years",
        }, user_id=12345)
        assert result["status"] == "updated"
        mock_repo.upsert.assert_awaited_once()


# ── Context Injection Tests ──

class TestInjectUserContext:
    @pytest.fixture
    def engine(self, mock_data_manager, fake_pool):
        with patch("ai.engine.settings") as mock_settings:
            mock_settings.anthropic_api_key = "test-key"
            with patch("ai.engine.ConversationManager"):
                e = AIEngine(data_manager=mock_data_manager, db_pool=fake_pool)
                e.notes_repo = MagicMock()
                return e

    async def test_injects_notes(self, engine):
        engine.notes_repo.get_recent = AsyncMock(return_value=[
            {"note_type": "concern", "content": "Worried about NVDA PE", "symbols": ["NVDA"]},
            {"note_type": "decision", "content": "Decided to hold AAPL", "symbols": ["AAPL"]},
        ])
        engine.notes_repo.get_active_action_items = AsyncMock(return_value=[])

        result = await engine._inject_user_context(12345, "Base prompt")
        assert "Your Notes About This User" in result
        assert "Worried about NVDA PE" in result
        assert "[concern]" in result
        assert "[NVDA]" in result

    async def test_injects_action_items(self, engine):
        engine.notes_repo.get_recent = AsyncMock(return_value=[])
        engine.notes_repo.get_active_action_items = AsyncMock(return_value=[
            {"id": 5, "content": "Review AAPL position", "symbols": ["AAPL"]},
        ])

        result = await engine._inject_user_context(12345, "Base prompt")
        assert "Open Action Items" in result
        assert "#5" in result
        assert "Review AAPL position" in result

    async def test_no_notes_no_change(self, engine):
        engine.notes_repo.get_recent = AsyncMock(return_value=[])
        engine.notes_repo.get_active_action_items = AsyncMock(return_value=[])

        result = await engine._inject_user_context(12345, "Base prompt")
        assert result == "Base prompt"

    async def test_error_returns_original_prompt(self, engine):
        engine.notes_repo.get_recent = AsyncMock(side_effect=Exception("DB error"))

        result = await engine._inject_user_context(12345, "Base prompt")
        assert result == "Base prompt"


# ── Activity Logging Tests ──

class TestLogActivity:
    @pytest.fixture
    def engine(self, mock_data_manager, fake_pool):
        with patch("ai.engine.settings") as mock_settings:
            mock_settings.anthropic_api_key = "test-key"
            with patch("ai.engine.ConversationManager"):
                e = AIEngine(data_manager=mock_data_manager, db_pool=fake_pool)
                return e

    @patch("storage.repositories.activity_repo.ActivityRepository")
    async def test_classifies_price_check(self, MockRepo, engine):
        mock_repo = MockRepo.return_value
        mock_repo.log_activity = AsyncMock()
        await engine._log_activity(12345, "What's the price of AAPL?")
        mock_repo.log_activity.assert_awaited_once()
        call_args = mock_repo.log_activity.call_args
        assert call_args[0][1] == "price_check"

    @patch("storage.repositories.activity_repo.ActivityRepository")
    async def test_classifies_analysis(self, MockRepo, engine):
        mock_repo = MockRepo.return_value
        mock_repo.log_activity = AsyncMock()
        await engine._log_activity(12345, "Give me an analysis of NVDA")
        call_args = mock_repo.log_activity.call_args
        assert call_args[0][1] == "analysis"

    @patch("storage.repositories.activity_repo.ActivityRepository")
    async def test_classifies_news(self, MockRepo, engine):
        mock_repo = MockRepo.return_value
        mock_repo.log_activity = AsyncMock()
        await engine._log_activity(12345, "Show me latest news")
        call_args = mock_repo.log_activity.call_args
        assert call_args[0][1] == "news"

    @patch("storage.repositories.activity_repo.ActivityRepository")
    async def test_classifies_earnings(self, MockRepo, engine):
        mock_repo = MockRepo.return_value
        mock_repo.log_activity = AsyncMock()
        await engine._log_activity(12345, "What were AAPL earnings?")
        call_args = mock_repo.log_activity.call_args
        assert call_args[0][1] == "earnings"

    @patch("storage.repositories.activity_repo.ActivityRepository")
    async def test_classifies_portfolio_decision(self, MockRepo, engine):
        mock_repo = MockRepo.return_value
        mock_repo.log_activity = AsyncMock()
        await engine._log_activity(12345, "Should I buy more TSLA?")
        call_args = mock_repo.log_activity.call_args
        assert call_args[0][1] == "portfolio_decision"

    @patch("storage.repositories.activity_repo.ActivityRepository")
    async def test_classifies_macro(self, MockRepo, engine):
        mock_repo = MockRepo.return_value
        mock_repo.log_activity = AsyncMock()
        await engine._log_activity(12345, "What's the latest CPI data?")
        call_args = mock_repo.log_activity.call_args
        assert call_args[0][1] == "macro"

    @patch("storage.repositories.activity_repo.ActivityRepository")
    async def test_classifies_general(self, MockRepo, engine):
        mock_repo = MockRepo.return_value
        mock_repo.log_activity = AsyncMock()
        await engine._log_activity(12345, "Tell me about Apple's services segment")
        call_args = mock_repo.log_activity.call_args
        assert call_args[0][1] == "general"

    @patch("storage.repositories.activity_repo.ActivityRepository")
    async def test_extracts_tickers(self, MockRepo, engine):
        mock_repo = MockRepo.return_value
        mock_repo.log_activity = AsyncMock()
        await engine._log_activity(12345, "Compare AAPL vs MSFT and GOOGL")
        call_args = mock_repo.log_activity.call_args
        symbols = call_args[0][2]
        assert "AAPL" in symbols
        assert "MSFT" in symbols
        assert "GOOGL" in symbols

    @patch("storage.repositories.activity_repo.ActivityRepository")
    async def test_filters_noise_words(self, MockRepo, engine):
        mock_repo = MockRepo.return_value
        mock_repo.log_activity = AsyncMock()
        await engine._log_activity(12345, "I AM looking AT AAPL")
        call_args = mock_repo.log_activity.call_args
        symbols = call_args[0][2]
        assert "I" not in symbols
        assert "AM" not in symbols
        assert "AT" not in symbols
        assert "AAPL" in symbols

    @patch("storage.repositories.activity_repo.ActivityRepository")
    async def test_error_does_not_raise(self, MockRepo, engine):
        MockRepo.side_effect = Exception("import error")
        # Should not raise
        await engine._log_activity(12345, "test query")
