"""Request classifier for model routing."""

import datetime
import re
from ai.models import ModelConfig, HAIKU, SONNET, OPUS, TIER_ROUTINE, TIER_STANDARD, TIER_DEEP
from config.settings import settings


# ── Opus daily budget tracker ──

class _OpusBudget:
    """Track daily Opus usage with proper reset logic."""

    def __init__(self) -> None:
        self._calls: int = 0
        self._date: str = ""

    def check(self, limit: int) -> bool:
        today = datetime.date.today().isoformat()
        if today != self._date:
            self._calls = 0
            self._date = today
        return self._calls < limit

    def record(self) -> None:
        self._calls += 1

    def usage(self, limit: int) -> tuple[int, int]:
        return self._calls, limit


_opus_budget = _OpusBudget()


def record_opus_call() -> None:
    """Record an Opus call for budget tracking."""
    _opus_budget.record()


def get_opus_usage() -> tuple[int, int]:
    """Return (used, limit) for Opus calls today."""
    return _opus_budget.usage(settings.opus_daily_budget)


# ── Pre-compiled routing patterns ──

# Keywords that indicate routine tasks (use Haiku)
ROUTINE_PATTERNS = [
    r"^(what is|what's) the (price|quote) of",
    r"^get (quote|price)",
    r"^(show|list) (watchlist|alerts)",
    r"classify|categorize|label",
    r"sentiment score",
    r"show.*news|latest news",
    r"what.*(trending|hot)",
    r"any (updates|news)",
    r"how (is|are) .*doing",
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
    r"deep dive",
    r"thorough analysis",
    r"in.depth",
    r"research.*report",
    r"detailed breakdown",
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
    r"what if i (buy|sell|invest)",
    r"tax.*(implication|consequence|impact)",
    r"risk.*(reward|return) ratio",
]

# Pre-compile all patterns once at module load (~10x faster matching)
_DEEP_RE = [re.compile(p) for p in DEEP_PATTERNS]
_PORTFOLIO_RE = [re.compile(p) for p in PORTFOLIO_UPGRADE_PATTERNS]
_ROUTINE_RE = [re.compile(p) for p in ROUTINE_PATTERNS]


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
    for pat in _DEEP_RE:
        if pat.search(content_lower):
            if _opus_budget.check(settings.opus_daily_budget):
                return TIER_DEEP
            return TIER_STANDARD  # Fall back to Sonnet if over budget

    # Portfolio-aware upgrade: if user has holdings and asks about portfolio decisions,
    # use at minimum Sonnet (not Haiku) for better recommendations
    if has_portfolio:
        for pat in _PORTFOLIO_RE:
            if pat.search(content_lower):
                return TIER_STANDARD

    # Check for routine task triggers
    for pat in _ROUTINE_RE:
        if pat.search(content_lower):
            return TIER_ROUTINE

    # Default to Sonnet for everything else
    return TIER_STANDARD
