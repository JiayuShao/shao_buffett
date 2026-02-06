"""Tests for ai/router.py — model routing and classification."""

import pytest
from unittest.mock import patch
from ai.router import (
    route_request,
    record_opus_call,
    get_opus_usage,
    _check_opus_budget,
    ROUTINE_PATTERNS,
    DEEP_PATTERNS,
    PORTFOLIO_UPGRADE_PATTERNS,
)
from ai.models import HAIKU, SONNET, OPUS, TIER_ROUTINE, TIER_STANDARD, TIER_DEEP


# ── Force tier override ──

class TestForceTier:
    def test_force_haiku(self):
        assert route_request("deep analysis of AAPL", force_tier="haiku") == HAIKU

    def test_force_sonnet(self):
        assert route_request("what is the price of AAPL", force_tier="sonnet") == SONNET

    def test_force_opus(self):
        assert route_request("hello", force_tier="opus") == OPUS

    def test_force_tier_case_insensitive(self):
        assert route_request("hello", force_tier="HAIKU") == HAIKU
        assert route_request("hello", force_tier="Sonnet") == SONNET

    def test_force_unknown_defaults_to_sonnet(self):
        assert route_request("hello", force_tier="gpt4") == SONNET


# ── Routine patterns → Haiku ──

class TestRoutineRouting:
    def test_price_query(self):
        assert route_request("what is the price of AAPL") == TIER_ROUTINE

    def test_whats_quote(self):
        assert route_request("what's the quote of TSLA") == TIER_ROUTINE

    def test_get_quote(self):
        assert route_request("get quote MSFT") == TIER_ROUTINE

    def test_show_watchlist(self):
        assert route_request("show watchlist") == TIER_ROUTINE

    def test_classify(self):
        assert route_request("classify this news article") == TIER_ROUTINE

    def test_sentiment_score(self):
        assert route_request("what's the sentiment score for AAPL") == TIER_ROUTINE


# ── Deep patterns → Opus ──

class TestDeepRouting:
    @patch("ai.router._check_opus_budget", return_value=True)
    def test_deep_analysis(self, _):
        assert route_request("deep analysis of NVDA") == TIER_DEEP

    @patch("ai.router._check_opus_budget", return_value=True)
    def test_dcf_model(self, _):
        assert route_request("build a DCF model for MSFT") == TIER_DEEP

    @patch("ai.router._check_opus_budget", return_value=True)
    def test_comprehensive_report(self, _):
        assert route_request("comprehensive report on Tesla") == TIER_DEEP

    @patch("ai.router._check_opus_budget", return_value=True)
    def test_compare_vs(self, _):
        assert route_request("compare AAPL vs MSFT and GOOGL") == TIER_DEEP

    @patch("ai.router._check_opus_budget", return_value=True)
    def test_investment_thesis(self, _):
        assert route_request("write an investment thesis for NVDA") == TIER_DEEP

    @patch("ai.router._check_opus_budget", return_value=True)
    def test_risk_assessment(self, _):
        assert route_request("risk assessment of my portfolio") == TIER_DEEP

    @patch("ai.router._check_opus_budget", return_value=False)
    def test_deep_falls_back_to_sonnet_over_budget(self, _):
        assert route_request("deep research on AAPL") == TIER_STANDARD


# ── Portfolio-aware upgrade patterns ──

class TestPortfolioRouting:
    def test_should_i_buy_with_portfolio(self):
        assert route_request("should i buy more NVDA?", has_portfolio=True) == TIER_STANDARD

    def test_should_i_sell_with_portfolio(self):
        assert route_request("should i sell AAPL?", has_portfolio=True) == TIER_STANDARD

    def test_rebalance_with_portfolio(self):
        assert route_request("how should I rebalance?", has_portfolio=True) == TIER_STANDARD

    def test_allocation_with_portfolio(self):
        assert route_request("check my allocation", has_portfolio=True) == TIER_STANDARD

    def test_tax_loss_harvest_with_portfolio(self):
        assert route_request("any tax loss harvest opportunities?", has_portfolio=True) == TIER_STANDARD

    def test_whats_my_portfolio(self):
        assert route_request("what's my portfolio worth?", has_portfolio=True) == TIER_STANDARD

    def test_position_sizing(self):
        assert route_request("help with position sizing", has_portfolio=True) == TIER_STANDARD

    def test_portfolio_risk(self):
        assert route_request("portfolio risk analysis", has_portfolio=True) == TIER_STANDARD

    def test_portfolio_pattern_without_portfolio_does_not_upgrade(self):
        # Without portfolio, "should i buy" would still match routine or fall to default
        # It doesn't match routine patterns, so defaults to TIER_STANDARD anyway
        result = route_request("should i buy NVDA?", has_portfolio=False)
        assert result == TIER_STANDARD  # default

    def test_buy_more_with_portfolio(self):
        assert route_request("buy more TSLA shares", has_portfolio=True) == TIER_STANDARD

    def test_exit_position(self):
        assert route_request("should I exit my position in COIN?", has_portfolio=True) == TIER_STANDARD


# ── Default routing ──

class TestDefaultRouting:
    def test_general_question_routes_to_sonnet(self):
        assert route_request("tell me about Apple's services revenue growth") == TIER_STANDARD

    def test_empty_string(self):
        assert route_request("") == TIER_STANDARD


# ── Opus budget tracking ──

class TestOpusBudget:
    def test_record_and_get_usage(self):
        import ai.router as router
        # Reset state
        router._opus_calls_today = 0
        router._opus_date = ""

        record_opus_call()
        used, limit = get_opus_usage()
        assert used == 1

    @patch("ai.router.settings")
    def test_check_budget_resets_on_new_day(self, mock_settings):
        import ai.router as router
        mock_settings.opus_daily_budget = 20
        router._opus_calls_today = 10
        router._opus_date = "2020-01-01"  # Stale date
        assert _check_opus_budget() is True
        assert router._opus_calls_today == 0  # Reset
