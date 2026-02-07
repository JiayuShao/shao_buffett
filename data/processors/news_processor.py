"""News dedup, classification, and relevance scoring."""

import time
import structlog
from typing import Any
from notifications.types import Notification
from config.constants import NotificationType

log = structlog.get_logger(__name__)

# URL dedup with expiry — entries auto-expire so new articles aren't blocked forever
_seen_urls: dict[str, float] = {}  # url -> monotonic timestamp when first seen
_SEEN_TTL = 4 * 3600  # 4 hours (DB dedup covers 6 hours as a second layer)

# Throttle first-boot flood: only send articles from the last 2 hours on startup
_initialized = False
_BOOT_WINDOW = 2 * 3600  # seconds


def _prune_seen() -> None:
    """Remove expired URL entries to allow re-notification of updated stories."""
    now = time.monotonic()
    expired = [url for url, ts in _seen_urls.items() if now - ts > _SEEN_TTL]
    for url in expired:
        del _seen_urls[url]


def _parse_publish_time(article: dict[str, Any]) -> float | None:
    """Parse article publish time to a Unix timestamp."""
    published = article.get("published_at")
    if not published:
        return None
    # Finnhub returns Unix timestamps (int/float)
    if isinstance(published, (int, float)):
        return float(published)
    # MarketAux returns ISO strings
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(str(published).replace("Z", "+00:00"))
        return dt.timestamp()
    except (ValueError, TypeError):
        return None


def process_news_articles(
    articles: list[dict[str, Any]],
    watchlist_symbols: set[str],
) -> list[Notification]:
    """Process news articles into notifications.

    Filters for relevance, deduplicates (with time-based expiry), and creates
    notifications.  On first boot only articles from the last 2 hours are sent
    to avoid flooding with a week of backlog.
    """
    global _initialized

    _prune_seen()
    now_wall = time.time()
    now_mono = time.monotonic()
    notifications = []

    for article in articles:
        url = article.get("url", "")
        if not url:
            continue

        # URL dedup (expires after 4 hours so genuinely new articles get through)
        if url in _seen_urls:
            continue
        _seen_urls[url] = now_mono

        # On first boot, skip old articles to avoid flooding
        if not _initialized:
            pub_ts = _parse_publish_time(article)
            if pub_ts and (now_wall - pub_ts) > _BOOT_WINDOW:
                continue

        symbols = article.get("symbols", [])
        matched_symbols = [s for s in symbols if s in watchlist_symbols]
        sentiment = article.get("sentiment")

        # Only notify for watchlist-relevant or high-sentiment news
        if not matched_symbols and (sentiment is None or abs(sentiment) < 0.3):
            continue

        symbol = matched_symbols[0] if matched_symbols else None

        notif = Notification(
            type=NotificationType.BREAKING_NEWS,
            title=article.get("title", ""),
            description=article.get("description", article.get("snippet", "")),
            symbol=symbol,
            data={
                "source": article.get("source", ""),
                "url": url,
                "sentiment": sentiment,
                "symbols": symbols,
            },
            urgency="high" if (sentiment and abs(sentiment) > 0.5) else "medium",
        )
        notifications.append(notif)

    if not _initialized and notifications:
        log.info("first_boot_news", count=len(notifications))
    _initialized = True
    return notifications
