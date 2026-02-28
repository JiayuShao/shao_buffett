"""Proactive insight generator — anticipates user needs."""

import asyncio
import hashlib
import json
import structlog
from datetime import UTC, datetime
import asyncpg
from ai.engine import AIEngine
from data.manager import DataManager
from storage.repositories.portfolio_repo import PortfolioRepository
from storage.repositories.notes_repo import NotesRepository
from storage.repositories.activity_repo import ActivityRepository, ProactiveInsightRepository
from storage.repositories.watchlist_repo import WatchlistRepository
from storage.repositories.user_repo import UserRepository
from notifications.dispatcher import NotificationDispatcher
from notifications.types import Notification
from config.constants import NotificationType, is_ai_related, MAX_AI_NEWS_PER_USER

log = structlog.get_logger(__name__)

# Thresholds
SIGNIFICANT_MOVE_PCT = 3.0  # >3% daily move triggers alert
NEWS_STRONG_SENTIMENT = 0.4
MAX_NEWS_INSIGHTS_PER_USER = 3
INSIDER_SIGNIFICANT_VALUE = 500_000  # $500K+ insider transactions

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
        db_pool: asyncpg.Pool,
        data_manager: DataManager,
        dispatcher: NotificationDispatcher,
        ai_engine: AIEngine | None = None,
    ) -> None:
        self.pool = db_pool
        self.dm = data_manager
        self.dispatcher = dispatcher
        self.ai_engine = ai_engine
        self.portfolio_repo = PortfolioRepository(db_pool)
        self.notes_repo = NotesRepository(db_pool)
        self.activity_repo = ActivityRepository(db_pool)
        self.insight_repo = ProactiveInsightRepository(db_pool)
        self.watchlist_repo = WatchlistRepository(db_pool)
        self.user_repo = UserRepository(db_pool)
        self._sector_news_cache: dict[str, list[dict]] = {}
        self._ai_news_cache: dict | None = None

    async def generate_all(self) -> int:
        """Generate proactive insights for all users. Returns count of insights created."""
        portfolio_users = await self.portfolio_repo.get_all_users_with_holdings()
        watchlist_users = await self.watchlist_repo.get_all_users_with_watchlist()
        portfolio_set = set(portfolio_users)
        all_user_ids = list(dict.fromkeys(portfolio_users + watchlist_users))

        # Pre-fetch sector news and AI news for all users (rate-limit friendly)
        await self._prefetch_sector_news(all_user_ids)
        await self._prefetch_ai_news()

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

        # Clear caches after cycle
        self._sector_news_cache.clear()
        self._ai_news_cache = None
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

        async def _fetch_sector(sector: str) -> None:
            try:
                articles = await self.dm.get_news_for_sectors(sector, limit=10)
                self._sector_news_cache[sector] = articles
                log.debug("prefetched_sector_news", sector=sector, count=len(articles))
            except Exception as e:
                log.debug("prefetch_news_error", sector=sector, error=str(e))

        async with asyncio.TaskGroup() as tg:
            for sector in needed_sectors:
                tg.create_task(_fetch_sector(sector))

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

        # Run all independent checks concurrently
        check_coros = []
        if all_symbols:
            check_coros.extend([
                self._check_price_movements(user_id, all_symbols),
                self._check_upcoming_earnings(user_id, all_symbols),
                self._check_earnings_calendar_week(user_id, all_symbols),
                self._check_insider_trades(user_id, all_symbols),
                self._auto_analyze_recent_earnings(user_id, all_symbols),
                self._suggest_watchlist_additions(user_id, held_symbols),
            ])
        check_coros.append(self._check_stale_action_items(user_id))
        check_coros.append(self._check_ai_news(user_id))
        if interests:
            check_coros.append(self._check_interest_news(user_id, interests, all_symbols))

        results = await asyncio.gather(*check_coros, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                log.error("proactive_check_error", user_id=user_id, error=str(r))
            else:
                count += r

        return count

    async def _check_price_movements(self, user_id: int, symbols: list[str]) -> int:
        """Check for significant price moves on tracked positions."""
        # Fetch all quotes in parallel
        results = await asyncio.gather(
            *(self.dm.get_quote(sym) for sym in symbols),
            return_exceptions=True,
        )

        count = 0
        for symbol, result in zip(symbols, results):
            if isinstance(result, Exception):
                log.debug("price_check_error", symbol=symbol, error=str(result))
                continue
            quote = result
            change_pct = quote.get("dp", quote.get("change_percent", quote.get("changesPercentage", 0)))
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
        return count

    async def _check_upcoming_earnings(self, user_id: int, symbols: list[str]) -> int:
        """Check for upcoming earnings on held stocks."""
        count = 0
        for symbol in symbols:
            try:
                earnings = await self.dm.get_earnings(symbol)
                if not earnings:
                    continue
                latest = earnings[0] if isinstance(earnings, list) and earnings else None
                if latest and latest.get("date"):
                    try:
                        earn_date = datetime.fromisoformat(str(latest["date"]).replace("Z", "+00:00"))
                        now = datetime.now(UTC)
                        days_until = (earn_date.replace(tzinfo=None) - now.replace(tzinfo=None)).days
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

    async def _check_earnings_calendar_week(self, user_id: int, symbols: list[str]) -> int:
        """Generate a weekly earnings calendar alert if multiple holdings report this week."""
        reporting_this_week = []
        now = datetime.now(UTC)

        for symbol in symbols:
            try:
                earnings = await self.dm.get_earnings(symbol)
                if not earnings or not isinstance(earnings, list):
                    continue
                latest = earnings[0]
                if latest and latest.get("date"):
                    try:
                        earn_date = datetime.fromisoformat(str(latest["date"]).replace("Z", "+00:00"))
                        days_until = (earn_date.replace(tzinfo=None) - now.replace(tzinfo=None)).days
                        if 0 < days_until <= 7:
                            day_name = earn_date.strftime("%A")
                            reporting_this_week.append((symbol, days_until, day_name))
                    except (ValueError, TypeError):
                        pass
            except Exception:
                pass

        if len(reporting_this_week) >= 2:
            ch = _content_hash(f"earnings_week_{now.isocalendar()[1]}_{','.join(s[0] for s in reporting_this_week)}")
            if await self.insight_repo.was_recently_created(user_id, "earnings_calendar", ch):
                return 0

            lines = [f"- **{sym}** ({day}, {d}d away)" for sym, d, day in sorted(reporting_this_week, key=lambda x: x[1])]
            content = (
                f"**{len(reporting_this_week)} of your holdings report earnings this week:**\n"
                + "\n".join(lines)
                + "\n\nConsider reviewing your exposure and setting expectations."
            )
            await self.insight_repo.create(
                discord_id=user_id,
                insight_type="earnings_calendar",
                title=f"{len(reporting_this_week)} holdings report earnings this week",
                content=content,
                symbols=[s[0] for s in reporting_this_week],
                content_hash=ch,
            )
            return 1
        return 0

    async def _check_insider_trades(self, user_id: int, symbols: list[str]) -> int:
        """Check for significant insider transactions on held stocks."""
        count = 0
        for symbol in symbols[:10]:  # Cap to avoid rate limits
            try:
                data = await self.dm.get_insider_transactions(symbol)
                if not data:
                    continue

                transactions = data.get("data", []) if isinstance(data, dict) else data
                if not isinstance(transactions, list):
                    continue

                for txn in transactions[:5]:
                    value = abs(float(txn.get("transactionValue", 0) or 0))
                    if value < INSIDER_SIGNIFICANT_VALUE:
                        continue

                    name = txn.get("name", "Insider")
                    txn_type = txn.get("transactionType", "").lower()
                    shares = txn.get("share", 0)
                    filing_date = txn.get("filingDate", "")

                    action = "sold" if "sale" in txn_type or "sell" in txn_type else "bought"
                    ch = _content_hash(f"{symbol}_{name}_{filing_date}_{value}")

                    if await self.insight_repo.was_recently_created(user_id, "insider_trade", ch):
                        continue

                    content = (
                        f"**{name}** {action} {abs(shares):,.0f} shares of **{symbol}** "
                        f"(${value:,.0f}) on {filing_date}."
                    )
                    await self.insight_repo.create(
                        discord_id=user_id,
                        insight_type="insider_trade",
                        title=f"{symbol}: {name} {action} ${value:,.0f}",
                        content=content,
                        symbols=[symbol],
                        content_hash=ch,
                    )
                    count += 1
            except Exception as e:
                log.debug("insider_check_error", symbol=symbol, error=str(e))
        return count

    async def _auto_analyze_recent_earnings(self, user_id: int, symbols: list[str]) -> int:
        """Auto-analyze earnings transcripts for holdings that reported in the last 48 hours."""
        if not self.ai_engine:
            return 0

        count = 0
        now = datetime.now(UTC)

        for symbol in symbols[:10]:
            try:
                earnings = await self.dm.get_earnings(symbol)
                if not earnings or not isinstance(earnings, list):
                    continue

                latest = earnings[0]
                period = latest.get("period") or latest.get("date")
                quarter = latest.get("quarter")
                year = latest.get("year")
                if not period or not quarter or not year:
                    continue

                # Check if this earnings report dropped in the last 48 hours
                try:
                    earn_date = datetime.fromisoformat(str(period).replace("Z", "+00:00"))
                    hours_since = (now.replace(tzinfo=None) - earn_date.replace(tzinfo=None)).total_seconds() / 3600
                except (ValueError, TypeError):
                    continue

                if hours_since < 0 or hours_since > 48:
                    continue

                # Dedup — only analyze once per earnings period
                ch = _content_hash(f"earnings_ai_{symbol}_{year}_Q{quarter}")
                if await self.insight_repo.was_recently_created(user_id, "earnings_analysis", ch):
                    continue

                # Fetch transcript
                try:
                    transcript = await self.dm.get_earnings_transcript(symbol, int(year), int(quarter))
                except Exception:
                    transcript = None

                if not transcript or not transcript.get("content"):
                    # No transcript yet — still create a basic earnings alert with surprise data
                    actual = latest.get("actual")
                    estimate = latest.get("estimate")
                    if actual is not None and estimate is not None:
                        surprise = ((actual - estimate) / abs(estimate)) * 100 if estimate != 0 else 0
                        emoji = "beat" if surprise > 0 else "missed"
                        content = (
                            f"**{symbol}** just reported Q{quarter} {year} earnings: "
                            f"EPS ${actual:.2f} vs ${estimate:.2f} est ({emoji} by {abs(surprise):.1f}%). "
                            f"Transcript not yet available — will analyze when published."
                        )
                        await self.insight_repo.create(
                            discord_id=user_id,
                            insight_type="earnings_analysis",
                            title=f"{symbol} Q{quarter} earnings: {emoji} by {abs(surprise):.1f}%",
                            content=content,
                            symbols=[symbol],
                            content_hash=ch,
                        )
                        count += 1
                    continue

                # Use AI to analyze the transcript
                from ai.prompts.system import TRANSCRIPT_SUMMARY_PROMPT
                actual = latest.get("actual")
                estimate = latest.get("estimate")
                surprise_text = ""
                if actual is not None and estimate is not None and estimate != 0:
                    surprise = ((actual - estimate) / abs(estimate)) * 100
                    surprise_text = f"\nEPS: ${actual:.2f} actual vs ${estimate:.2f} estimate ({surprise:+.1f}% surprise)"

                transcript_text = transcript.get("content", "")[:8000]  # Cap to avoid token limits
                prompt = (
                    f"Analyze this Q{quarter} {year} earnings call transcript for {symbol}.{surprise_text}\n\n"
                    f"Transcript excerpt:\n{transcript_text}\n\n"
                    f"Provide a concise summary covering: key numbers vs expectations, management tone, "
                    f"guidance changes, and the single most important takeaway for an investor."
                )

                try:
                    analysis = await self.ai_engine.analyze(
                        prompt=prompt,
                        force_model="haiku",
                        system_prompt=TRANSCRIPT_SUMMARY_PROMPT,
                    )
                except Exception as e:
                    log.warning("earnings_ai_analysis_error", symbol=symbol, error=str(e))
                    continue

                await self.insight_repo.create(
                    discord_id=user_id,
                    insight_type="earnings_analysis",
                    title=f"{symbol} Q{quarter} {year} Earnings Analysis",
                    content=analysis[:2000],  # Cap for Discord
                    symbols=[symbol],
                    content_hash=ch,
                )
                count += 1

            except Exception as e:
                log.debug("earnings_analysis_error", symbol=symbol, error=str(e))
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
        now = datetime.now(UTC)

        for item in items:
            created = item["created_at"].replace(tzinfo=None)
            days_old = (now.replace(tzinfo=None) - created).days
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

    async def _check_interest_news(
        self, user_id: int, interests: list[str], symbols: list[str]
    ) -> int:
        """Check pre-fetched sector news for strong-sentiment articles relevant to user interests."""
        count = 0
        tracked_symbols = set(symbols)

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

            sentiment = article.get("sentiment")
            if sentiment is None or abs(sentiment) < NEWS_STRONG_SENTIMENT:
                continue

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

    async def _prefetch_ai_news(self) -> None:
        """Fetch AI news once per cycle, shared across all users."""
        try:
            self._ai_news_cache = await self.dm.get_ai_news()
            article_count = len(self._ai_news_cache.get("articles", []))
            paper_count = len(self._ai_news_cache.get("papers", []))
            log.debug("prefetched_ai_news", articles=article_count, papers=paper_count)
        except Exception as e:
            log.debug("prefetch_ai_news_error", error=str(e))
            # Fall back to Technology sector news if available
            tech_articles = self._sector_news_cache.get("Technology", [])
            if tech_articles:
                ai_articles = [a for a in tech_articles
                               if is_ai_related(f"{a.get('title', '')} {a.get('description', '')}")]
                self._ai_news_cache = {"articles": ai_articles, "papers": []}
            else:
                self._ai_news_cache = {"articles": [], "papers": []}

    async def _check_ai_news(self, user_id: int) -> int:
        """Check AI news cache and create insights for a user."""
        if not self._ai_news_cache:
            return 0

        count = 0
        articles = self._ai_news_cache.get("articles", [])
        papers = self._ai_news_cache.get("papers", [])

        # Process articles
        for article in articles:
            if count >= MAX_AI_NEWS_PER_USER:
                break

            url = article.get("url", "")
            if not url:
                continue

            ch = _content_hash(url)
            try:
                if await self.insight_repo.was_recently_created(user_id, "ai_news", ch):
                    continue

                title = article.get("title", "Untitled")
                description = article.get("description", article.get("snippet", ""))[:200]
                sentiment = article.get("sentiment")
                source = article.get("source", "")

                content = f"**{title}**"
                if description:
                    content += f"\n{description}"
                if sentiment is not None:
                    label = "Positive" if sentiment > 0 else "Negative" if sentiment < 0 else "Neutral"
                    content += f"\nSentiment: {label} ({sentiment:+.2f})"
                if source:
                    content += f"\nSource: {source}"
                if url:
                    content += f"\n[Read more]({url})"

                await self.insight_repo.create(
                    discord_id=user_id,
                    insight_type="ai_news",
                    title=f"AI News: {title[:80]}",
                    content=content,
                    content_hash=ch,
                )
                count += 1
            except Exception as e:
                log.debug("ai_news_insight_error", url=url, error=str(e))

        # Process papers (if room under cap)
        for paper in papers:
            if count >= MAX_AI_NEWS_PER_USER:
                break

            arxiv_id = paper.get("arxiv_id", "")
            if not arxiv_id:
                continue

            ch = _content_hash(arxiv_id)
            try:
                if await self.insight_repo.was_recently_created(user_id, "ai_news", ch):
                    continue

                title = paper.get("title", "Untitled")
                summary = paper.get("summary", "")[:200]
                authors = ", ".join(paper.get("authors", [])[:3])
                pdf_url = paper.get("pdf_url", arxiv_id)

                content = f"**{title}**"
                if authors:
                    content += f"\nAuthors: {authors}"
                if summary:
                    content += f"\n{summary}"
                if pdf_url:
                    content += f"\n[Read paper]({pdf_url})"

                await self.insight_repo.create(
                    discord_id=user_id,
                    insight_type="ai_news",
                    title=f"AI Research: {title[:80]}",
                    content=content,
                    content_hash=ch,
                )
                count += 1
            except Exception as e:
                log.debug("ai_paper_insight_error", arxiv_id=arxiv_id, error=str(e))

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
