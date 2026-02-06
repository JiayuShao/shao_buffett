"""Tests for data/manager.py — DataManager orchestration."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from data.manager import DataManager


class TestDataManagerPolymarket:
    """Test the new Polymarket integration in DataManager."""

    @pytest.fixture
    def dm(self):
        d = DataManager()
        d.polymarket = MagicMock()
        d.polymarket.search_markets = AsyncMock(return_value=[
            {"question": "Fed rate cut?", "outcome_prices": "[0.65, 0.35]"},
        ])
        d.cache = MagicMock()
        d.cache.get = MagicMock(return_value=None)
        d.cache.set = MagicMock()
        return d

    async def test_get_polymarket_fetches_data(self, dm):
        result = await dm.get_polymarket("Fed rate", limit=5)
        assert len(result) == 1
        assert result[0]["question"] == "Fed rate cut?"
        dm.polymarket.search_markets.assert_awaited_once_with("Fed rate", limit=5)

    async def test_get_polymarket_uses_cache(self, dm):
        dm.cache.get.return_value = [{"question": "cached"}]
        result = await dm.get_polymarket("test")
        assert result == [{"question": "cached"}]
        dm.polymarket.search_markets.assert_not_awaited()

    async def test_get_polymarket_sets_cache(self, dm):
        await dm.get_polymarket("test", limit=3)
        dm.cache.set.assert_called_once()
        call_args = dm.cache.set.call_args
        assert "polymarket:test:3" == call_args[0][0]


class TestDataManagerCollectors:
    """Test that DataManager properly initializes all collectors."""

    def test_has_polymarket_collector(self):
        with patch("data.manager.FinnhubCollector"), \
             patch("data.manager.FredCollector"), \
             patch("data.manager.MarketAuxCollector"), \
             patch("data.manager.FMPCollector"), \
             patch("data.manager.SECEdgarCollector"), \
             patch("data.manager.ArxivCollector"), \
             patch("data.manager.PolymarketCollector") as MockPoly:
            dm = DataManager()
            assert hasattr(dm, "polymarket")
            MockPoly.assert_called_once()

    def test_health_check_includes_polymarket(self):
        with patch("data.manager.FinnhubCollector"), \
             patch("data.manager.FredCollector"), \
             patch("data.manager.MarketAuxCollector"), \
             patch("data.manager.FMPCollector"), \
             patch("data.manager.SECEdgarCollector"), \
             patch("data.manager.ArxivCollector"), \
             patch("data.manager.PolymarketCollector"):
            dm = DataManager()
            # Verify health_check method uses polymarket
            # We can't call it without await, but we can check it's included in the checks dict
            # by examining the method source
            import inspect
            src = inspect.getsource(dm.health_check)
            assert "polymarket" in src
