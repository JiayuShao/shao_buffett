"""Tests for data/manager.py — DataManager orchestration."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from data.manager import DataManager


class TestDataManagerCollectors:
    """Test that DataManager properly initializes all collectors."""

    def test_has_all_collectors(self):
        with patch("data.manager.FinnhubCollector"), \
             patch("data.manager.FredCollector"), \
             patch("data.manager.MarketAuxCollector"), \
             patch("data.manager.FMPCollector"), \
             patch("data.manager.SECEdgarCollector"), \
             patch("data.manager.ArxivCollector"):
            dm = DataManager()
            assert hasattr(dm, "finnhub")
            assert hasattr(dm, "fred")
            assert hasattr(dm, "marketaux")
            assert hasattr(dm, "fmp")
            assert hasattr(dm, "sec_edgar")
            assert hasattr(dm, "arxiv")

    def test_health_check_includes_all_apis(self):
        with patch("data.manager.FinnhubCollector"), \
             patch("data.manager.FredCollector"), \
             patch("data.manager.MarketAuxCollector"), \
             patch("data.manager.FMPCollector"), \
             patch("data.manager.SECEdgarCollector"), \
             patch("data.manager.ArxivCollector"):
            dm = DataManager()
            import inspect
            src = inspect.getsource(dm.health_check)
            for api in ["finnhub", "fred", "marketaux", "fmp", "sec_edgar", "arxiv"]:
                assert api in src
