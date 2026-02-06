"""Morning briefing generator."""

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
    """Generate and send the morning market briefing."""
    log.info("generating_morning_briefing")

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
        log.info("morning_briefing_sent")

    except Exception as e:
        log.error("morning_briefing_error", error=str(e))
