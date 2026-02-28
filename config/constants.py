"""Constants used across the application."""

import re
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
    AI_NEWS = 0x7B1FA2


# Rate limits per API (requests per minute)
API_RATE_LIMITS = {
    "finnhub": 55,        # Free tier allows 60/min — leave slim headroom
    "fred": 120,
    "marketaux": 5,       # Basic plan: 250/day — batched calls keep usage low
    "fmp": 30,
    "sec_edgar": 10,      # 10 req/sec but we go conservative
    "arxiv": 10,
}

# Polling intervals (seconds)
POLL_INTERVALS = {
    "news": 180,          # 3 min (falls back to Finnhub when MarketAux exhausted)
    "analyst": 7200,      # 2 hours
    "earnings": 1800,     # 30 min
    "macro": 3600,        # 1 hour
    "sec_filings": 3600,  # 1 hour
    "insider": 3600,      # 1 hour
    "price_alerts": 60,   # 60 sec (quotes now via FMP)
}

# Cache TTLs (seconds)
CACHE_TTL = {
    "quote": 60,          # 1 min (FMP-sourced now)
    "profile": 86400,     # 1 day
    "fundamentals": 3600, # 1 hour
    "news": 120,          # 2 min (polls every 3 min, fresh data most cycles)
    "analyst": 7200,      # 2 hours
    "macro": 1800,        # 30 min
    "earnings": 3600,     # 1 hour
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
MAX_AI_NEWS_PER_USER = 3

# AI/tech news keyword matching
AI_NEWS_KEYWORDS = [
    # Companies
    "OpenAI", "Anthropic", "DeepMind", "Google AI", "Meta AI", "Microsoft AI",
    "Nvidia", "xAI", "Mistral", "Cohere", "Stability AI", "Hugging Face",
    "Perplexity", "Inflection", "Character AI",
    # Technical terms
    "LLM", "large language model", "GPT", "transformer", "foundation model",
    "generative AI", "gen AI", "neural network", "deep learning",
    "machine learning", "natural language processing", "NLP",
    "computer vision", "reinforcement learning",
    # Domain terms
    "AI safety", "AI regulation", "AI chip", "AI accelerator",
    "artificial intelligence", "AGI", "AI model", "AI startup",
    "AI agent", "multimodal AI",
]
_AI_NEWS_RE = re.compile(
    "|".join(re.escape(kw) for kw in AI_NEWS_KEYWORDS),
    re.IGNORECASE,
)


def is_ai_related(text: str) -> bool:
    """Check if text contains AI/tech keywords."""
    return bool(_AI_NEWS_RE.search(text))
