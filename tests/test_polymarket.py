"""Tests for data/collectors/polymarket.py — Polymarket API collector."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from data.collectors.polymarket import PolymarketCollector, GAMMA_API_BASE


class TestPolymarketCollector:
    @pytest.fixture
    def collector(self):
        rate_limiter = MagicMock()
        rate_limiter.acquire = AsyncMock()
        rate_limiter.configure = MagicMock()
        c = PolymarketCollector(rate_limiter)
        return c

    async def test_search_markets_returns_results(self, collector):
        mock_response = [
            {
                "question": "Will the Fed cut rates in March?",
                "description": "This market resolves...",
                "outcomePrices": "[0.65, 0.35]",
                "outcomes": '["Yes", "No"]',
                "volume": 1500000,
                "liquidity": 500000,
                "endDate": "2025-03-19",
                "active": True,
                "slug": "fed-rate-cut-march",
            },
            {
                "question": "Bitcoin above 100k by June?",
                "description": "Resolves Yes if...",
                "outcomePrices": "[0.42, 0.58]",
                "outcomes": '["Yes", "No"]',
                "volume": 800000,
                "liquidity": 300000,
                "endDate": "2025-06-30",
                "active": True,
                "slug": "btc-100k-june",
            },
        ]
        collector._request = AsyncMock(return_value=mock_response)

        results = await collector.search_markets("Fed rate", limit=5)
        assert len(results) == 2
        assert results[0]["question"] == "Will the Fed cut rates in March?"
        assert results[0]["outcome_prices"] == "[0.65, 0.35]"
        assert results[0]["volume"] == 1500000
        assert results[1]["slug"] == "btc-100k-june"

    async def test_search_markets_empty(self, collector):
        collector._request = AsyncMock(return_value=[])
        results = await collector.search_markets("nonexistent topic")
        assert results == []

    async def test_search_markets_non_list_response(self, collector):
        collector._request = AsyncMock(return_value={"error": "bad request"})
        results = await collector.search_markets("test")
        assert results == []

    async def test_search_markets_respects_limit(self, collector):
        mock_response = [
            {"question": f"Q{i}", "description": "", "outcomePrices": "", "outcomes": "",
             "volume": 0, "liquidity": 0, "endDate": None, "active": True, "slug": f"q{i}"}
            for i in range(10)
        ]
        collector._request = AsyncMock(return_value=mock_response)

        results = await collector.search_markets("test", limit=3)
        assert len(results) == 3

    async def test_search_markets_truncates_description(self, collector):
        long_desc = "x" * 500
        collector._request = AsyncMock(return_value=[
            {"question": "Q", "description": long_desc, "outcomePrices": "",
             "outcomes": "", "volume": 0, "liquidity": 0, "endDate": None,
             "active": True, "slug": "q"},
        ])
        results = await collector.search_markets("test")
        assert len(results[0]["description"]) == 300

    async def test_search_markets_handles_none_description(self, collector):
        collector._request = AsyncMock(return_value=[
            {"question": "Q", "description": None, "outcomePrices": "",
             "outcomes": "", "volume": 0, "liquidity": 0, "endDate": None,
             "active": True, "slug": "q"},
        ])
        results = await collector.search_markets("test")
        assert results[0]["description"] == ""

    async def test_health_check_success(self, collector):
        collector._request = AsyncMock(return_value=[{"question": "test"}])
        assert await collector.health_check() is True

    async def test_health_check_empty(self, collector):
        collector._request = AsyncMock(return_value=[])
        assert await collector.health_check() is False

    async def test_health_check_error(self, collector):
        collector._request = AsyncMock(side_effect=Exception("timeout"))
        assert await collector.health_check() is False

    def test_api_name(self, collector):
        assert collector.api_name == "polymarket"

    async def test_request_params(self, collector):
        collector._request = AsyncMock(return_value=[])
        await collector.search_markets("recession", limit=3)
        collector._request.assert_awaited_once()
        call_args = collector._request.call_args
        params = call_args[1]["params"] if "params" in call_args[1] else call_args[0][1]
        assert params["q"] == "recession"
        assert params["limit"] == 3
        assert params["active"] == "true"
        assert params["closed"] == "false"
