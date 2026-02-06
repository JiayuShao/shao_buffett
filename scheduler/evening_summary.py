"""Evening market summary generator."""

import structlog
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
    """Generate and send the evening market close recap."""
    log.info("generating_evening_summary")

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
        log.info("evening_summary_sent")

    except Exception as e:
        log.error("evening_summary_error", error=str(e))
