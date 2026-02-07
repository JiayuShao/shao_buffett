"""Morning briefing generator — personalized per user when they have portfolios."""

import structlog
from typing import Any
from ai.engine import AIEngine
from ai.prompts.system import BRIEFING_SYSTEM_PROMPT
from data.manager import DataManager
from notifications.dispatcher import NotificationDispatcher
from notifications.types import Notification
from config.constants import NotificationType

log = structlog.get_logger(__name__)

# Structured briefing prompt with clear sections
PERSONALIZED_BRIEFING_PROMPT = """Generate a personalized morning market briefing for a user who holds: {symbols}.

Use your tools to fetch:
1. Current quotes for their holdings (flag any >3% moves)
2. get_factor_grades for the user's largest 3 holdings (show Quant Rating)
3. Latest news relevant to their positions
4. Any analyst actions on their stocks
5. Key macro indicators (VIX, 10Y yield)
6. Sector performance

Structure the briefing with these EXACT sections:

## Market Pulse
Key index levels. Risk-on or risk-off? VIX level.

## Your Portfolio
For each holding: price, daily change, any notable news. Flag the biggest movers with arrows.

## Quant Snapshot
Show factor grades and Quant Rating for their top 3 holdings. Flag any Sell-rated positions.

## Earnings Calendar
List any holdings reporting earnings in the next 7 days. Include date and key metrics to watch.

## News & Catalysts
Top 3-5 most relevant stories for their holdings. Include sentiment.

## Analyst Actions
Any upgrades, downgrades, or price target changes for portfolio/watchlist stocks.

## Macro Backdrop
Key macro data points that affect their holdings.

## Action Items
Specific things to pay attention to today based on all the above.{concern_text}{interests_text}

Use emojis for quick visual parsing (🟢 up, 🔴 down, ⚠️ alert, 📊 data, 📅 calendar).
Keep it concise but comprehensive — this replaces reading 10 different sources.
"""

WATCHLIST_BRIEFING_PROMPT = """Generate a personalized morning market briefing for a user watching: {symbols}.

Use your tools to fetch:
1. Current quotes for their watchlist stocks (flag any >3% moves)
2. get_factor_grades for the top 3 watchlist stocks (show Quant Rating)
3. Latest news relevant to their watchlist
4. Any analyst actions on their watched stocks
5. Key macro indicators (VIX, 10Y yield)
6. Sector performance

Structure the briefing with these EXACT sections:

## Market Pulse
Key index levels. Risk-on or risk-off? VIX level.

## Watchlist Movers
For each watched stock: price, daily change. Flag significant moves with arrows.

## Quant Snapshot
Show factor grades and Quant Rating for top 3 watchlist stocks. Highlight any Strong Buy or Strong Sell.

## Earnings Calendar
List any watchlist stocks reporting earnings in the next 7 days.

## News & Catalysts
Top 3-5 most relevant stories for their watchlist. Include sentiment.

## Analyst Actions
Any upgrades, downgrades, or price target changes.

## Macro Backdrop
Key macro indicators affecting their watched sectors.{concern_text}{interests_text}

Use emojis for quick visual parsing (🟢 up, 🔴 down, ⚠️ alert, 📊 data, 📅 calendar).
"""


async def generate_morning_briefing(
    ai_engine: AIEngine,
    data_manager: DataManager,
    dispatcher: NotificationDispatcher,
) -> None:
    """Generate morning briefings — personalized per user when possible."""
    log.info("generating_morning_briefing")

    personalized_users: set[int] = set()

    try:
        from storage.repositories.portfolio_repo import PortfolioRepository
        from storage.repositories.notes_repo import NotesRepository
        from storage.repositories.watchlist_repo import WatchlistRepository
        from storage.repositories.user_repo import UserRepository
        portfolio_repo = PortfolioRepository(ai_engine.db_pool)
        notes_repo = NotesRepository(ai_engine.db_pool)
        watchlist_repo = WatchlistRepository(ai_engine.db_pool)
        user_repo = UserRepository(ai_engine.db_pool)

        users_with_holdings = await portfolio_repo.get_all_users_with_holdings()
        for user_id in users_with_holdings:
            try:
                await _generate_personalized_briefing(
                    ai_engine, data_manager, dispatcher,
                    user_id, portfolio_repo, notes_repo, user_repo,
                )
                personalized_users.add(user_id)
            except Exception as e:
                log.error("personalized_briefing_error", user_id=user_id, error=str(e))

        users_with_watchlist = await watchlist_repo.get_all_users_with_watchlist()
        for user_id in users_with_watchlist:
            if user_id in personalized_users:
                continue
            try:
                await _generate_watchlist_briefing(
                    ai_engine, data_manager, dispatcher,
                    user_id, watchlist_repo, notes_repo, user_repo,
                )
                personalized_users.add(user_id)
            except Exception as e:
                log.error("watchlist_briefing_error", user_id=user_id, error=str(e))
    except Exception as e:
        log.debug("personalized_briefing_setup_error", error=str(e))

    if not personalized_users:
        await _generate_generic_briefing(ai_engine, dispatcher)


