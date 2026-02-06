"""Macro economic data processing."""

import structlog
from typing import Any
from notifications.types import Notification
from config.constants import NotificationType

log = structlog.get_logger(__name__)

_last_values: dict[str, str] = {}


def process_macro_data(snapshot: dict[str, Any]) -> list[Notification]:
    """Detect significant macro data changes."""
    notifications = []

    for name, data in snapshot.items():
        value = data.get("value", "")
        date = data.get("date", "")
        series_id = data.get("series_id", "")

        if not value or value == ".":
            continue

        key = f"{series_id}:{date}"
        last = _last_values.get(series_id)

        if last is None:
            _last_values[series_id] = value
            continue

        if value != last:
            _last_values[series_id] = value

            notif = Notification(
                type=NotificationType.MACRO_RELEASE,
                title=name,
                description=f"**{name}** updated: {last} → {value} (as of {date})",
                data={"series_id": series_id, "old_value": last, "new_value": value, "date": date},
                urgency="medium",
            )
            notifications.append(notif)

    return notifications
