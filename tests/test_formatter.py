"""Tests for notifications/formatter.py — notification embed formatting."""

import pytest
from notifications.formatter import format_notification, _format_proactive_insight
from notifications.types import Notification
from config.constants import NotificationType, EmbedColor


class TestFormatNotification:
    """Test the dispatch function routes to correct formatters."""

    def test_price_alert(self):
        notif = Notification(
            type=NotificationType.PRICE_ALERT,
            title="Price Alert",
            description="AAPL hit target",
            symbol="AAPL",
            data={"price": 190.50, "condition": "above", "threshold": 190.0},
        )
        embed = format_notification(notif)
        assert "AAPL" in embed.title
        assert "Price Alert" in embed.title

    def test_breaking_news(self):
        notif = Notification(
            type=NotificationType.BREAKING_NEWS,
            title="Big news about tech",
            description="Tech stocks surging",
            data={"source": "Reuters", "sentiment": 0.8, "url": "https://example.com"},
        )
        embed = format_notification(notif)
        assert "Big news about tech" in embed.title

    def test_analyst_upgrade(self):
        notif = Notification(
            type=NotificationType.ANALYST_UPGRADE,
            title="Upgrade",
            description="Upgraded to buy",
            symbol="NVDA",
            data={"firm": "Goldman Sachs", "from_grade": "Hold", "to_grade": "Buy"},
        )
        embed = format_notification(notif)
        assert "Upgrade" in embed.title
        assert embed.color.value == EmbedColor.BULLISH

    def test_analyst_downgrade(self):
        notif = Notification(
            type=NotificationType.ANALYST_DOWNGRADE,
            title="Downgrade",
            description="Downgraded to sell",
            symbol="TSLA",
            data={"firm": "JP Morgan", "from_grade": "Buy", "to_grade": "Sell"},
        )
        embed = format_notification(notif)
        assert "Downgrade" in embed.title
        assert embed.color.value == EmbedColor.BEARISH

    def test_earnings_beat(self):
        notif = Notification(
            type=NotificationType.EARNINGS_SURPRISE,
            title="Earnings",
            description="AAPL beat estimates",
            symbol="AAPL",
            data={"surprise_pct": 5.2, "actual_eps": 2.18, "estimated_eps": 2.10},
        )
        embed = format_notification(notif)
        assert "Beat" in embed.title
        assert embed.color.value == EmbedColor.BULLISH

    def test_earnings_miss(self):
        notif = Notification(
            type=NotificationType.EARNINGS_SURPRISE,
            title="Earnings",
            description="TSLA missed estimates",
            symbol="TSLA",
            data={"surprise_pct": -3.1, "actual_eps": 0.85, "estimated_eps": 0.88},
        )
        embed = format_notification(notif)
        assert "Miss" in embed.title
        assert embed.color.value == EmbedColor.BEARISH

    def test_unknown_type_uses_default(self):
        """Unknown notification type should use the default formatter."""
        notif = Notification(
            type=NotificationType.MORNING_BRIEFING,
            title="Morning Briefing",
            description="Market overview...",
        )
        embed = format_notification(notif)
        assert embed.title == "Morning Briefing"


class TestFormatProactiveInsight:
    def _make_insight(self, insight_type, title="Test", description="Details", symbol=None, symbols=None):
        return Notification(
            type=NotificationType.PROACTIVE_INSIGHT,
            title=title,
            description=description,
            symbol=symbol,
            data={"insight_type": insight_type, "symbols": symbols or []},
        )

    def test_price_movement(self):
        notif = self._make_insight("price_movement", "AAPL +5%", "Big move", "AAPL")
        embed = format_notification(notif)
        assert "AAPL +5%" in embed.title
        assert embed.color.value == EmbedColor.ALERT
        assert any(f.name == "Symbol" for f in embed.fields)

    def test_earnings_upcoming(self):
        notif = self._make_insight("earnings_upcoming", "NVDA earnings in 3 days")
        embed = format_notification(notif)
        assert embed.color.value == EmbedColor.EARNINGS

    def test_action_reminder(self):
        notif = self._make_insight("action_reminder", "Pending action (5 days)")
        embed = format_notification(notif)
        assert embed.color.value == EmbedColor.WARNING

    def test_symbol_suggestion(self):
        notif = self._make_insight("symbol_suggestion", "You frequently ask about TSLA")
        embed = format_notification(notif)
        assert embed.color.value == EmbedColor.INFO

    def test_news_relevant(self):
        notif = self._make_insight("news_relevant", "News about your holding")
        embed = format_notification(notif)
        assert embed.color.value == EmbedColor.NEWS

    def test_portfolio_drift(self):
        notif = self._make_insight("portfolio_drift", "Portfolio drift detected")
        embed = format_notification(notif)
        assert embed.color.value == EmbedColor.WARNING

    def test_unknown_insight_type_default(self):
        notif = self._make_insight("unknown_type", "Something")
        embed = format_notification(notif)
        assert embed.color.value == EmbedColor.INFO

    def test_footer(self):
        notif = self._make_insight("price_movement", "Test")
        embed = format_notification(notif)
        assert "Proactive Insight" in embed.footer.text

    def test_no_symbol_field_when_none(self):
        notif = self._make_insight("action_reminder", "Pending")
        embed = format_notification(notif)
        assert not any(f.name == "Symbol" for f in embed.fields)
