"""Earnings surprise detection and transcript summarization."""

import structlog
from typing import Any
from notifications.types import Notification
from config.constants import NotificationType

log = structlog.get_logger(__name__)

_seen_earnings: set[str] = set()


def process_earnings(
    symbol: str,
    earnings: list[dict[str, Any]],
) -> list[Notification]:
    """Detect earnings surprises."""
    notifications = []

    for earning in earnings[:2]:  # Check most recent 2 quarters
        period = earning.get("period", "")
        key = f"{symbol}:{period}"
        if key in _seen_earnings:
            continue

        actual = earning.get("actual")
        estimate = earning.get("estimate")

        if actual is None or estimate is None:
            continue

        _seen_earnings.add(key)

        if estimate != 0:
            surprise_pct = ((actual - estimate) / abs(estimate)) * 100
        else:
            surprise_pct = 0

        if abs(surprise_pct) < 1:  # Skip tiny surprises
            continue

        beat = surprise_pct > 0
        notif = Notification(
            type=NotificationType.EARNINGS_SURPRISE,
            title=f"Earnings {'Beat' if beat else 'Miss'} — {symbol}",
            description=(
                f"{symbol} reported EPS of ${actual:.2f} vs estimate of ${estimate:.2f} "
                f"({'beat' if beat else 'missed'} by {abs(surprise_pct):.1f}%)"
            ),
            symbol=symbol,
            data={
                "actual_eps": actual,
                "estimated_eps": estimate,
                "surprise_pct": surprise_pct,
                "period": period,
                "revenue": earning.get("revenue"),
                "revenue_estimate": earning.get("revenueEstimate"),
            },
            urgency="critical" if abs(surprise_pct) > 10 else "high",
        )
        notifications.append(notif)

    return notifications
