"""Price alert trigger detection."""

import structlog
from typing import Any
from notifications.types import Notification
from config.constants import NotificationType

log = structlog.get_logger(__name__)


def check_price_alerts(
    alerts: list[dict[str, Any]],
    quotes: dict[str, dict[str, Any]],
) -> list[tuple[Notification, int]]:
    """Check if any price alerts should trigger.

    Returns list of (Notification, alert_id) tuples for triggered alerts.
    """
    triggered = []

    for alert in alerts:
        symbol = alert["symbol"]
        quote = quotes.get(symbol)
        if not quote:
            continue

        price = quote.get("price", 0)
        change_pct = quote.get("change_pct", 0)
        condition = alert["condition"]
        threshold = float(alert["threshold"])

        should_trigger = False
        if condition == "above" and price > threshold:
            should_trigger = True
        elif condition == "below" and price < threshold:
            should_trigger = True
        elif condition == "change_pct" and abs(change_pct) >= abs(threshold):
            should_trigger = True

        if should_trigger:
            notif = Notification(
                type=NotificationType.PRICE_ALERT,
                title=f"Price Alert — {symbol}",
                description=f"{symbol} is now ${price:.2f} ({condition} ${threshold:.2f})",
                symbol=symbol,
                data={
                    "price": price,
                    "condition": condition,
                    "threshold": threshold,
                    "change_pct": change_pct,
                },
                target_users=[alert["discord_id"]],
                urgency="high",
            )
            triggered.append((notif, alert["id"]))

    return triggered
