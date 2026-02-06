"""Constants used across the application."""

from enum import Enum


# Discord embed colors
class EmbedColor(int, Enum):
    SUCCESS = 0x00C853
    WARNING = 0xFFAB00
    ERROR = 0xFF1744
    INFO = 0x2979FF
    BULLISH = 0x00C853
    BEARISH = 0xFF1744
    NEUTRAL = 0x9E9E9E
    EARNINGS = 0x7C4DFF
    NEWS = 0x00B8D4
    ALERT = 0xFF6D00
    MACRO = 0x651FFF
    RESEARCH = 0x00BFA5


# Rate limits per API (requests per minute)
API_RATE_LIMITS = {
    "finnhub": 60,
    "fred": 120,
    "marketaux": 2,       # 100/day ≈ ~2/min conservative
    "fmp": 30,
    "sec_edgar": 10,      # 10 req/sec but we go conservative
    "arxiv": 10,
    "polymarket": 30,
}

# Polling intervals (seconds)
POLL_INTERVALS = {
    "news": 300,          # 5 min
    "analyst": 3600,      # 1 hour
    "earnings": 1800,     # 30 min
    "macro": 3600,        # 1 hour
    "sec_filings": 3600,  # 1 hour
    "insider": 3600,      # 1 hour
    "price_alerts": 30,   # 30 sec
}

# Cache TTLs (seconds)
CACHE_TTL = {
    "quote": 30,
    "profile": 86400,     # 1 day
    "fundamentals": 3600, # 1 hour
    "news": 300,          # 5 min
    "analyst": 3600,      # 1 hour
    "macro": 1800,        # 30 min
    "earnings": 1800,     # 30 min
    "transcript": 86400,  # 1 day
    "filing": 86400,      # 1 day
}

# Sectors
SECTORS = [
    "Technology",
    "Healthcare",
    "Financial Services",
    "Consumer Cyclical",
    "Communication Services",
    "Industrials",
    "Consumer Defensive",
    "Energy",
    "Utilities",
    "Real Estate",
    "Basic Materials",
]

# Focused metrics options
METRIC_OPTIONS = [
    "pe_ratio",
    "forward_pe",
    "eps",
    "eps_growth",
    "revenue_growth",
    "profit_margin",
    "operating_margin",
    "roe",
    "debt_to_equity",
    "free_cash_flow",
    "dividend_yield",
    "beta",
    "market_cap",
    "price_to_book",
    "price_to_sales",
    "current_ratio",
]

# Notification types
class NotificationType(str, Enum):
    PRICE_ALERT = "price_alert"
    BREAKING_NEWS = "breaking_news"
    ANALYST_UPGRADE = "analyst_upgrade"
    ANALYST_DOWNGRADE = "analyst_downgrade"
    TARGET_PRICE_CHANGE = "target_price_change"
    EARNINGS_SURPRISE = "earnings_surprise"
    MACRO_RELEASE = "macro_release"
    INSIDER_TRADE = "insider_trade"
    SEC_FILING = "sec_filing"
    EARNINGS_TRANSCRIPT = "earnings_transcript"
    RESEARCH_DIGEST = "research_digest"
    MORNING_BRIEFING = "morning_briefing"
    EVENING_SUMMARY = "evening_summary"
    PROACTIVE_INSIGHT = "proactive_insight"

# Risk tolerance
class RiskTolerance(str, Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"

# Max limits
MAX_WATCHLIST_SIZE = 50
MAX_ALERTS_PER_USER = 25
MAX_CONVERSATION_HISTORY = 20
MAX_EMBED_DESCRIPTION = 4096
MAX_EMBED_FIELD_VALUE = 1024
