"""Request classifier for model routing."""

import re
from ai.models import ModelConfig, HAIKU, SONNET, OPUS, TIER_ROUTINE, TIER_STANDARD, TIER_DEEP
from config.settings import settings

# Track daily Opus usage
_opus_calls_today: int = 0
_opus_date: str = ""


def _check_opus_budget() -> bool:
    """Check if we're within the daily Opus budget."""
    import datetime
    global _opus_calls_today, _opus_date
    today = datetime.date.today().isoformat()
    if today != _opus_date:
        _opus_calls_today = 0
        _opus_date = today
    return _opus_calls_today < settings.opus_daily_budget


def record_opus_call() -> None:
    """Record an Opus call for budget tracking."""
    global _opus_calls_today
    _opus_calls_today += 1


def get_opus_usage() -> tuple[int, int]:
    """Return (used, limit) for Opus calls today."""
    return _opus_calls_today, settings.opus_daily_budget


# Keywords that indicate routine tasks (use Haiku)
ROUTINE_PATTERNS = [
    r"^(what is|what's) the (price|quote) of",
    r"^get (quote|price)",
    r"^(show|list) (watchlist|alerts)",
    r"classify|categorize|label",
    r"sentiment score",
]

# Keywords that indicate deep analysis (use Opus)
DEEP_PATTERNS = [
    r"deep (analysis|research|dive)",
    r"dcf|discounted cash flow",
    r"comprehensive (report|analysis)",
    r"compare .+ (vs|versus|and) .+",
    r"multi.*(document|report) analysis",
    r"investment thesis",
    r"risk assessment",
    r"synthesize|synthesis",
]

# Keywords that need at least Sonnet when user has a portfolio (not Haiku)
PORTFOLIO_UPGRADE_PATTERNS = [
    r"should i (buy|sell|hold|add|trim)",
    r"(buy|sell|hold) more",
    r"rebalance",
    r"allocation",
    r"tax loss harvest",
    r"what('?s| is) my portfolio",
    r"position siz",
    r"(add to|reduce|exit|close) (my )?(position|holding)",
    r"portfolio (risk|exposure|concentration)",
]


def route_request(
    content: str,
    force_tier: str | None = None,
    has_portfolio: bool = False,
) -> ModelConfig:
    """Route a request to the appropriate model tier.

    Args:
        content: The user's message/request content.
        force_tier: Override with 'haiku', 'sonnet', or 'opus'.
        has_portfolio: Whether the user has portfolio holdings (triggers smarter routing).

    Returns:
        The ModelConfig to use for this request.
    """
    if force_tier:
        mapping = {"haiku": HAIKU, "sonnet": SONNET, "opus": OPUS}
        return mapping.get(force_tier.lower(), SONNET)

    content_lower = content.lower()

    # Check for deep analysis triggers
    for pattern in DEEP_PATTERNS:
        if re.search(pattern, content_lower):
            if _check_opus_budget():
                return TIER_DEEP
            return TIER_STANDARD  # Fall back to Sonnet if over budget

    # Portfolio-aware upgrade: if user has holdings and asks about portfolio decisions,
    # use at minimum Sonnet (not Haiku) for better recommendations
    if has_portfolio:
        for pattern in PORTFOLIO_UPGRADE_PATTERNS:
            if re.search(pattern, content_lower):
                return TIER_STANDARD

    # Check for routine task triggers
    for pattern in ROUTINE_PATTERNS:
        if re.search(pattern, content_lower):
            return TIER_ROUTINE

    # Default to Sonnet for everything else
    return TIER_STANDARD
