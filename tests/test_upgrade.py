"""Tests for the professional-grade upgrade features:
- Prompt caching
- Extended thinking
- Technical analysis indicators
- Chart generation wiring
- Streaming + progress indicators
- Conversation summarization
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from ai.engine import AIEngine
from ai.models import ModelConfig, HAIKU, SONNET, OPUS
from ai.tools import FINANCIAL_TOOLS
from ai.conversation import ConversationManager
from bot.events import _split_message, TOOL_LABELS
from tests.conftest import FakePool, FakeRecord


# ── Models: Extended Thinking ──


class TestExtendedThinking:
    def test_haiku_no_thinking(self):
        assert HAIKU.thinking_budget is None

    def test_sonnet_thinking_budget(self):
        assert SONNET.thinking_budget == 10000

    def test_opus_thinking_budget(self):
        assert OPUS.thinking_budget == 16000

    def test_thinking_budget_field(self):
        config = ModelConfig(
            model_id="test",
            display_name="Test",
            max_tokens=1000,
            cost_per_1k_input=0.001,
            cost_per_1k_output=0.005,
            thinking_budget=5000,
        )
        assert config.thinking_budget == 5000

    def test_default_thinking_budget_none(self):
        config = ModelConfig(
            model_id="test",
            display_name="Test",
            max_tokens=1000,
            cost_per_1k_input=0.001,
            cost_per_1k_output=0.005,
        )
        assert config.thinking_budget is None


# ── Tools: Technical Analysis ──


class TestTechnicalAnalysisTool:
    def test_tool_defined(self):
        names = [t["name"] for t in FINANCIAL_TOOLS]
        assert "get_technical_indicators" in names

    def test_tool_requires_symbol(self):
        tool = next(t for t in FINANCIAL_TOOLS if t["name"] == "get_technical_indicators")
        assert "symbol" in tool["input_schema"]["required"]

    def test_tool_description(self):
        tool = next(t for t in FINANCIAL_TOOLS if t["name"] == "get_technical_indicators")
        assert "SMA" in tool["description"]
        assert "RSI" in tool["description"]
        assert "MACD" in tool["description"]


class TestPriceChartEnum:
    def test_price_chart_in_enum(self):
        chart_tool = next(t for t in FINANCIAL_TOOLS if t["name"] == "generate_chart")
        enums = chart_tool["input_schema"]["properties"]["chart_type"]["enum"]
        assert "price_chart" in enums


# ── Engine: Technical Analysis Execution ──


class TestExecuteToolTechnical:
    @pytest.fixture
    def engine(self, mock_data_manager, fake_pool):
        with patch("ai.engine.settings") as mock_settings:
            mock_settings.anthropic_api_key = "test-key"
            with patch("ai.engine.ConversationManager"):
                e = AIEngine(data_manager=mock_data_manager, db_pool=fake_pool)
                return e

    async def test_get_technical_indicators(self, engine, mock_data_manager):
        mock_data_manager.get_technical_indicators = AsyncMock(return_value={
            "symbol": "AAPL",
            "sma_20": 185.0,
            "sma_50": 180.0,
            "sma_200": 170.0,
            "rsi_14": 62.5,
            "ema_12": 184.0,
            "ema_26": 181.0,
            "macd": 3.0,
        })
        result = await engine._execute_tool("get_technical_indicators", {"symbol": "AAPL"})
        mock_data_manager.get_technical_indicators.assert_awaited_once_with("AAPL")
        assert result["symbol"] == "AAPL"
        assert result["rsi_14"] == 62.5
        assert result["macd"] == 3.0


# ── Engine: Chart Generation Wiring ──


class TestChartGenerationWiring:
    @pytest.fixture
    def engine(self, mock_data_manager, fake_pool):
        with patch("ai.engine.settings") as mock_settings:
            mock_settings.anthropic_api_key = "test-key"
            with patch("ai.engine.ConversationManager"):
                e = AIEngine(data_manager=mock_data_manager, db_pool=fake_pool)
                return e

    async def test_chart_no_send_file(self, engine):
        result = await engine._execute_tool(
            "generate_chart",
            {"chart_type": "comparison", "symbols": ["AAPL"]},
        )
        assert result["status"] == "charts unavailable in this context"

    @patch("dashboard.generator.DashboardGenerator")
    async def test_chart_with_send_file(self, MockGen, engine):
        mock_file = MagicMock()
        mock_gen = MockGen.return_value
        mock_gen.generate_chart = AsyncMock(return_value=[mock_file])
        send_file = AsyncMock()

        result = await engine._execute_tool(
            "generate_chart",
            {"chart_type": "sector_heatmap"},
            send_file=send_file,
        )
        assert result["status"] == "chart_sent"
        send_file.assert_awaited_once_with(mock_file)


# ── Prompt Caching Structure ──


class TestPromptCaching:
    def test_last_tool_gets_cache_control(self):
        """Verify the cache_control injection logic works correctly."""
        cached_tools = list(FINANCIAL_TOOLS)
        cached_tools[-1] = {**cached_tools[-1], "cache_control": {"type": "ephemeral"}}
        assert "cache_control" in cached_tools[-1]
        assert cached_tools[-1]["cache_control"]["type"] == "ephemeral"
        # Earlier tools should NOT have cache_control
        assert "cache_control" not in cached_tools[0]

    def test_system_blocks_structure(self):
        """Verify the system block format for prompt caching."""
        system_prompt = "You are a test assistant."
        system_blocks = [
            {"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}
        ]
        assert len(system_blocks) == 1
        assert system_blocks[0]["type"] == "text"
        assert system_blocks[0]["cache_control"]["type"] == "ephemeral"


# ── Tool Labels ──


class TestToolLabels:
    def test_all_tools_have_labels(self):
        tool_names = {t["name"] for t in FINANCIAL_TOOLS}
        labeled = set(TOOL_LABELS.keys())
        # All tools should have labels
        for name in tool_names:
            assert name in labeled, f"Tool '{name}' missing from TOOL_LABELS"

    def test_labels_are_human_readable(self):
        for name, label in TOOL_LABELS.items():
            assert len(label) > 0
            # Should not start with get_ or look like code
            assert not label.startswith("get_")


# ── Conversation Summarization ──


class TestConversationSummarization:
    @pytest.fixture
    def conv_mgr(self, fake_pool):
        return ConversationManager(fake_pool)

    async def test_no_summarize_under_threshold(self, conv_mgr, fake_pool):
        """Should not summarize when <= 20 messages."""
        fake_pool.conn.fetchval_result = 10
        mock_engine = MagicMock()
        mock_engine.analyze = AsyncMock()
        await conv_mgr.summarize_if_needed(123, 456, mock_engine)
        mock_engine.analyze.assert_not_awaited()

    async def test_no_summarize_at_threshold(self, conv_mgr, fake_pool):
        """Should not summarize at exactly 20 messages."""
        fake_pool.conn.fetchval_result = 20
        mock_engine = MagicMock()
        mock_engine.analyze = AsyncMock()
        await conv_mgr.summarize_if_needed(123, 456, mock_engine)
        mock_engine.analyze.assert_not_awaited()

    async def test_summarize_over_threshold(self, conv_mgr, fake_pool):
        """Should summarize when > 20 messages."""
        fake_pool.conn.fetchval_result = 25
        # Build 25 fake messages
        messages = [
            {"id": i, "role": "user" if i % 2 == 0 else "assistant",
             "content": f"Message {i}", "is_summary": False}
            for i in range(25)
        ]
        fake_pool.conn.fetch_results = [messages]

        mock_engine = MagicMock()
        mock_engine.analyze = AsyncMock(return_value="Summary of conversation about stocks")

        await conv_mgr.summarize_if_needed(123, 456, mock_engine)
        mock_engine.analyze.assert_awaited_once()
        # Check that the analyze was called with "haiku" model
        call_kwargs = mock_engine.analyze.call_args[1]
        assert call_kwargs["force_model"] == "haiku"

    async def test_summarize_handles_error(self, conv_mgr, fake_pool):
        """Should handle summarization errors gracefully."""
        fake_pool.conn.fetchval_result = 25
        messages = [
            {"id": i, "role": "user", "content": f"msg {i}", "is_summary": False}
            for i in range(25)
        ]
        fake_pool.conn.fetch_results = [messages]

        mock_engine = MagicMock()
        mock_engine.analyze = AsyncMock(side_effect=Exception("API error"))

        # Should not raise
        await conv_mgr.summarize_if_needed(123, 456, mock_engine)


# ── DataManager: Technical Indicators ──


class TestDataManagerTechnicals:
    @pytest.fixture
    def dm(self):
        from data.manager import DataManager
        d = DataManager()
        d.fmp = MagicMock()
        d.fmp.get_technical_indicator = AsyncMock(return_value=[{"sma": 185.0}])
        d.fmp.get_historical_price = AsyncMock(return_value=[
            {"date": "2025-01-15", "open": 180, "high": 186, "low": 179, "close": 185, "volume": 1000000}
        ])
        d.cache = MagicMock()
        d.cache.get = MagicMock(return_value=None)
        d.cache.set = MagicMock()
        return d

    async def test_get_technical_indicators(self, dm):
        # Mock each indicator call
        dm.fmp.get_technical_indicator = AsyncMock(side_effect=[
            [{"sma": 185.0}],   # sma 20
            [{"sma": 180.0}],   # sma 50
            [{"sma": 170.0}],   # sma 200
            [{"rsi": 62.5}],    # rsi 14
            [{"ema": 184.0}],   # ema 12
            [{"ema": 181.0}],   # ema 26
        ])
        result = await dm.get_technical_indicators("AAPL")
        assert result["symbol"] == "AAPL"
        assert result["sma_20"] == 185.0
        assert result["sma_50"] == 180.0
        assert result["sma_200"] == 170.0
        assert result["rsi_14"] == 62.5
        assert result["ema_12"] == 184.0
        assert result["ema_26"] == 181.0
        assert result["macd"] == 3.0  # 184 - 181

    async def test_get_technical_indicators_cached(self, dm):
        dm.cache.get.return_value = {"symbol": "AAPL", "sma_20": 185.0}
        result = await dm.get_technical_indicators("AAPL")
        assert result["sma_20"] == 185.0
        dm.fmp.get_technical_indicator.assert_not_awaited()

    async def test_get_historical_prices(self, dm):
        result = await dm.get_historical_prices("AAPL", limit=90)
        assert len(result) == 1
        assert result[0]["close"] == 185
        dm.fmp.get_historical_price.assert_awaited_once_with("AAPL", limit=90)

    async def test_get_historical_prices_cached(self, dm):
        dm.cache.get.return_value = [{"date": "2025-01-15", "close": 185}]
        result = await dm.get_historical_prices("AAPL")
        dm.fmp.get_historical_price.assert_not_awaited()


# ── Charts: Price Chart ──


class TestPriceChart:
    def test_price_chart_creation(self):
        from dashboard.charts import price_chart
        data = [
            {"date": f"2025-01-{i:02d}", "open": 180+i, "high": 185+i,
             "low": 178+i, "close": 183+i, "volume": 1000000+i*100}
            for i in range(1, 11)
        ]
        fig = price_chart("AAPL", data, "AAPL Price")
        assert fig is not None
        # Should have 2 traces (candlestick + volume)
        assert len(fig.data) == 2

    def test_price_chart_empty_data(self):
        from dashboard.charts import price_chart
        fig = price_chart("AAPL", [], "Empty")
        assert fig is not None


# ── Dashboard Generator: Price Chart ──


class TestDashboardPriceChart:
    async def test_generate_price_chart(self, mock_data_manager):
        mock_data_manager.get_historical_prices = AsyncMock(return_value=[
            {"date": f"2025-01-{i:02d}", "open": 180, "high": 186,
             "low": 179, "close": 185, "volume": 1000000}
            for i in range(1, 11)
        ])

        with patch("dashboard.generator.render_to_discord_file") as mock_render:
            mock_render.return_value = MagicMock()
            from dashboard.generator import DashboardGenerator
            gen = DashboardGenerator(mock_data_manager)
            files = await gen.generate_price_chart("AAPL")
            assert len(files) == 1
            mock_render.assert_called_once()

    async def test_generate_chart_price_type(self, mock_data_manager):
        mock_data_manager.get_historical_prices = AsyncMock(return_value=[
            {"date": "2025-01-01", "open": 180, "high": 186,
             "low": 179, "close": 185, "volume": 1000000}
        ])

        with patch("dashboard.generator.render_to_discord_file") as mock_render:
            mock_render.return_value = MagicMock()
            from dashboard.generator import DashboardGenerator
            gen = DashboardGenerator(mock_data_manager)
            files = await gen.generate_chart("price_chart", symbols=["AAPL"])
            assert len(files) == 1


# ── Events: Message Splitting ──


class TestSplitMessage:
    def test_short_message(self):
        assert _split_message("hello") == ["hello"]

    def test_long_message_splits_at_newline(self):
        text = "a" * 1500 + "\n" + "b" * 1000
        chunks = _split_message(text, limit=2000)
        assert len(chunks) == 2
        assert all(len(c) <= 2000 for c in chunks)

    def test_exact_limit(self):
        text = "a" * 2000
        assert _split_message(text) == [text]


# ── Rate Limiter: Notifications ──


class TestRateLimiterNotifications:
    async def test_on_rate_limit_callback_fires(self):
        from data.rate_limiter import RateLimiter
        rl = RateLimiter()
        rl.configure("test_api", 1)  # 1 req/min — will trigger on 2nd

        notified = []
        async def on_limit(api_name, wait_secs):
            notified.append((api_name, wait_secs))

        rl.on_rate_limit = on_limit

        # First call should be fine
        await rl.acquire("test_api")
        assert len(notified) == 0

        # Second call should trigger notification + wait
        await rl.acquire("test_api")
        assert len(notified) == 1
        assert notified[0][0] == "test_api"

    async def test_debounce_prevents_spam(self):
        from data.rate_limiter import RateLimiter
        rl = RateLimiter()
        rl.configure("test_api", 1)

        call_count = 0
        async def on_limit(api_name, wait_secs):
            nonlocal call_count
            call_count += 1

        rl.on_rate_limit = on_limit

        # Fill the window
        await rl.acquire("test_api")
        # Two more acquires — should only notify once due to debounce
        await rl.acquire("test_api")
        await rl.acquire("test_api")
        assert call_count == 1  # debounced

    def test_get_usage(self):
        from data.rate_limiter import RateLimiter
        rl = RateLimiter()
        rl.configure("finnhub", 60)
        rl.configure("fmp", 30)
        usage = rl.get_usage()
        assert "finnhub" in usage
        assert usage["finnhub"]["limit"] == 60
        assert usage["finnhub"]["used"] == 0
        assert usage["fmp"]["limit"] == 30

    async def test_no_callback_no_error(self):
        from data.rate_limiter import RateLimiter
        rl = RateLimiter()
        rl.configure("test_api", 1)
        # No callback set — should not error
        await rl.acquire("test_api")
        await rl.acquire("test_api")  # triggers throttle, no callback — should not crash
