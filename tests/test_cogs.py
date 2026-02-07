"""Tests for all Discord slash command cogs.

We call the underlying callback directly (cog.command.callback(cog, ctx, ...))
to bypass py-cord's slash command dispatch, which requires a real Interaction.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch


# ── Helpers ──


def make_ctx(user_id=12345, channel_id=99999):
    """Create a mock ApplicationContext."""
    ctx = AsyncMock()
    ctx.author = MagicMock()
    ctx.author.id = user_id
    ctx.author.display_name = "TestUser"
    ctx.channel_id = channel_id
    ctx.respond = AsyncMock()
    ctx.followup = MagicMock()
    ctx.followup.send = AsyncMock()
    ctx.defer = AsyncMock()
    return ctx


def make_bot(data_manager=None, ai_engine=None, db_pool=None):
    """Create a mock bot with data_manager, ai_engine, and db_pool."""
    bot = MagicMock()
    bot.data_manager = data_manager or MagicMock()
    bot.ai_engine = ai_engine
    bot.db_pool = db_pool or MagicMock()
    bot.guilds = [MagicMock()]
    bot.latency = 0.05
    return bot


# ── Watchlist Cog ──


class TestWatchlistCog:
    @pytest.fixture
    def cog(self):
        from bot.cogs.watchlist import WatchlistCog
        bot = make_bot()
        return WatchlistCog(bot)

    @pytest.mark.asyncio
    @patch("bot.cogs.watchlist.WatchlistRepository")
    async def test_add_valid_ticker(self, MockRepo, cog):
        repo = MockRepo.return_value
        repo.add = AsyncMock(return_value=True)
        ctx = make_ctx()

        await cog.add.callback(cog, ctx, "AAPL")

        repo.add.assert_called_once_with(ctx.author.id, "AAPL")
        ctx.respond.assert_called_once()
        embed = ctx.respond.call_args[1]["embed"]
        assert "AAPL" in embed.description

    @pytest.mark.asyncio
    async def test_add_invalid_ticker(self, cog):
        ctx = make_ctx()
        await cog.add.callback(cog, ctx, "!!invalid!!")

        ctx.respond.assert_called_once()
        embed = ctx.respond.call_args[1]["embed"]
        assert "Error" in embed.title

    @pytest.mark.asyncio
    @patch("bot.cogs.watchlist.WatchlistRepository")
    async def test_add_already_exists(self, MockRepo, cog):
        repo = MockRepo.return_value
        repo.add = AsyncMock(return_value=False)
        ctx = make_ctx()

        await cog.add.callback(cog, ctx, "AAPL")

        ctx.respond.assert_called_once()
        assert ctx.respond.call_args[1].get("ephemeral") is True

    @pytest.mark.asyncio
    @patch("bot.cogs.watchlist.WatchlistRepository")
    async def test_remove_success(self, MockRepo, cog):
        repo = MockRepo.return_value
        repo.remove = AsyncMock(return_value=True)
        ctx = make_ctx()

        await cog.remove.callback(cog, ctx, "AAPL")

        repo.remove.assert_called_once_with(ctx.author.id, "AAPL")
        embed = ctx.respond.call_args[1]["embed"]
        assert "AAPL" in embed.description

    @pytest.mark.asyncio
    @patch("bot.cogs.watchlist.WatchlistRepository")
    async def test_remove_not_found(self, MockRepo, cog):
        repo = MockRepo.return_value
        repo.remove = AsyncMock(return_value=False)
        ctx = make_ctx()

        await cog.remove.callback(cog, ctx, "AAPL")

        assert ctx.respond.call_args[1].get("ephemeral") is True

    @pytest.mark.asyncio
    @patch("bot.cogs.watchlist.WatchlistRepository")
    async def test_show_empty(self, MockRepo, cog):
        repo = MockRepo.return_value
        repo.get = AsyncMock(return_value=[])
        ctx = make_ctx()

        await cog.show.callback(cog, ctx)

        ctx.defer.assert_called_once()
        embed = ctx.respond.call_args[1]["embed"]
        assert "empty" in embed.description.lower()

    @pytest.mark.asyncio
    @patch("bot.cogs.watchlist.WatchlistRepository")
    async def test_show_with_stocks(self, MockRepo, cog):
        repo = MockRepo.return_value
        repo.get = AsyncMock(return_value=["AAPL", "MSFT"])
        cog.bot.data_manager.get_quote = AsyncMock(return_value={
            "price": 185.50, "change_pct": 1.25,
        })
        ctx = make_ctx()

        await cog.show.callback(cog, ctx)

        embed = ctx.respond.call_args[1]["embed"]
        assert "2 stocks" in embed.title


# ── Alerts Cog ──


class TestAlertsCog:
    @pytest.fixture
    def cog(self):
        from bot.cogs.alerts import AlertsCog
        bot = make_bot()
        return AlertsCog(bot)

    @pytest.mark.asyncio
    @patch("bot.cogs.alerts.AlertRepository")
    async def test_set_above_alert(self, MockRepo, cog):
        repo = MockRepo.return_value
        repo.create = AsyncMock(return_value=42)
        ctx = make_ctx()

        await cog.set.callback(cog, ctx, "AAPL", "above", 200.0)

        repo.create.assert_called_once_with(ctx.author.id, "AAPL", "above", 200.0)
        embed = ctx.respond.call_args[1]["embed"]
        assert "42" in embed.description
        assert "AAPL" in embed.description

    @pytest.mark.asyncio
    @patch("bot.cogs.alerts.AlertRepository")
    async def test_set_change_pct_alert(self, MockRepo, cog):
        repo = MockRepo.return_value
        repo.create = AsyncMock(return_value=7)
        ctx = make_ctx()

        await cog.set.callback(cog, ctx, "TSLA", "change_pct", 5.0)

        embed = ctx.respond.call_args[1]["embed"]
        assert "5.0%" in embed.description

    @pytest.mark.asyncio
    @patch("bot.cogs.alerts.AlertRepository")
    async def test_set_alert_limit_reached(self, MockRepo, cog):
        repo = MockRepo.return_value
        repo.create = AsyncMock(return_value=None)
        ctx = make_ctx()

        await cog.set.callback(cog, ctx, "AAPL", "below", 150.0)

        assert ctx.respond.call_args[1].get("ephemeral") is True

    @pytest.mark.asyncio
    async def test_set_invalid_ticker(self, cog):
        ctx = make_ctx()
        await cog.set.callback(cog, ctx, "!!!bad", "above", 100.0)

        assert ctx.respond.call_args[1].get("ephemeral") is True
        embed = ctx.respond.call_args[1]["embed"]
        assert "Error" in embed.title

    @pytest.mark.asyncio
    @patch("bot.cogs.alerts.AlertRepository")
    async def test_remove_alert(self, MockRepo, cog):
        repo = MockRepo.return_value
        repo.remove = AsyncMock(return_value=True)
        ctx = make_ctx()

        await cog.remove.callback(cog, ctx, 42)

        repo.remove.assert_called_once_with(42, ctx.author.id)
        embed = ctx.respond.call_args[1]["embed"]
        assert "42" in embed.description

    @pytest.mark.asyncio
    @patch("bot.cogs.alerts.AlertRepository")
    async def test_remove_alert_not_found(self, MockRepo, cog):
        repo = MockRepo.return_value
        repo.remove = AsyncMock(return_value=False)
        ctx = make_ctx()

        await cog.remove.callback(cog, ctx, 999)

        assert ctx.respond.call_args[1].get("ephemeral") is True

    @pytest.mark.asyncio
    @patch("bot.cogs.alerts.AlertRepository")
    async def test_list_empty(self, MockRepo, cog):
        repo = MockRepo.return_value
        repo.get_active = AsyncMock(return_value=[])
        ctx = make_ctx()

        await cog.list_alerts.callback(cog, ctx)

        embed = ctx.respond.call_args[1]["embed"]
        assert "No active alerts" in embed.description

    @pytest.mark.asyncio
    @patch("bot.cogs.alerts.AlertRepository")
    async def test_list_with_alerts(self, MockRepo, cog):
        repo = MockRepo.return_value
        repo.get_active = AsyncMock(return_value=[
            {"id": 1, "symbol": "AAPL", "condition": "above", "threshold": "200"},
            {"id": 2, "symbol": "TSLA", "condition": "change_pct", "threshold": "5.0"},
        ])
        ctx = make_ctx()

        await cog.list_alerts.callback(cog, ctx)

        embed = ctx.respond.call_args[1]["embed"]
        assert "2 active" in embed.title
        assert "AAPL" in embed.description
        assert "TSLA" in embed.description


# ── Market Cog ──


class TestMarketCog:
    @pytest.fixture
    def cog(self):
        from bot.cogs.market import MarketCog
        bot = make_bot()
        bot.data_manager.get_quote = AsyncMock(return_value={
            "price": 185.50, "change_pct": 1.25,
        })
        bot.data_manager.get_sector_performance = AsyncMock(return_value=[
            {"sector": "Technology", "changesPercentage": "+2.5%"},
            {"sector": "Healthcare", "changesPercentage": "-0.3%"},
        ])
        bot.data_manager.get_macro_data = AsyncMock(return_value={
            "GDP": {"value": 27.36, "date": "2024-Q4"},
            "FEDFUNDS": {"value": 5.33, "date": "2024-12"},
        })
        return MarketCog(bot)

    @pytest.mark.asyncio
    async def test_overview(self, cog):
        ctx = make_ctx()
        await cog.overview.callback(cog, ctx)

        ctx.defer.assert_called_once()
        embed = ctx.respond.call_args[1]["embed"]
        assert "Market Overview" in embed.title

    @pytest.mark.asyncio
    async def test_sector(self, cog):
        ctx = make_ctx()
        await cog.sector.callback(cog, ctx)

        ctx.defer.assert_called_once()
        embed = ctx.respond.call_args[1]["embed"]
        assert "Sector" in embed.title
        assert "Technology" in embed.description

    @pytest.mark.asyncio
    async def test_sector_empty(self, cog):
        cog.bot.data_manager.get_sector_performance = AsyncMock(return_value=[])
        ctx = make_ctx()

        await cog.sector.callback(cog, ctx)

        embed = ctx.respond.call_args[1]["embed"]
        assert "No data" in embed.description

    @pytest.mark.asyncio
    async def test_sector_exception(self, cog):
        cog.bot.data_manager.get_sector_performance = AsyncMock(side_effect=Exception("API down"))
        ctx = make_ctx()

        await cog.sector.callback(cog, ctx)

        embed = ctx.respond.call_args[1]["embed"]
        assert "Error" in embed.title

    @pytest.mark.asyncio
    async def test_macro(self, cog):
        ctx = make_ctx()
        await cog.macro.callback(cog, ctx)

        ctx.defer.assert_called_once()
        embed = ctx.respond.call_args[1]["embed"]
        assert "Macro" in embed.title

    @pytest.mark.asyncio
    async def test_macro_exception(self, cog):
        cog.bot.data_manager.get_macro_data = AsyncMock(side_effect=Exception("FRED down"))
        ctx = make_ctx()

        await cog.macro.callback(cog, ctx)

        embed = ctx.respond.call_args[1]["embed"]
        assert "Error" in embed.title


# ── Portfolio Cog ──


class TestPortfolioCog:
    @pytest.fixture
    def cog(self):
        from bot.cogs.portfolio import PortfolioCog
        bot = make_bot()
        return PortfolioCog(bot)

    @pytest.mark.asyncio
    @patch("bot.cogs.portfolio.PortfolioRepository")
    async def test_show_empty(self, MockRepo, cog):
        repo = MockRepo.return_value
        repo.get_holdings = AsyncMock(return_value=[])
        ctx = make_ctx()

        await cog.show.callback(cog, ctx)

        embed = ctx.respond.call_args[1]["embed"]
        assert "No holdings" in embed.description

    @pytest.mark.asyncio
    @patch("bot.cogs.portfolio.PortfolioRepository")
    async def test_show_with_holdings(self, MockRepo, cog):
        repo = MockRepo.return_value
        repo.get_holdings = AsyncMock(return_value=[
            {"symbol": "AAPL", "shares": 100, "cost_basis": 150.0, "account_type": "taxable", "notes": None},
            {"symbol": "MSFT", "shares": 50, "cost_basis": 350.0, "account_type": "roth_ira", "notes": "long-term hold"},
        ])
        ctx = make_ctx()

        await cog.show.callback(cog, ctx)

        embed = ctx.respond.call_args[1]["embed"]
        assert "2 positions" in embed.title
        assert "AAPL" in embed.description
        assert "MSFT" in embed.description
        assert "roth_ira" in embed.description

    @pytest.mark.asyncio
    @patch("bot.cogs.portfolio.PortfolioRepository")
    async def test_add_position(self, MockRepo, cog):
        repo = MockRepo.return_value
        repo.upsert = AsyncMock()
        ctx = make_ctx()

        await cog.add.callback(cog, ctx, "AAPL", 100, 185.0, "taxable")

        repo.upsert.assert_called_once_with(
            discord_id=ctx.author.id,
            symbol="AAPL",
            shares=100,
            cost_basis=185.0,
            account_type="taxable",
        )
        embed = ctx.respond.call_args[1]["embed"]
        assert "AAPL" in embed.description

    @pytest.mark.asyncio
    async def test_add_invalid_ticker(self, cog):
        ctx = make_ctx()
        await cog.add.callback(cog, ctx, "!!!bad", 100, None, "taxable")

        assert ctx.respond.call_args[1].get("ephemeral") is True

    @pytest.mark.asyncio
    @patch("bot.cogs.portfolio.PortfolioRepository")
    async def test_remove_position(self, MockRepo, cog):
        repo = MockRepo.return_value
        repo.remove = AsyncMock(return_value=True)
        ctx = make_ctx()

        await cog.remove.callback(cog, ctx, "AAPL", "taxable")

        repo.remove.assert_called_once_with(ctx.author.id, "AAPL", "taxable")

    @pytest.mark.asyncio
    @patch("bot.cogs.portfolio.PortfolioRepository")
    async def test_remove_not_found(self, MockRepo, cog):
        repo = MockRepo.return_value
        repo.remove = AsyncMock(return_value=False)
        ctx = make_ctx()

        await cog.remove.callback(cog, ctx, "AAPL", "taxable")

        embed = ctx.respond.call_args[1]["embed"]
        assert "Error" in embed.title

    @pytest.mark.asyncio
    @patch("bot.cogs.portfolio.FinancialProfileRepository")
    async def test_goals_view_empty(self, MockProfileRepo, cog):
        repo = MockProfileRepo.return_value
        repo.get = AsyncMock(return_value=None)
        ctx = make_ctx()

        await cog.goals.callback(cog, ctx, None)

        embed = ctx.respond.call_args[1]["embed"]
        assert "No goals" in embed.description

    @pytest.mark.asyncio
    @patch("bot.cogs.portfolio.FinancialProfileRepository")
    async def test_goals_view_with_goals(self, MockProfileRepo, cog):
        repo = MockProfileRepo.return_value
        repo.get = AsyncMock(return_value={"goals": ["Retire by 55", "Pay off house"]})
        ctx = make_ctx()

        await cog.goals.callback(cog, ctx, None)

        embed = ctx.respond.call_args[1]["embed"]
        assert "Retire by 55" in embed.description

    @pytest.mark.asyncio
    @patch("bot.cogs.portfolio.FinancialProfileRepository")
    async def test_goals_add(self, MockProfileRepo, cog):
        repo = MockProfileRepo.return_value
        repo.get = AsyncMock(return_value={"goals": ["Retire by 55"]})
        repo.upsert = AsyncMock()
        ctx = make_ctx()

        await cog.goals.callback(cog, ctx, "Save 100k emergency fund")

        repo.upsert.assert_called_once()
        call_kwargs = repo.upsert.call_args[1]
        assert "Save 100k emergency fund" in call_kwargs["goals"]
        assert "Retire by 55" in call_kwargs["goals"]


# ── Notes Cog ──


class TestNotesCog:
    @pytest.fixture
    def cog(self):
        from bot.cogs.notes import NotesCog
        bot = make_bot()
        return NotesCog(bot)

    @pytest.mark.asyncio
    @patch("bot.cogs.notes.NotesRepository")
    async def test_show_empty(self, MockRepo, cog):
        repo = MockRepo.return_value
        repo.get_recent = AsyncMock(return_value=[])
        ctx = make_ctx()

        await cog.show.callback(cog, ctx, "all", 10)

        embed = ctx.respond.call_args[1]["embed"]
        assert "No notes" in embed.description

    @pytest.mark.asyncio
    @patch("bot.cogs.notes.NotesRepository")
    async def test_show_all_notes(self, MockRepo, cog):
        repo = MockRepo.return_value
        repo.get_recent = AsyncMock(return_value=[
            {
                "id": 1, "note_type": "insight", "content": "NVDA has strong AI moat",
                "symbols": ["NVDA"], "is_resolved": False,
                "created_at": datetime(2025, 1, 15),
            },
            {
                "id": 2, "note_type": "concern", "content": "Worried about 60x PE",
                "symbols": ["NVDA"], "is_resolved": False,
                "created_at": datetime(2025, 1, 16),
            },
        ])
        ctx = make_ctx()

        await cog.show.callback(cog, ctx, "all", 10)

        embed = ctx.respond.call_args[1]["embed"]
        assert "2" in embed.title
        assert "NVDA" in embed.description

    @pytest.mark.asyncio
    @patch("bot.cogs.notes.NotesRepository")
    async def test_show_filtered_by_type(self, MockRepo, cog):
        repo = MockRepo.return_value
        repo.get_by_type = AsyncMock(return_value=[
            {
                "id": 3, "note_type": "concern", "content": "Market overvalued",
                "symbols": [], "is_resolved": False,
                "created_at": datetime(2025, 1, 20),
            },
        ])
        ctx = make_ctx()

        await cog.show.callback(cog, ctx, "concern", 10)

        repo.get_by_type.assert_called_once_with(ctx.author.id, "concern", limit=10)

    @pytest.mark.asyncio
    @patch("bot.cogs.notes.NotesRepository")
    async def test_actions_empty(self, MockRepo, cog):
        repo = MockRepo.return_value
        repo.get_active_action_items = AsyncMock(return_value=[])
        ctx = make_ctx()

        await cog.actions.callback(cog, ctx)

        embed = ctx.respond.call_args[1]["embed"]
        assert "No open action items" in embed.description

    @pytest.mark.asyncio
    @patch("bot.cogs.notes.NotesRepository")
    async def test_actions_with_items(self, MockRepo, cog):
        repo = MockRepo.return_value
        repo.get_active_action_items = AsyncMock(return_value=[
            {
                "id": 5, "content": "Research TSLA valuation",
                "symbols": ["TSLA"],
                "created_at": datetime(2025, 1, 20),
            },
        ])
        ctx = make_ctx()

        await cog.actions.callback(cog, ctx)

        embed = ctx.respond.call_args[1]["embed"]
        assert "1" in embed.title
        assert "TSLA" in embed.description

    @pytest.mark.asyncio
    @patch("bot.cogs.notes.NotesRepository")
    async def test_resolve_success(self, MockRepo, cog):
        repo = MockRepo.return_value
        repo.resolve_action_item = AsyncMock(return_value=True)
        ctx = make_ctx()

        await cog.resolve.callback(cog, ctx, 5)

        repo.resolve_action_item.assert_called_once_with(5, ctx.author.id)
        embed = ctx.respond.call_args[1]["embed"]
        assert "Resolved" in embed.title

    @pytest.mark.asyncio
    @patch("bot.cogs.notes.NotesRepository")
    async def test_resolve_not_found(self, MockRepo, cog):
        repo = MockRepo.return_value
        repo.resolve_action_item = AsyncMock(return_value=False)
        ctx = make_ctx()

        await cog.resolve.callback(cog, ctx, 999)

        embed = ctx.respond.call_args[1]["embed"]
        assert "Error" in embed.title

    @pytest.mark.asyncio
    @patch("bot.cogs.notes.NotesRepository")
    async def test_delete_success(self, MockRepo, cog):
        repo = MockRepo.return_value
        repo.delete = AsyncMock(return_value=True)
        ctx = make_ctx()

        await cog.delete.callback(cog, ctx, 3)

        repo.delete.assert_called_once_with(3, ctx.author.id)
        embed = ctx.respond.call_args[1]["embed"]
        assert "Deleted" in embed.title

    @pytest.mark.asyncio
    @patch("bot.cogs.notes.NotesRepository")
    async def test_delete_not_found(self, MockRepo, cog):
        repo = MockRepo.return_value
        repo.delete = AsyncMock(return_value=False)
        ctx = make_ctx()

        await cog.delete.callback(cog, ctx, 999)

        embed = ctx.respond.call_args[1]["embed"]
        assert "Error" in embed.title


# ── Research Cog ──


class TestResearchCog:
    @pytest.fixture
    def cog(self):
        from bot.cogs.research import ResearchCog
        bot = make_bot()
        bot.ai_engine = MagicMock()
        bot.ai_engine.chat = AsyncMock(return_value="**AAPL Analysis**: Strong buy.")
        bot.ai_engine.analyze = AsyncMock(return_value="Deep analysis result.")
        bot.data_manager.get_sec_filings = AsyncMock(return_value=[
            {"form_type": "10-K", "file_date": "2024-11-01", "entity_name": "Apple Inc."},
        ])
        bot.data_manager.get_research_papers = AsyncMock(return_value=[
            {"title": "Deep Learning for Portfolio", "authors": ["Smith", "Jones"], "pdf_url": "https://arxiv.org/pdf/1234"},
        ])
        return ResearchCog(bot)

    @pytest.mark.asyncio
    async def test_quick_valid(self, cog):
        ctx = make_ctx()
        await cog.quick.callback(cog, ctx, "AAPL")

        ctx.defer.assert_called_once()
        cog.bot.ai_engine.chat.assert_called_once()
        ctx.respond.assert_called_once()
        assert "AAPL" in ctx.respond.call_args[0][0]

    @pytest.mark.asyncio
    async def test_quick_invalid_ticker(self, cog):
        ctx = make_ctx()
        await cog.quick.callback(cog, ctx, "!!bad!!")

        assert ctx.respond.call_args[1].get("ephemeral") is True

    @pytest.mark.asyncio
    @patch("ai.router.get_opus_usage", return_value=(0, 5))
    async def test_deep_research(self, mock_usage, cog):
        ctx = make_ctx()
        await cog.deep.callback(cog, ctx, "AAPL")

        ctx.defer.assert_called_once()
        # First respond is the "Running analysis" embed
        ctx.respond.assert_called_once()
        # Then followup with the result
        cog.bot.ai_engine.chat.assert_called_once()

    @pytest.mark.asyncio
    @patch("ai.router.get_opus_usage", return_value=(5, 5))
    async def test_deep_budget_exhausted(self, mock_usage, cog):
        ctx = make_ctx()
        await cog.deep.callback(cog, ctx, "AAPL")

        embed = ctx.respond.call_args[1]["embed"]
        assert "exhausted" in embed.description.lower()
        assert ctx.respond.call_args[1].get("ephemeral") is True

    @pytest.mark.asyncio
    async def test_compare(self, cog):
        ctx = make_ctx()
        await cog.compare.callback(cog, ctx, "AAPL,MSFT,GOOGL")

        ctx.defer.assert_called_once()
        cog.bot.ai_engine.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_compare_too_few(self, cog):
        ctx = make_ctx()
        await cog.compare.callback(cog, ctx, "AAPL")

        assert ctx.respond.call_args[1].get("ephemeral") is True

    @pytest.mark.asyncio
    async def test_transcript(self, cog):
        ctx = make_ctx()
        await cog.transcript.callback(cog, ctx, "AAPL", 2024, 4)

        ctx.defer.assert_called_once()
        cog.bot.ai_engine.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_filing(self, cog):
        ctx = make_ctx()
        await cog.filing.callback(cog, ctx, "AAPL", "10-K")

        ctx.defer.assert_called_once()
        embed = ctx.respond.call_args[1]["embed"]
        assert "10-K" in embed.description

    @pytest.mark.asyncio
    async def test_filing_no_results(self, cog):
        cog.bot.data_manager.get_sec_filings = AsyncMock(return_value=[])
        ctx = make_ctx()

        await cog.filing.callback(cog, ctx, "AAPL", "All")

        embed = ctx.respond.call_args[1]["embed"]
        assert "No recent" in embed.description

    @pytest.mark.asyncio
    async def test_papers(self, cog):
        ctx = make_ctx()
        await cog.papers.callback(cog, ctx, "portfolio optimization")

        ctx.defer.assert_called_once()
        embed = ctx.respond.call_args[1]["embed"]
        assert "Deep Learning" in embed.description

    @pytest.mark.asyncio
    async def test_papers_no_results(self, cog):
        cog.bot.data_manager.get_research_papers = AsyncMock(return_value=[])
        ctx = make_ctx()

        await cog.papers.callback(cog, ctx, None)

        embed = ctx.respond.call_args[1]["embed"]
        assert "No papers" in embed.description


# ── Briefing Cog ──


class TestBriefingCog:
    @pytest.fixture
    def cog(self):
        from bot.cogs.briefing import BriefingCog
        bot = make_bot()
        bot.ai_engine = MagicMock()
        bot.ai_engine.analyze = AsyncMock(return_value="Morning briefing content here.")
        bot.ai_engine.chat = AsyncMock(return_value="Macro analysis content here.")
        return BriefingCog(bot)

    @pytest.mark.asyncio
    async def test_morning(self, cog):
        ctx = make_ctx()
        await cog.morning.callback(cog, ctx)

        ctx.defer.assert_called_once()
        cog.bot.ai_engine.analyze.assert_called_once()
        ctx.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_morning_error(self, cog):
        cog.bot.ai_engine.analyze = AsyncMock(side_effect=Exception("API error"))
        ctx = make_ctx()

        await cog.morning.callback(cog, ctx)

        embed = ctx.respond.call_args[1]["embed"]
        assert "Error" in embed.title

    @pytest.mark.asyncio
    async def test_evening(self, cog):
        ctx = make_ctx()
        await cog.evening.callback(cog, ctx)

        ctx.defer.assert_called_once()
        cog.bot.ai_engine.analyze.assert_called_once()

    @pytest.mark.asyncio
    async def test_macro(self, cog):
        ctx = make_ctx()
        await cog.macro.callback(cog, ctx)

        ctx.defer.assert_called_once()
        cog.bot.ai_engine.chat.assert_called_once()


# ── News Cog ──


class TestNewsCog:
    @pytest.fixture
    def cog(self):
        from bot.cogs.news import NewsCog
        bot = make_bot()
        bot.data_manager.get_news = AsyncMock(return_value=[
            {
                "title": "Apple hits record",
                "source": "Reuters",
                "description": "Apple stock reaches all-time high.",
                "url": "https://example.com",
                "sentiment": 0.7,
                "symbols": ["AAPL"],
            },
        ])
        bot.data_manager.marketaux = MagicMock()
        bot.data_manager.marketaux.get_news = AsyncMock(return_value=[
            {
                "title": "Tech earnings strong",
                "source": "Bloomberg",
                "description": "Tech sector beats estimates.",
                "url": "https://example.com/2",
                "sentiment": 0.5,
            },
        ])
        return NewsCog(bot)

    @pytest.mark.asyncio
    async def test_latest_no_filter(self, cog):
        ctx = make_ctx()
        await cog.latest.callback(cog, ctx, None, 5)

        ctx.defer.assert_called_once()
        cog.bot.data_manager.get_news.assert_called_once_with(symbol=None, limit=5)
        ctx.respond.assert_called_once()
        assert len(ctx.respond.call_args[1]["embeds"]) == 1

    @pytest.mark.asyncio
    async def test_latest_with_symbol(self, cog):
        ctx = make_ctx()
        await cog.latest.callback(cog, ctx, "AAPL", 3)

        cog.bot.data_manager.get_news.assert_called_once_with(symbol="AAPL", limit=3)

    @pytest.mark.asyncio
    async def test_latest_invalid_symbol(self, cog):
        ctx = make_ctx()
        await cog.latest.callback(cog, ctx, "!!bad!!", 5)

        assert ctx.respond.call_args[1].get("ephemeral") is True

    @pytest.mark.asyncio
    async def test_latest_no_results(self, cog):
        cog.bot.data_manager.get_news = AsyncMock(return_value=[])
        ctx = make_ctx()

        await cog.latest.callback(cog, ctx, None, 5)

        embed = ctx.respond.call_args[1]["embed"]
        assert "No" in embed.title

    @pytest.mark.asyncio
    async def test_search(self, cog):
        ctx = make_ctx()
        await cog.search.callback(cog, ctx, "Tech")

        ctx.defer.assert_called_once()
        ctx.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_no_results(self, cog):
        cog.bot.data_manager.marketaux.get_news = AsyncMock(return_value=[])
        ctx = make_ctx()

        await cog.search.callback(cog, ctx, "nonexistent")

        embed = ctx.respond.call_args[1]["embed"]
        assert "No" in embed.title


# ── Dashboard Cog ──


class TestDashboardCog:
    @pytest.fixture
    def cog(self):
        from bot.cogs.dashboard import DashboardCog
        bot = make_bot()
        return DashboardCog(bot)

    @pytest.mark.asyncio
    @patch("bot.cogs.dashboard.WatchlistRepository")
    @patch("bot.cogs.dashboard.DashboardGenerator")
    async def test_watchlist_dashboard(self, MockGen, MockRepo, cog):
        MockRepo.return_value.get = AsyncMock(return_value=["AAPL", "MSFT"])
        mock_files = [MagicMock()]
        MockGen.return_value.generate_watchlist_dashboard = AsyncMock(return_value=mock_files)
        ctx = make_ctx()

        await cog.watchlist.callback(cog, ctx)

        ctx.defer.assert_called_once()
        assert ctx.respond.call_args[1]["files"] == mock_files

    @pytest.mark.asyncio
    @patch("bot.cogs.dashboard.WatchlistRepository")
    async def test_watchlist_empty(self, MockRepo, cog):
        MockRepo.return_value.get = AsyncMock(return_value=[])
        ctx = make_ctx()

        await cog.watchlist.callback(cog, ctx)

        embed = ctx.respond.call_args[1]["embed"]
        assert "empty" in embed.description.lower()

    @pytest.mark.asyncio
    @patch("bot.cogs.dashboard.DashboardGenerator")
    async def test_sectors_dashboard(self, MockGen, cog):
        mock_files = [MagicMock()]
        MockGen.return_value.generate_sector_dashboard = AsyncMock(return_value=mock_files)
        ctx = make_ctx()

        await cog.sectors.callback(cog, ctx)

        ctx.defer.assert_called_once()
        assert ctx.respond.call_args[1]["files"] == mock_files

    @pytest.mark.asyncio
    @patch("bot.cogs.dashboard.DashboardGenerator")
    async def test_sectors_fail(self, MockGen, cog):
        MockGen.return_value.generate_sector_dashboard = AsyncMock(return_value=[])
        ctx = make_ctx()

        await cog.sectors.callback(cog, ctx)

        embed = ctx.respond.call_args[1]["embed"]
        assert "Error" in embed.title

    @pytest.mark.asyncio
    @patch("bot.cogs.dashboard.DashboardGenerator")
    async def test_earnings_dashboard(self, MockGen, cog):
        mock_files = [MagicMock()]
        MockGen.return_value.generate_earnings_dashboard = AsyncMock(return_value=mock_files)
        ctx = make_ctx()

        await cog.earnings.callback(cog, ctx, "aapl")

        MockGen.return_value.generate_earnings_dashboard.assert_called_once_with("AAPL")

    @pytest.mark.asyncio
    @patch("bot.cogs.dashboard.DashboardGenerator")
    async def test_earnings_no_data(self, MockGen, cog):
        MockGen.return_value.generate_earnings_dashboard = AsyncMock(return_value=[])
        ctx = make_ctx()

        await cog.earnings.callback(cog, ctx, "NVDA")

        embed = ctx.respond.call_args[1]["embed"]
        assert "Error" in embed.title

    @pytest.mark.asyncio
    @patch("bot.cogs.dashboard.DashboardGenerator")
    async def test_macro_dashboard(self, MockGen, cog):
        mock_files = [MagicMock()]
        MockGen.return_value.generate_macro_dashboard = AsyncMock(return_value=mock_files)
        ctx = make_ctx()

        await cog.macro.callback(cog, ctx, "GDP")

        MockGen.return_value.generate_macro_dashboard.assert_called_once_with("GDP", "GDP")


# ── Profile Cog ──


class TestProfileCog:
    @pytest.fixture
    def cog(self):
        from bot.cogs.profile import ProfileCog
        bot = make_bot()
        return ProfileCog(bot)

    @pytest.mark.asyncio
    @patch("bot.cogs.profile.UserRepository")
    async def test_show(self, MockRepo, cog):
        repo = MockRepo.return_value
        repo.get_or_create = AsyncMock(return_value={
            "interests": {"sectors": ["Technology", "Healthcare"]},
            "focused_metrics": ["pe_ratio", "eps"],
            "risk_tolerance": "moderate",
            "notification_preferences": {"delivery": "channel"},
        })
        ctx = make_ctx()

        await cog.show.callback(cog, ctx)

        embed = ctx.respond.call_args[1]["embed"]
        assert "Profile" in embed.title

    @pytest.mark.asyncio
    @patch("bot.cogs.profile.UserRepository")
    async def test_sectors(self, MockRepo, cog):
        repo = MockRepo.return_value
        repo.update_interests = AsyncMock()
        ctx = make_ctx()

        await cog.sectors.callback(cog, ctx, "Technology, Healthcare")

        repo.update_interests.assert_called_once_with(
            ctx.author.id, {"sectors": ["Technology", "Healthcare"]}
        )
        embed = ctx.respond.call_args[1]["embed"]
        assert "Technology" in embed.description

    @pytest.mark.asyncio
    @patch("bot.cogs.profile.UserRepository")
    async def test_metrics_valid(self, MockRepo, cog):
        repo = MockRepo.return_value
        repo.update_metrics = AsyncMock()
        ctx = make_ctx()

        await cog.metrics.callback(cog, ctx, "pe_ratio, eps, revenue_growth")

        repo.update_metrics.assert_called_once_with(
            ctx.author.id, ["pe_ratio", "eps", "revenue_growth"]
        )

    @pytest.mark.asyncio
    @patch("bot.cogs.profile.UserRepository")
    async def test_metrics_invalid(self, MockRepo, cog):
        repo = MockRepo.return_value
        ctx = make_ctx()

        await cog.metrics.callback(cog, ctx, "bogus_metric, fake_metric")

        assert ctx.respond.call_args[1].get("ephemeral") is True

    @pytest.mark.asyncio
    @patch("bot.cogs.profile.UserRepository")
    async def test_risk(self, MockRepo, cog):
        repo = MockRepo.return_value
        repo.update_risk_tolerance = AsyncMock()
        ctx = make_ctx()

        await cog.risk.callback(cog, ctx, "aggressive")

        repo.update_risk_tolerance.assert_called_once_with(ctx.author.id, "aggressive")
        embed = ctx.respond.call_args[1]["embed"]
        assert "aggressive" in embed.description

    @pytest.mark.asyncio
    @patch("bot.cogs.profile.UserRepository")
    async def test_notifications(self, MockRepo, cog):
        repo = MockRepo.return_value
        repo.update_notifications = AsyncMock()
        ctx = make_ctx()

        await cog.notifications.callback(cog, ctx, "dm")

        repo.update_notifications.assert_called_once_with(
            ctx.author.id, {"delivery": "dm", "quiet_hours": None}
        )
        embed = ctx.respond.call_args[1]["embed"]
        assert "dm" in embed.description


# ── Chat Cog ──


class TestChatCog:
    @pytest.fixture
    def cog(self):
        from bot.cogs.chat import ChatCog
        bot = make_bot()
        bot.ai_engine = MagicMock()
        bot.ai_engine.chat_stream = AsyncMock(return_value="Here's my analysis...")
        bot.ai_engine.conversation = MagicMock()
        bot.ai_engine.conversation.clear_history = AsyncMock(return_value=5)
        return ChatCog(bot)

    @pytest.mark.asyncio
    async def test_ask(self, cog):
        ctx = make_ctx()
        # Mock the interaction flow: ctx.respond returns an interaction with original_response
        mock_msg = AsyncMock()
        mock_interaction = AsyncMock()
        mock_interaction.original_response = AsyncMock(return_value=mock_msg)
        ctx.respond = AsyncMock(return_value=mock_interaction)
        ctx.channel = MagicMock()
        ctx.channel.send = AsyncMock()

        await cog.ask.callback(cog, ctx, "What do you think about AAPL?")

        ctx.defer.assert_called_once()
        cog.bot.ai_engine.chat_stream.assert_called_once()
        call_kwargs = cog.bot.ai_engine.chat_stream.call_args[1]
        assert call_kwargs["user_id"] == ctx.author.id
        assert call_kwargs["content"] == "What do you think about AAPL?"

    @pytest.mark.asyncio
    async def test_ask_no_engine(self, cog):
        cog.bot.ai_engine = None
        ctx = make_ctx()

        await cog.ask.callback(cog, ctx, "test")

        assert ctx.respond.call_args[1].get("ephemeral") is True

    @pytest.mark.asyncio
    async def test_ask_error(self, cog):
        mock_msg = AsyncMock()
        mock_interaction = AsyncMock()
        mock_interaction.original_response = AsyncMock(return_value=mock_msg)
        ctx = make_ctx()
        ctx.respond = AsyncMock(return_value=mock_interaction)
        ctx.channel = MagicMock()
        ctx.channel.send = AsyncMock()
        cog.bot.ai_engine.chat_stream = AsyncMock(side_effect=Exception("API failed"))

        await cog.ask.callback(cog, ctx, "test")

        mock_msg.edit.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_chat(self, cog):
        ctx = make_ctx()
        await cog.clear_chat.callback(cog, ctx)

        cog.bot.ai_engine.conversation.clear_history.assert_called_once_with(
            ctx.author.id, ctx.channel_id
        )
        ctx.respond.assert_called_once()
        assert "5" in ctx.respond.call_args[0][0]

    @pytest.mark.asyncio
    async def test_clear_chat_no_engine(self, cog):
        cog.bot.ai_engine = None
        ctx = make_ctx()

        await cog.clear_chat.callback(cog, ctx)

        assert ctx.respond.call_args[1].get("ephemeral") is True


# ── Admin Cog ──


class TestAdminCog:
    @pytest.fixture
    def cog(self):
        from bot.cogs.admin import AdminCog
        bot = make_bot()
        bot.data_manager.health_check = AsyncMock(return_value={
            "finnhub": True, "fmp": True, "fred": False,
        })
        bot.data_manager.cache = MagicMock()
        bot.data_manager.cache.cleanup = MagicMock(return_value=3)
        bot.data_manager.cache._store = {"a": 1, "b": 2}
        return AdminCog(bot)

    @pytest.mark.asyncio
    @patch("bot.cogs.admin.get_opus_usage", return_value=(2, 5))
    async def test_status(self, mock_usage, cog):
        ctx = make_ctx()
        await cog.status.callback(cog, ctx)

        ctx.defer.assert_called_once()
        embed = ctx.respond.call_args[1]["embed"]
        assert "System Status" in embed.title

    @pytest.mark.asyncio
    async def test_cache(self, cog):
        ctx = make_ctx()
        await cog.cache.callback(cog, ctx)

        embed = ctx.respond.call_args[1]["embed"]
        assert "Cache" in embed.title
        assert "2" in embed.description  # 2 entries
        assert "3" in embed.description  # 3 expired

    @pytest.mark.asyncio
    async def test_cache_no_data_manager(self, cog):
        cog.bot.data_manager = None
        ctx = make_ctx()

        await cog.cache.callback(cog, ctx)

        ctx.respond.assert_called_once()
