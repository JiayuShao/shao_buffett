"""Proactive insight generator — anticipates user needs."""

import hashlib
import json
import structlog
from typing import Any
from data.manager import DataManager
from storage.repositories.portfolio_repo import PortfolioRepository
from storage.repositories.notes_repo import NotesRepository
from storage.repositories.activity_repo import ActivityRepository, ProactiveInsightRepository
from storage.repositories.watchlist_repo import WatchlistRepository
from storage.repositories.user_repo import UserRepository
from notifications.dispatcher import NotificationDispatcher
from notifications.types import Notification
from config.constants import NotificationType

log = structlog.get_logger(__name__)

# Thresholds
SIGNIFICANT_MOVE_PCT = 3.0  # >3% daily move triggers alert
POLYMARKET_MIN_VOLUME = 50_000
POLYMARKET_HIGH_VOLUME = 100_000
POLYMARKET_EXTREME_HIGH = 0.85
POLYMARKET_EXTREME_LOW = 0.15
NEWS_STRONG_SENTIMENT = 0.4
MAX_NEWS_INSIGHTS_PER_USER = 3

# Maps user interests to Polymarket search queries
INTEREST_POLYMARKET_QUERIES: dict[str, list[str]] = {
    "Technology": ["tech stocks", "technology"],
    "AI": ["artificial intelligence", "AI"],
    "Space": ["space", "SpaceX"],
    "Semiconductor": ["semiconductor", "chips"],
    "Energy": ["energy", "oil"],
    "Robotics": ["robotics", "automation"],
    "Crypto": ["bitcoin", "crypto"],
    "Healthcare": ["healthcare", "pharma"],
    "Finance": ["banking", "interest rates"],
    "EV": ["electric vehicles", "EV"],
}

# Maps user interests to MarketAux industry parameter values
INTEREST_MARKETAUX_SECTORS: dict[str, str] = {
    "Technology": "Technology",
    "AI": "Technology",
    "Semiconductor": "Technology",
    "Robotics": "Technology",
    "Space": "Industrials",
    "Energy": "Energy",
    "Healthcare": "Healthcare",
    "Finance": "Financial",
    "EV": "Consumer Cyclical",
    "Crypto": "Financial",
}


def _content_hash(value: str) -> str:
    """Create a 16-char hex hash for dedup."""
    return hashlib.sha256(value.encode()).hexdigest()[:16]


