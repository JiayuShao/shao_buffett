"""Tests for config/constants.py — enums and configuration values."""

import pytest
from config.constants import (
    EmbedColor,
    NotificationType,
    RiskTolerance,
    API_RATE_LIMITS,
    POLL_INTERVALS,
    CACHE_TTL,
    SECTORS,
    METRIC_OPTIONS,
    MAX_WATCHLIST_SIZE,
    MAX_ALERTS_PER_USER,
)


class TestNotificationType:
    def test_all_notification_types(self):
        expected = {
            "price_alert", "breaking_news", "analyst_upgrade", "analyst_downgrade",
            "target_price_change", "earnings_surprise", "macro_release",
            "insider_trade", "sec_filing", "earnings_transcript",
            "research_digest", "morning_briefing", "evening_summary",
            "proactive_insight",
        }
        actual = {nt.value for nt in NotificationType}
        assert actual == expected

    def test_proactive_insight_exists(self):
        assert NotificationType.PROACTIVE_INSIGHT == "proactive_insight"

    def test_is_string_enum(self):
        assert isinstance(NotificationType.PRICE_ALERT.value, str)


class TestEmbedColor:
    def test_colors_are_ints(self):
        for color in EmbedColor:
            assert isinstance(color.value, int)

    def test_specific_colors(self):
        assert EmbedColor.BULLISH == 0x00C853
        assert EmbedColor.BEARISH == 0xFF1744


class TestRiskTolerance:
    def test_values(self):
        assert RiskTolerance.CONSERVATIVE == "conservative"
        assert RiskTolerance.MODERATE == "moderate"
        assert RiskTolerance.AGGRESSIVE == "aggressive"


class TestAPIRateLimits:
    def test_all_apis_have_limits(self):
        expected_apis = {"finnhub", "fred", "marketaux", "fmp", "sec_edgar", "arxiv"}
        assert expected_apis.issubset(set(API_RATE_LIMITS.keys()))

    def test_limits_are_positive(self):
        for api, limit in API_RATE_LIMITS.items():
            assert limit > 0, f"{api} rate limit should be positive"


class TestPollIntervals:
    def test_price_alerts_fast(self):
        assert POLL_INTERVALS["price_alerts"] <= 60

    def test_all_intervals_positive(self):
        for name, interval in POLL_INTERVALS.items():
            assert interval > 0, f"{name} poll interval should be positive"


class TestCacheTTL:
    def test_quote_is_short(self):
        assert CACHE_TTL["quote"] <= 60

    def test_profile_is_long(self):
        assert CACHE_TTL["profile"] >= 3600


class TestSectors:
    def test_has_major_sectors(self):
        assert "Technology" in SECTORS
        assert "Healthcare" in SECTORS
        assert "Energy" in SECTORS


class TestLimits:
    def test_watchlist_limit(self):
        assert MAX_WATCHLIST_SIZE >= 10

    def test_alerts_limit(self):
        assert MAX_ALERTS_PER_USER >= 10
