"""Number/currency formatting and ticker validation."""

import re

_TICKER_PATTERN = re.compile(r"^[A-Z]{1,5}$")


def validate_ticker(symbol: str) -> str | None:
    """Validate and normalize a stock ticker symbol. Returns None if invalid."""
    symbol = symbol.upper().strip()
    if _TICKER_PATTERN.match(symbol):
        return symbol
    return None


def format_currency(value: float | int | None, decimals: int = 2) -> str:
    """Format a number as currency."""
    if value is None:
        return "N/A"
    if abs(value) >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.{decimals}f}T"
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.{decimals}f}B"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.{decimals}f}M"
    return f"${value:,.{decimals}f}"


def format_number(value: float | int | None, decimals: int = 2) -> str:
    """Format a number with commas."""
    if value is None:
        return "N/A"
    return f"{value:,.{decimals}f}"


def format_percent(value: float | None, decimals: int = 2) -> str:
    """Format a number as a percentage."""
    if value is None:
        return "N/A"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{decimals}f}%"


def format_change(value: float | None, decimals: int = 2) -> str:
    """Format a price change with sign and color emoji."""
    if value is None:
        return "N/A"
    sign = "+" if value > 0 else ""
    emoji = "🟢" if value > 0 else "🔴" if value < 0 else "⚪"
    return f"{emoji} {sign}{value:.{decimals}f}"


def format_large_number(value: float | int | None) -> str:
    """Format large numbers with K/M/B/T suffixes."""
    if value is None:
        return "N/A"
    if abs(value) >= 1_000_000_000_000:
        return f"{value / 1_000_000_000_000:.1f}T"
    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.1f}K"
    return str(value)


def truncate(text: str, max_length: int = 1024) -> str:
    """Truncate text to max_length, adding ellipsis if needed."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