class ProactiveInsightGenerator:
    """Cross-references user data with market data to generate proactive insights."""

    def __init__(
        self,
        db_pool: Any,
        data_manager: DataManager,
        dispatcher: NotificationDispatcher,
    ) -> None:
        self.pool = db_pool
        self.dm = data_manager
        self.dispatcher = dispatcher
        self.portfolio_repo = PortfolioRepository(db_pool)
        self.notes_repo = NotesRepository(db_pool)
        self.activity_repo = ActivityRepository(db_pool)
        self.insight_repo = ProactiveInsightRepository(db_pool)
        self.watchlist_repo = WatchlistRepository(db_pool)
        self.user_repo = UserRepository(db_pool)
        self._sector_news_cache: dict[str, list[dict]] = {}

    async def generate_all(self) -> int:
        """Generate proactive insights for all users. Returns count of insights created."""
        portfolio_users = await self.portfolio_repo.get_all_users_with_holdings()
        watchlist_users = await self.watchlist_repo.get_all_users_with_watchlist()
        portfolio_set = set(portfolio_users)
        all_user_ids = list(dict.fromkeys(portfolio_users + watchlist_users))

        # Pre-fetch sector news for all users (rate-limit friendly)
        await self._prefetch_sector_news(all_user_ids)

        total = 0
        for user_id in portfolio_users:
            try:
                count = await self._generate_for_user(user_id)
                total += count
            except Exception as e:
                log.error("proactive_user_error", user_id=user_id, error=str(e))

        # Also process watchlist-only users (not already covered by portfolio)
        for user_id in watchlist_users:
            if user_id in portfolio_set:
                continue
            try:
                count = await self._generate_for_user(user_id)
                total += count
            except Exception as e:
                log.error("proactive_user_error", user_id=user_id, error=str(e))

        # Clear cache after cycle
        self._sector_news_cache.clear()
        return total

    async def _prefetch_sector_news(self, user_ids: list[int]) -> None:
        """Batch-fetch MarketAux news for all unique sectors needed across users."""
        needed_sectors: set[str] = set()
        for user_id in user_ids:
            try:
                profile = await self.user_repo.get_or_create(user_id)
                interests = profile.get("interests") or {}
                if isinstance(interests, str):
                    interests = json.loads(interests)
                categories = interests.get("categories", [])
                for cat in categories:
                    sector = INTEREST_MARKETAUX_SECTORS.get(cat)
                    if sector:
                        needed_sectors.add(sector)
            except Exception as e:
                log.debug("prefetch_profile_error", user_id=user_id, error=str(e))

        for sector in needed_sectors:
            try:
                articles = await self.dm.get_news_for_sectors(sector, limit=10)
                self._sector_news_cache[sector] = articles
                log.debug("prefetched_sector_news", sector=sector, count=len(articles))
            except Exception as e:
                log.debug("prefetch_news_error", sector=sector, error=str(e))

    async def _generate_for_user(self, user_id: int) -> int:
        """Generate insights for a specific user."""
        count = 0
        holdings = await self.portfolio_repo.get_holdings(user_id)
        held_symbols = [h["symbol"] for h in holdings]
        watchlist_symbols = await self.watchlist_repo.get(user_id)

        # Merge portfolio + watchlist symbols (deduplicated, preserving order)
        all_symbols = list(dict.fromkeys(held_symbols + watchlist_symbols))

        # Get user interests
        interests: list[str] = []
        try:
            profile = await self.user_repo.get_or_create(user_id)
            raw_interests = profile.get("interests") or {}
            if isinstance(raw_interests, str):
                raw_interests = json.loads(raw_interests)
            interests = raw_interests.get("categories", [])
        except Exception as e:
            log.debug("user_interests_error", user_id=user_id, error=str(e))

        if not all_symbols and not interests:
            return 0

        # Check for significant price movements on held/watched positions
        if all_symbols:
            count += await self._check_price_movements(user_id, all_symbols)
            count += await self._check_upcoming_earnings(user_id, all_symbols)
            count += await self._suggest_watchlist_additions(user_id, held_symbols)

        # Check for stale action items
        count += await self._check_stale_action_items(user_id)

        # Cross-reference with Polymarket and sector news
        if interests:
            count += await self._check_polymarket_signals(user_id, interests, all_symbols)
            count += await self._check_interest_news(user_id, interests, all_symbols)

        return count

    async def _check_price_movements(self, user_id: int, symbols: list[str]) -> int:
        """Check for significant price moves on tracked positions."""
        count = 0
        for symbol in symbols:
            try:
                quote = await self.dm.get_quote(symbol)
                change_pct = quote.get("dp", quote.get("change_percent", 0))
                if change_pct is None:
                    continue
                change_pct = float(change_pct)

                if abs(change_pct) >= SIGNIFICANT_MOVE_PCT:
                    direction = "up" if change_pct > 0 else "down"
                    price = quote.get("c", quote.get("price", 0))
                    await self.insight_repo.create(
                        discord_id=user_id,
                        insight_type="price_movement",
                        title=f"{symbol} moved {change_pct:+.1f}% today",
                        content=f"**{symbol}** is {direction} **{change_pct:+.1f}%** today (${price:.2f}). This is a significant move worth monitoring.",
                        symbols=[symbol],
                    )
                    count += 1
            except Exception as e:
                log.debug("price_check_error", symbol=symbol, error=str(e))
        return count

    async def _check_upcoming_earnings(self, user_id: int, symbols: list[str]) -> int:
        """Check for upcoming earnings on held stocks."""
        count = 0
        for symbol in symbols:
            try:
                earnings = await self.dm.get_earnings(symbol)
                if not earnings:
                    continue
                # Check if there's an upcoming earnings date
                latest = earnings[0] if isinstance(earnings, list) and earnings else None
                if latest and latest.get("date"):
                    from datetime import datetime, timedelta
                    try:
                        earn_date = datetime.fromisoformat(str(latest["date"]).replace("Z", "+00:00"))
                        now = datetime.utcnow()
                        days_until = (earn_date.replace(tzinfo=None) - now).days
                        if 0 < days_until <= 7:
                            await self.insight_repo.create(
                                discord_id=user_id,
                                insight_type="earnings_upcoming",
                                title=f"{symbol} earnings in {days_until} day(s)",
                                content=f"**{symbol}** reports earnings in **{days_until} day(s)**. Consider reviewing your position and setting expectations.",
                                symbols=[symbol],
                            )
                            count += 1
                    except (ValueError, TypeError):
                        pass
            except Exception as e:
                log.debug("earnings_check_error", symbol=symbol, error=str(e))
        return count

    async def _suggest_watchlist_additions(self, user_id: int, held_symbols: list[str]) -> int:
        """Suggest adding frequently queried symbols to watchlist."""
        count = 0
        freq = await self.activity_repo.get_frequently_queried_symbols(user_id, days=14, limit=5)
        watchlist = await self.watchlist_repo.get(user_id)
        tracked = set(held_symbols) | set(watchlist)

        for entry in freq:
            symbol = entry["symbol"]
            query_count = entry["query_count"]
            if symbol not in tracked and query_count >= 3:
                await self.insight_repo.create(
                    discord_id=user_id,
                    insight_type="symbol_suggestion",
                    title=f"You frequently ask about {symbol}",
                    content=f"You've asked about **{symbol}** {query_count} times recently but it's not in your watchlist or portfolio. Want to add it to your watchlist?",
                    symbols=[symbol],
                )
                count += 1
        return count

    async def _check_stale_action_items(self, user_id: int) -> int:
        """Remind about old unresolved action items."""
        count = 0
        items = await self.notes_repo.get_active_action_items(user_id)
        from datetime import datetime, timedelta
        now = datetime.utcnow()

        for item in items:
            created = item["created_at"].replace(tzinfo=None)
            days_old = (now - created).days
            if days_old >= 3:
                symbols = item.get("symbols", [])
                await self.insight_repo.create(
                    discord_id=user_id,
                    insight_type="action_reminder",
                    title=f"Action item pending ({days_old} days)",
                    content=f"Reminder: {item['content']} (noted {days_old} days ago)",
                    symbols=symbols if symbols else [],
                )
                count += 1
        return count

    async def _check_polymarket_signals(
        self, user_id: int, interests: list[str], symbols: list[str]
    ) -> int:
        """Check Polymarket for meaningful prediction markets matching user interests."""
        count = 0
        queries: list[str] = []

        # Build queries from interests
        for interest in interests:
            queries.extend(INTEREST_POLYMARKET_QUERIES.get(interest, []))

        # Add top watchlist symbols (limit to 5)
        for symbol in symbols[:5]:
            queries.append(symbol)

        # Deduplicate queries
        queries = list(dict.fromkeys(queries))

        for query in queries:
            try:
                markets = await self.dm.get_polymarket(query, limit=3)
                for market in markets:
                    if not self._is_meaningful_polymarket(market):
                        continue

                    slug = market.get("slug", "")
                    ch = _content_hash(slug)
                    if await self.insight_repo.was_recently_created(
                        user_id, "polymarket_signal", ch
                    ):
                        continue

                    probability = self._format_polymarket_probability(market)
                    volume = float(market.get("volume", 0))
                    question = market.get("question", "Unknown market")
                    link = f"https://polymarket.com/event/{slug}" if slug else ""

                    content = f"**{question}**\n{probability}\nVolume: ${volume:,.0f}"
                    if link:
                        content += f"\n[View on Polymarket]({link})"

                    await self.insight_repo.create(
                        discord_id=user_id,
                        insight_type="polymarket_signal",
                        title=f"Prediction: {question[:80]}",
                        content=content,
                        content_hash=ch,
                    )
                    count += 1
            except Exception as e:
                log.debug("polymarket_check_error", query=query, error=str(e))

        return count

    @staticmethod
    def _is_meaningful_polymarket(market: dict) -> bool:
        """Filter for markets with sufficient volume and interesting probabilities."""
        volume = float(market.get("volume", 0))
        if volume < POLYMARKET_MIN_VOLUME:
            return False

        # High volume alone is interesting
        if volume >= POLYMARKET_HIGH_VOLUME:
            return True

        # Otherwise require extreme probability
        try:
            prices = json.loads(market.get("outcome_prices", "[]"))
            for p in prices:
                p_val = float(p)
                if p_val >= POLYMARKET_EXTREME_HIGH or p_val <= POLYMARKET_EXTREME_LOW:
                    return True
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

        return False

    @staticmethod
    def _format_polymarket_probability(market: dict) -> str:
        """Format outcome prices for display."""
        try:
            prices = json.loads(market.get("outcome_prices", "[]"))
            outcomes = json.loads(market.get("outcomes", "[]"))
            parts = []
            for outcome, price in zip(outcomes, prices):
                pct = float(price) * 100
                parts.append(f"{outcome}: {pct:.0f}%")
            return " | ".join(parts)
        except (json.JSONDecodeError, ValueError, TypeError):
            return ""

    async def _check_interest_news(
        self, user_id: int, interests: list[str], symbols: list[str]
    ) -> int:
        """Check pre-fetched sector news for strong-sentiment articles relevant to user interests."""
        count = 0
        tracked_symbols = set(symbols)

        # Collect articles from pre-fetched cache
        seen_urls: set[str] = set()
        candidates: list[dict] = []

        for interest in interests:
            sector = INTEREST_MARKETAUX_SECTORS.get(interest)
            if not sector:
                continue
            articles = self._sector_news_cache.get(sector, [])
            for article in articles:
                url = article.get("url", "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                candidates.append(article)

        for article in candidates:
            if count >= MAX_NEWS_INSIGHTS_PER_USER:
                break

            # Skip weak sentiment
            sentiment = article.get("sentiment")
            if sentiment is None or abs(sentiment) < NEWS_STRONG_SENTIMENT:
                continue

            # Skip if article only mentions symbols already tracked by price_movements
            article_symbols = set(article.get("symbols", []))
            if article_symbols and article_symbols.issubset(tracked_symbols):
                continue

            url = article.get("url", "")
            ch = _content_hash(url)
            try:
                if await self.insight_repo.was_recently_created(
                    user_id, "news_relevant", ch
                ):
                    continue

                title = article.get("title", "Untitled")
                source = article.get("source", "")
                sentiment_label = "Bullish" if sentiment > 0 else "Bearish"
                content = f"**{title}**\nSentiment: {sentiment_label} ({sentiment:+.2f})"
                if source:
                    content += f"\nSource: {source}"
                if url:
                    content += f"\n[Read more]({url})"

                await self.insight_repo.create(
                    discord_id=user_id,
                    insight_type="news_relevant",
                    title=f"{sentiment_label} news: {title[:80]}",
                    content=content,
                    content_hash=ch,
                )
                count += 1
            except Exception as e:
                log.debug("interest_news_error", url=url, error=str(e))

        return count

    async def dispatch_pending(self) -> int:
        """Dispatch all undelivered insights as notifications."""
        portfolio_users = await self.portfolio_repo.get_all_users_with_holdings()
        watchlist_users = await self.watchlist_repo.get_all_users_with_watchlist()
        users = list(dict.fromkeys(portfolio_users + watchlist_users))
        sent = 0

        for user_id in users:
            insights = await self.insight_repo.get_undelivered(user_id)
            for insight in insights:
                notif = Notification(
                    type=NotificationType.PROACTIVE_INSIGHT,
                    title=insight["title"],
                    description=insight["content"],
                    symbol=insight["symbols"][0] if insight["symbols"] else None,
                    target_users=[user_id],
                    data={"insight_type": insight["insight_type"], "symbols": insight["symbols"]},
                    urgency="medium",
                )
                delivered = await self.dispatcher.dispatch(notif)
                if delivered > 0:
                    await self.insight_repo.mark_delivered(insight["id"])
                    sent += 1

        return sent
