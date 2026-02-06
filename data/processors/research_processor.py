"""Research report and filing summarization via Claude."""

import structlog
from typing import Any
from notifications.types import Notification
from config.constants import NotificationType

log = structlog.get_logger(__name__)


async def summarize_earnings_transcript(
    ai_engine: Any,
    symbol: str,
    transcript: dict[str, Any],
) -> Notification | None:
    """Summarize an earnings transcript using Claude."""
    content = transcript.get("content", "")
    if not content or len(content) < 100:
        return None

    from ai.prompts.system import TRANSCRIPT_SUMMARY_PROMPT

    # Truncate very long transcripts for cost management
    if len(content) > 50000:
        content = content[:50000] + "\n\n[Transcript truncated for length]"

    prompt = (
        f"Summarize the following earnings call transcript for {symbol}:\n\n"
        f"{content}"
    )

    try:
        summary = await ai_engine.analyze(
            prompt=prompt,
            force_model="sonnet",
            system_prompt=TRANSCRIPT_SUMMARY_PROMPT,
        )
    except Exception as e:
        log.error("transcript_summary_error", symbol=symbol, error=str(e))
        return None

    return Notification(
        type=NotificationType.EARNINGS_TRANSCRIPT,
        title=f"Earnings Transcript — {symbol}",
        description=summary,
        symbol=symbol,
        data={"quarter": transcript.get("quarter"), "year": transcript.get("year")},
        urgency="high",
    )


async def summarize_sec_filing(
    ai_engine: Any,
    symbol: str,
    filing: dict[str, Any],
) -> Notification | None:
    """Summarize an SEC filing using Claude."""
    from ai.prompts.system import FILING_SUMMARY_PROMPT

    form_type = filing.get("form_type", "Filing")
    description = filing.get("description", "")

    prompt = (
        f"A new {form_type} filing was detected for {symbol}.\n"
        f"Filing details: {description}\n"
        f"Filed on: {filing.get('file_date', 'Unknown')}\n\n"
        f"Based on the filing type and company, provide a brief analysis of what "
        f"investors should look for in this filing and its potential significance."
    )

    try:
        summary = await ai_engine.analyze(
            prompt=prompt,
            force_model="haiku",
            system_prompt=FILING_SUMMARY_PROMPT,
        )
    except Exception as e:
        log.error("filing_summary_error", symbol=symbol, error=str(e))
        return None

    return Notification(
        type=NotificationType.SEC_FILING,
        title=f"SEC {form_type} — {symbol}",
        description=summary,
        symbol=symbol,
        data={
            "form_type": form_type,
            "file_date": filing.get("file_date"),
            "url": filing.get("file_url"),
        },
        urgency="medium",
    )


async def create_research_digest(
    ai_engine: Any,
    papers: list[dict[str, Any]],
) -> Notification | None:
    """Create a weekly digest of relevant research papers."""
    if not papers:
        return None

    paper_summaries = []
    for p in papers[:10]:
        paper_summaries.append(
            f"Title: {p.get('title', 'Untitled')}\n"
            f"Authors: {', '.join(p.get('authors', [])[:3])}\n"
            f"Summary: {p.get('summary', '')[:200]}\n"
        )

    prompt = (
        "Create a concise weekly digest of these quantitative finance research papers. "
        "For each, provide a 1-2 sentence summary of the key finding and its practical relevance "
        "to investment decisions:\n\n" + "\n---\n".join(paper_summaries)
    )

    try:
        digest = await ai_engine.analyze(
            prompt=prompt,
            force_model="haiku",
        )
    except Exception as e:
        log.error("research_digest_error", error=str(e))
        return None

    return Notification(
        type=NotificationType.RESEARCH_DIGEST,
        title="Weekly Research Digest",
        description=digest,
        urgency="low",
    )
