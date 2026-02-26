"""Analyst rating/target change detection."""

import structlog
from typing import Any
from notifications.types import Notification
from config.constants import NotificationType

log = structlog.get_logger(__name__)

# Cache of last-known analyst state per symbol
_last_known: dict[str, dict[str, Any]] = {}


def process_analyst_data(
    symbol: str,
    analyst_data: dict[str, Any],
) -> list[Notification]:
    """Detect analyst rating changes and target price changes."""
    notifications = []

    upgrades = analyst_data.get("upgrades_downgrades", [])
    if not upgrades:
        return notifications

    last = _last_known.get(symbol, {})
    last_ids = last.get("upgrade_ids", set())

    for action in upgrades[:5]:
        # Create a simple ID from the action data
        action_id = f"{action.get('company', '')}:{action.get('gradeDate', '')}:{action.get('toGrade', '')}"
        if action_id in last_ids:
            continue

        from_grade = action.get("fromGrade", "N/A")
        to_grade = action.get("toGrade", "N/A")
        firm = action.get("company", "Unknown")
        action_type = action.get("action", "")

        is_upgrade = action_type.lower() in ("upgrade", "up")
        notif_type = NotificationType.ANALYST_UPGRADE if is_upgrade else NotificationType.ANALYST_DOWNGRADE

        notif = Notification(
            type=notif_type,
            title=f"{'Upgrade' if is_upgrade else 'Downgrade'} — {symbol}",
            description=f"{firm}: {from_grade} → {to_grade}",
            symbol=symbol,
            data={
                "firm": firm,
                "from_grade": from_grade,
                "to_grade": to_grade,
                "action": action_type,
                "date": action.get("gradeDate", ""),
            },
            urgency="high",
        )
        notifications.append(notif)

    # Update cache
    new_ids = {
        f"{a.get('company', '')}:{a.get('gradeDate', '')}:{a.get('toGrade', '')}"
        for a in upgrades[:10]
    }
    _last_known[symbol] = {"upgrade_ids": new_ids}

    # Check estimate changes (from FMP analyst estimates)
    estimates = analyst_data.get("estimates", [])
    if estimates:
        latest = estimates[0]
        current_target = latest.get("epsAvg") or latest.get("estimatedEpsAvg")
        last_target = last.get("est_eps_avg")

        if current_target and last_target and current_target != last_target:
            change_pct = ((current_target - last_target) / last_target) * 100
            if abs(change_pct) >= 5:  # Only notify for significant changes
                notif = Notification(
                    type=NotificationType.TARGET_PRICE_CHANGE,
                    title=f"Estimate Change — {symbol}",
                    description=f"Consensus EPS estimate moved from ${last_target:.2f} to ${current_target:.2f} ({change_pct:+.1f}%)",
                    symbol=symbol,
                    data={
                        "old_estimate": last_target,
                        "new_estimate": current_target,
                        "change_pct": change_pct,
                    },
                    urgency="medium",
                )
                notifications.append(notif)

        if current_target:
            _last_known.setdefault(symbol, {})["est_eps_avg"] = current_target

    return notifications