async def _generate_personalized_briefing(
    ai_engine: AIEngine,
    data_manager: DataManager,
    dispatcher: NotificationDispatcher,
    user_id: int,
    portfolio_repo: Any,
    notes_repo: Any,
    user_repo: Any | None = None,
) -> None:
    """Generate a personalized briefing for a specific user."""
    holdings = await portfolio_repo.get_holdings(user_id)
    symbols = [h["symbol"] for h in holdings]
    if not symbols:
        return

    concerns = await notes_repo.get_by_type(user_id, "concern", limit=5)
    concern_text = ""
    if concerns:
        concern_text = "\n\nThe user has these active concerns:\n" + "\n".join(
            f"- {c['content']}" for c in concerns
        )

    interests_text = await _get_interests_text(user_id, user_repo)

    symbols_str = ", ".join(symbols[:15])
    prompt = PERSONALIZED_BRIEFING_PROMPT.format(
        symbols=symbols_str,
        concern_text=concern_text,
        interests_text=interests_text,
    )

    briefing = await ai_engine.analyze(
        prompt=prompt,
        force_model="sonnet",
        system_prompt=BRIEFING_SYSTEM_PROMPT,
    )

    notif = Notification(
        type=NotificationType.MORNING_BRIEFING,
        title="Your Morning Briefing",
        description=briefing,
        target_users=[user_id],
        urgency="medium",
    )
    await dispatcher.dispatch(notif)
    log.info("personalized_morning_briefing_sent", user_id=user_id)


async def _generate_watchlist_briefing(
    ai_engine: AIEngine,
    data_manager: DataManager,
    dispatcher: NotificationDispatcher,
    user_id: int,
    watchlist_repo: Any,
    notes_repo: Any,
    user_repo: Any | None = None,
) -> None:
    """Generate a personalized briefing for a user based on their watchlist."""
    symbols = await watchlist_repo.get(user_id)
    if not symbols:
        return

    concerns = await notes_repo.get_by_type(user_id, "concern", limit=5)
    concern_text = ""
    if concerns:
        concern_text = "\n\nThe user has these active concerns:\n" + "\n".join(
            f"- {c['content']}" for c in concerns
        )

    interests_text = await _get_interests_text(user_id, user_repo)

    symbols_str = ", ".join(symbols[:15])
    prompt = WATCHLIST_BRIEFING_PROMPT.format(
        symbols=symbols_str,
        concern_text=concern_text,
        interests_text=interests_text,
    )

    briefing = await ai_engine.analyze(
        prompt=prompt,
        force_model="sonnet",
        system_prompt=BRIEFING_SYSTEM_PROMPT,
    )

    notif = Notification(
        type=NotificationType.MORNING_BRIEFING,
        title="Your Morning Briefing",
        description=briefing,
        target_users=[user_id],
        urgency="medium",
    )
    await dispatcher.dispatch(notif)
    log.info("watchlist_morning_briefing_sent", user_id=user_id)


async def _get_interests_text(user_id: int, user_repo: Any | None) -> str:
    """Fetch user's sector interests and format as prompt context."""
    if not user_repo:
        return ""
    try:
        profile = await user_repo.get_or_create(user_id)
        interests = profile.get("interests")
        if isinstance(interests, dict) and interests.get("sectors"):
            sectors = ", ".join(interests["sectors"])
            return f"\n\nThe user is especially interested in these sectors: {sectors}. Include relevant developments in these areas."
    except Exception:
        pass
    return ""


async def _generate_generic_briefing(
    ai_engine: AIEngine,
    dispatcher: NotificationDispatcher,
) -> None:
    """Generate a generic morning briefing for all users."""
    prompt = (
        "Generate a morning market briefing. Use your tools to fetch:\n"
        "1. Current quotes for the major tech stocks (AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA)\n"
        "2. Latest market news (top 5 stories)\n"
        "3. Key macro indicators (VIX, 10Y yield, Fed funds rate)\n"
        "4. Sector performance\n\n"
        "Format as a scannable morning briefing with emojis for quick visual parsing."
    )

    try:
        briefing = await ai_engine.analyze(
            prompt=prompt,
            force_model="sonnet",
            system_prompt=BRIEFING_SYSTEM_PROMPT,
        )

        notif = Notification(
            type=NotificationType.MORNING_BRIEFING,
            title="Morning Market Briefing",
            description=briefing,
            urgency="medium",
        )
        await dispatcher.dispatch(notif)
        log.info("generic_morning_briefing_sent")

    except Exception as e:
        log.error("generic_morning_briefing_error", error=str(e))
