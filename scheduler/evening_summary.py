"""Evening market summary generator."""

import structlog
from typing import Any
from ai.engine import AIEngine
from ai.prompts.system import BRIEFING_SYSTEM_PROMPT
from data.manager import DataManager
from notifications.dispatcher import NotificationDispatcher
from notifications.types import Notification
from config.constants import NotificationType

log = structlog.get_logger(__name__)


async def generate_evening_summary(
    ai_engine: AIEngine,
    data_manager: DataManager,
    dispatcher: NotificationDispatcher,
) -> None:
    """Generate and send the evening market close recap — personalized when possible."""
    log.info("generating_evening_summary")

    personalized_users: set[int] = set()

    try:
        from storage.repositories.portfolio_repo import PortfolioRepository
        from storage.repositories.watchlist_repo import WatchlistRepository
        from storage.repositories.notes_repo import NotesRepository
        from storage.repositories.user_repo import UserRepository
        portfolio_repo = PortfolioRepository(ai_engine.db_pool)
        watchlist_repo = WatchlistRepository(ai_engine.db_pool)
        notes_repo = NotesRepository(ai_engine.db_pool)
        user_repo = UserRepository(ai_engine.db_pool)

        portfolio_users = await portfolio_repo.get_all_users_with_holdings()
        watchlist_users = await watchlist_repo.get_all_users_with_watchlist()
        all_users = list(dict.fromkeys(portfolio_users + watchlist_users))

        for user_id in all_users:
            try:
                holdings = await portfolio_repo.get_holdings(user_id)
                held_symbols = [h["symbol"] for h in holdings]
                watchlist_symbols = await watchlist_repo.get(user_id)
                symbols = list(dict.fromkeys(held_symbols + watchlist_symbols))

                if not symbols:
                    continue

                await _generate_personalized_summary(
                    ai_engine, dispatcher, user_id, symbols, notes_repo, user_repo,
                )
                personalized_users.add(user_id)
            except Exception as e:
                log.error("personalized_evening_error", user_id=user_id, error=str(e))
    except Exception as e:
        log.debug("personalized_evening_setup_error", error=str(e))

    # Generic summary only if no personalized ones were generated
    if not personalized_users:
        await _generate_generic_summary(ai_engine, dispatcher)


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


async def _generate_personalized_summary(
    ai_engine: AIEngine,
    dispatcher: NotificationDispatcher,
    user_id: int,
    symbols: list[str],
    notes_repo: Any,
    user_repo: Any | None = None,
) -> None:
    """Generate a personalized evening recap for a specific user."""
    concerns = await notes_repo.get_by_type(user_id, "concern", limit=5)
    concern_text = ""
    if concerns:
        concern_text = "\n\nThe user has these active concerns:\n" + "\n".join(
            f"- {c['content']}" for c in concerns
        )

    interests_text = await _get_interests_text(user_id, user_repo)

    symbols_str = ", ".join(symbols[:20])
    prompt = (
        f"Generate a personalized evening market close summary for a user tracking: {symbols_str}.\n\n"
        f"Use your tools to fetch:\n"
        f"1. Closing prices for their tracked stocks\n"
        f"2. Today's biggest market news relevant to their positions\n"
        f"3. Any analyst upgrades/downgrades today for their stocks\n"
        f"4. Sector performance for the day\n"
        f"5. Key macro data updates\n\n"
        f"Prioritize their stocks in the recap. Highlight the biggest movers and key stories.{concern_text}{interests_text}\n\n"
        f"Format as a close-of-day recap with emojis for quick visual parsing."
    )

    summary = await ai_engine.analyze(
        prompt=prompt,
        force_model="sonnet",
        system_prompt=BRIEFING_SYSTEM_PROMPT,
    )

    notif = Notification(
        type=NotificationType.EVENING_SUMMARY,
        title="Your Evening Summary",
        description=summary,
        target_users=[user_id],
        urgency="medium",
    )
    await dispatcher.dispatch(notif)
    log.info("personalized_evening_summary_sent", user_id=user_id)


async def _generate_generic_summary(
    ai_engine: AIEngine,
    dispatcher: NotificationDispatcher,
) -> None:
    """Generate a generic evening summary for all users."""
    prompt = (
        "Generate an evening market close summary. Use your tools to fetch:\n"
        "1. Closing prices for major tech stocks (AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA)\n"
        "2. Today's biggest market news\n"
        "3. Any analyst upgrades/downgrades today for these stocks\n"
        "4. Sector performance for the day\n"
        "5. Key macro data updates\n\n"
        "Format as a close-of-day recap. Highlight the biggest movers and key stories."
    )

    try:
        summary = await ai_engine.analyze(
            prompt=prompt,
            force_model="sonnet",
            system_prompt=BRIEFING_SYSTEM_PROMPT,
        )

        notif = Notification(
            type=NotificationType.EVENING_SUMMARY,
            title="Evening Market Summary",
            description=summary,
            urgency="medium",
        )
        await dispatcher.dispatch(notif)
        log.info("generic_evening_summary_sent")

    except Exception as e:
        log.error("generic_evening_summary_error", error=str(e))
