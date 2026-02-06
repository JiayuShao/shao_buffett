"""Tests for notifications/types.py — Notification dataclass."""

import pytest
from notifications.types import Notification
from config.constants import NotificationType


class TestNotification:
    def test_create_basic(self):
        notif = Notification(
            type=NotificationType.PRICE_ALERT,
            title="Price Alert",
            description="AAPL hit $190",
        )
        assert notif.type == NotificationType.PRICE_ALERT
        assert notif.title == "Price Alert"
        assert notif.symbol is None
        assert notif.urgency == "medium"
        assert notif.target_users is None

    def test_create_with_all_fields(self):
        notif = Notification(
            type=NotificationType.BREAKING_NEWS,
            title="Breaking",
            description="Big news",
            symbol="AAPL",
            data={"source": "Reuters"},
            target_users=[111, 222],
            urgency="critical",
        )
        assert notif.symbol == "AAPL"
        assert notif.data["source"] == "Reuters"
        assert notif.target_users == [111, 222]
        assert notif.urgency == "critical"

    def test_auto_content_hash(self):
        notif = Notification(
            type=NotificationType.PRICE_ALERT,
            title="Test",
            description="Desc",
            symbol="AAPL",
        )
        assert notif.content_hash != ""
        assert len(notif.content_hash) == 16

    def test_custom_content_hash(self):
        notif = Notification(
            type=NotificationType.PRICE_ALERT,
            title="Test",
            description="Desc",
            content_hash="custom_hash",
        )
        assert notif.content_hash == "custom_hash"

    def test_same_inputs_same_hash(self):
        n1 = Notification(type=NotificationType.PRICE_ALERT, title="Test", description="D", symbol="AAPL")
        n2 = Notification(type=NotificationType.PRICE_ALERT, title="Test", description="D", symbol="AAPL")
        assert n1.content_hash == n2.content_hash

    def test_different_symbols_different_hash(self):
        n1 = Notification(type=NotificationType.PRICE_ALERT, title="Test", description="D", symbol="AAPL")
        n2 = Notification(type=NotificationType.PRICE_ALERT, title="Test", description="D", symbol="MSFT")
        assert n1.content_hash != n2.content_hash

    def test_proactive_insight_type(self):
        notif = Notification(
            type=NotificationType.PROACTIVE_INSIGHT,
            title="Insight",
            description="Your holding moved",
            data={"insight_type": "price_movement"},
        )
        assert notif.type == NotificationType.PROACTIVE_INSIGHT

    def test_default_data_is_dict(self):
        notif = Notification(type=NotificationType.PRICE_ALERT, title="T", description="D")
        assert isinstance(notif.data, dict)
        assert notif.data == {}
