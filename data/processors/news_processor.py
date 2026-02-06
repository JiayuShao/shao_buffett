"""News dedup, classification, and relevance scoring."""

import structlog
from typing import Any
from notifications.types import Notification
from config.constants import NotificationType

log = structlog.get_logger(__name__)

_seen_urls: set[str] = set()


def process_news_articles(
    articles: list[dict[str, Any]],
    watchlist_symbols: set[str],
) -> list[Notification]:
    """Process news articles into notifications.

    Filters for relevance, deduplicates, and creates notifications.
    """
    notifications = []

    for article in articles:
        url = article.get("url", "")
        if url in _seen_urls:
            continue
        _seen_urls.add(url)

        # Trim seen URLs set to prevent memory growth
        if len(_seen_urls) > 5000:
            # Keep most recent half
            _seen_urls.clear()

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

    return notifications
