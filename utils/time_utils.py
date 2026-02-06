"""Market hours and timezone handling."""

from datetime import datetime, time, timezone, timedelta

ET = timezone(timedelta(hours=-5))  # Eastern Time (approximate; DST not handled)
UTC = timezone.utc

MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)

# US market holidays are not exhaustive; check a calendar for completeness
US_MARKET_HOLIDAYS_2025 = {
    datetime(2025, 1, 1).date(),   # New Year's Day
    datetime(2025, 1, 20).date(),  # MLK Day
    datetime(2025, 2, 17).date(),  # Presidents' Day
    datetime(2025, 4, 18).date(),  # Good Friday
    datetime(2025, 5, 26).date(),  # Memorial Day
    datetime(2025, 6, 19).date(),  # Juneteenth
    datetime(2025, 7, 4).date(),   # Independence Day
    datetime(2025, 9, 1).date(),   # Labor Day
    datetime(2025, 11, 27).date(), # Thanksgiving
    datetime(2025, 12, 25).date(), # Christmas
}


def now_et() -> datetime:
    """Get current time in Eastern Time."""
    return datetime.now(ET)


def is_market_open() -> bool:
    """Check if US stock market is currently open."""
    now = now_et()
    # Weekend
    if now.weekday() >= 5:
        return False
    # Holiday
    if now.date() in US_MARKET_HOLIDAYS_2025:
        return False
    # Market hours
    current_time = now.time()
    return MARKET_OPEN <= current_time <= MARKET_CLOSE


def time_until_market_open() -> timedelta | None:
    """Time until next market open. None if market is open."""
    if is_market_open():
        return None

    now = now_et()
    # Find next trading day
    target = now.replace(hour=9, minute=30, second=0, microsecond=0)

    if now.time() > MARKET_CLOSE or now.weekday() >= 5:
        target += timedelta(days=1)

    while target.weekday() >= 5 or target.date() in US_MARKET_HOLIDAYS_2025:
        target += timedelta(days=1)

    return target - now


def format_timestamp(dt: datetime | None) -> str:
    """Format a datetime for display."""
    if dt is None:
        return "N/A"
    return dt.strftime("%b %d, %Y %I:%M %p ET")


def relative_time(dt: datetime) -> str:
    """Get a human-readable relative time string."""
    now = datetime.now(UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    diff = now - dt

    seconds = int(diff.total_seconds())
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        mins = seconds // 60
        return f"{mins}m ago"
    if seconds < 86400:
        hours = seconds // 3600
        return f"{hours}h ago"
    days = seconds // 86400
    return f"{days}d ago"
