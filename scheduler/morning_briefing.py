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


async def generate_morning_briefing(
    ai_engine: AIEngine,
    data_manager: DataManager,
    dispatcher: NotificationDispatcher,
) -> None:
    """Generate morning briefings — personalized per user when possible."""
    log.info("generating_morning_briefing")

    # Try to generate personalized briefings for users with portfolios
    try:
        from storage.repositories.portfolio_repo import PortfolioRepository
        from storage.repositories.notes_repo import NotesRepository
        portfolio_repo = PortfolioRepository(ai_engine.db_pool)
        notes_repo = NotesRepository(ai_engine.db_pool)

        users_with_holdings = await portfolio_repo.get_all_users_with_holdings()
        for user_id in users_with_holdings:
            try:
                await _generate_personalized_briefing(
                    ai_engine, data_manager, dispatcher,
                    user_id, portfolio_repo, notes_repo,
                )
            except Exception as e:
                log.error("personalized_briefing_error", user_id=user_id, error=str(e))
    except Exception as e:
        log.debug("personalized_briefing_setup_error", error=str(e))

    # Also generate a generic briefing for users without portfolios
    await _generate_generic_briefing(ai_engine, dispatcher)


async def _generate_personalized_briefing(
    ai_engine: AIEngine,
    data_manager: DataManager,
    dispatcher: NotificationDispatcher,
    user_id: int,
    portfolio_repo: Any,
    notes_repo: Any,
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

    symbols_str = ", ".join(symbols[:15])
    prompt = (
        f"Generate a personalized morning market briefing for a user who holds: {symbols_str}.\n\n"
        f"Use your tools to fetch:\n"
        f"1. Current quotes for their holdings\n"
        f"2. Latest news relevant to their positions\n"
        f"3. Any analyst actions on their stocks\n"
        f"4. Key macro indicators (VIX, 10Y yield)\n"
        f"5. Sector performance\n\n"
        f"Prioritize their holdings in the briefing. Flag any significant moves.{concern_text}\n\n"
        f"Format as a scannable morning briefing with emojis for quick visual parsing."
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
