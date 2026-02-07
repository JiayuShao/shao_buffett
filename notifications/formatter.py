"""Discord embed builders for each notification type."""

import discord
from notifications.types import Notification
from config.constants import NotificationType, EmbedColor
from utils.formatting import format_currency, format_percent, truncate


def format_notification(notif: Notification) -> discord.Embed:
    """Create a Discord embed for a notification."""
    formatters = {
        NotificationType.PRICE_ALERT: _format_price_alert,
        NotificationType.BREAKING_NEWS: _format_news,
        NotificationType.ANALYST_UPGRADE: _format_analyst,
        NotificationType.ANALYST_DOWNGRADE: _format_analyst,
        NotificationType.TARGET_PRICE_CHANGE: _format_target_change,
        NotificationType.EARNINGS_SURPRISE: _format_earnings,
        NotificationType.MACRO_RELEASE: _format_macro,
        NotificationType.INSIDER_TRADE: _format_insider,
        NotificationType.SEC_FILING: _format_filing,
        NotificationType.EARNINGS_TRANSCRIPT: _format_transcript,
        NotificationType.RESEARCH_DIGEST: _format_research,
        NotificationType.PROACTIVE_INSIGHT: _format_proactive_insight,
    }

    formatter = formatters.get(notif.type, _format_default)
    return formatter(notif)


def _format_price_alert(notif: Notification) -> discord.Embed:
    data = notif.data
    price = data.get("price", 0)
    condition = data.get("condition", "")
    threshold = data.get("threshold", 0)

    embed = discord.Embed(
        title=f"🔔 Price Alert — {notif.symbol}",
        description=f"**{notif.symbol}** is now ${price:.2f} ({condition} {format_currency(threshold)})",
        color=EmbedColor.ALERT,
    )
    embed.set_footer(text="Shao Buffett • Price Alert")
    return embed


def _format_news(notif: Notification) -> discord.Embed:
    data = notif.data
    sentiment = data.get("sentiment")
    color = EmbedColor.NEWS
    if sentiment and sentiment > 0.2:
        color = EmbedColor.BULLISH
    elif sentiment and sentiment < -0.2:
        color = EmbedColor.BEARISH

    embed = discord.Embed(
        title=f"📰 {truncate(notif.title, 256)}",
        description=truncate(notif.description, 4096),
        color=color,
    )
    if data.get("source"):
        embed.add_field(name="Source", value=data["source"], inline=True)
    if notif.symbol:
        embed.add_field(name="Ticker", value=notif.symbol, inline=True)
    if data.get("url"):
        embed.url = data["url"]
    embed.set_footer(text="Shao Buffett • Breaking News")
    return embed


def _format_analyst(notif: Notification) -> discord.Embed:
    data = notif.data
    is_upgrade = notif.type == NotificationType.ANALYST_UPGRADE
    emoji = "⬆️" if is_upgrade else "⬇️"
    color = EmbedColor.BULLISH if is_upgrade else EmbedColor.BEARISH

    embed = discord.Embed(
        title=f"{emoji} Analyst {'Upgrade' if is_upgrade else 'Downgrade'} — {notif.symbol}",
        description=notif.description,
        color=color,
    )
    if data.get("firm"):
        embed.add_field(name="Firm", value=data["firm"], inline=True)
    if data.get("from_grade"):
        embed.add_field(name="From", value=data["from_grade"], inline=True)
    if data.get("to_grade"):
        embed.add_field(name="To", value=data["to_grade"], inline=True)
    embed.set_footer(text="Shao Buffett • Analyst Action")
    return embed


def _format_target_change(notif: Notification) -> discord.Embed:
    data = notif.data
    embed = discord.Embed(
        title=f"🎯 Target Price Change — {notif.symbol}",
        description=notif.description,
        color=EmbedColor.INFO,
    )
    if data.get("old_target"):
        embed.add_field(name="Old Target", value=format_currency(data["old_target"]), inline=True)
    if data.get("new_target"):
        embed.add_field(name="New Target", value=format_currency(data["new_target"]), inline=True)
    embed.set_footer(text="Shao Buffett • Price Target")
    return embed


def _format_earnings(notif: Notification) -> discord.Embed:
    data = notif.data
    surprise = data.get("surprise_pct", 0)
    color = EmbedColor.BULLISH if surprise > 0 else EmbedColor.BEARISH
    emoji = "✅" if surprise > 0 else "❌"

    embed = discord.Embed(
        title=f"{emoji} Earnings {'Beat' if surprise > 0 else 'Miss'} — {notif.symbol}",
        description=notif.description,
        color=color,
    )
    if data.get("actual_eps") is not None:
        embed.add_field(name="EPS Actual", value=f"${data['actual_eps']:.2f}", inline=True)
    if data.get("estimated_eps") is not None:
        embed.add_field(name="EPS Est.", value=f"${data['estimated_eps']:.2f}", inline=True)
    embed.add_field(name="Surprise", value=format_percent(surprise), inline=True)
    embed.set_footer(text="Shao Buffett • Earnings")
    return embed


def _format_macro(notif: Notification) -> discord.Embed:
    embed = discord.Embed(
        title=f"📊 Macro Release — {notif.title}",
        description=notif.description,
        color=EmbedColor.MACRO,
    )
    embed.set_footer(text="Shao Buffett • Macro Data")
    return embed


def _format_insider(notif: Notification) -> discord.Embed:
    data = notif.data
    embed = discord.Embed(
        title=f"👤 Insider Trade — {notif.symbol}",
        description=notif.description,
        color=EmbedColor.WARNING,
    )
    if data.get("name"):
        embed.add_field(name="Insider", value=data["name"], inline=True)
    if data.get("transaction_type"):
        embed.add_field(name="Type", value=data["transaction_type"], inline=True)
    if data.get("value"):
        embed.add_field(name="Value", value=format_currency(data["value"]), inline=True)
    embed.set_footer(text="Shao Buffett • Insider Trade")
    return embed


def _format_filing(notif: Notification) -> discord.Embed:
    data = notif.data
    embed = discord.Embed(
        title=f"📋 SEC Filing — {notif.symbol} ({data.get('form_type', 'Filing')})",
        description=truncate(notif.description, 4096),
        color=EmbedColor.RESEARCH,
    )
    if data.get("file_date"):
        embed.add_field(name="Filed", value=data["file_date"], inline=True)
    if data.get("url"):
        embed.url = data["url"]
    embed.set_footer(text="Shao Buffett • SEC Filing")
    return embed


def _format_transcript(notif: Notification) -> discord.Embed:
    embed = discord.Embed(
        title=f"🎙️ Earnings Transcript — {notif.symbol}",
        description=truncate(notif.description, 4096),
        color=EmbedColor.EARNINGS,
    )
    embed.set_footer(text="Shao Buffett • Earnings Transcript Summary")
    return embed


def _format_research(notif: Notification) -> discord.Embed:
    embed = discord.Embed(
        title=f"📚 Research Digest",
        description=truncate(notif.description, 4096),
        color=EmbedColor.RESEARCH,
    )
    embed.set_footer(text="Shao Buffett • Research Digest")
    return embed


def _format_proactive_insight(notif: Notification) -> discord.Embed:
    data = notif.data
    insight_type = data.get("insight_type", "")

    type_config = {
        "portfolio_drift": ("📊", EmbedColor.WARNING),
        "earnings_upcoming": ("📅", EmbedColor.EARNINGS),
        "price_movement": ("📈", EmbedColor.ALERT),
        "news_relevant": ("📰", EmbedColor.NEWS),
        "action_reminder": ("📋", EmbedColor.WARNING),
        "symbol_suggestion": ("💡", EmbedColor.INFO),
        "polymarket_signal": ("🔮", EmbedColor.MACRO),
    }
    emoji, color = type_config.get(insight_type, ("🔔", EmbedColor.INFO))

    embed = discord.Embed(
        title=f"{emoji} {notif.title}",
        description=truncate(notif.description, 4096),
        color=color,
    )
    if notif.symbol:
        embed.add_field(name="Symbol", value=notif.symbol, inline=True)
    embed.set_footer(text="Shao Buffett • Proactive Insight")
    return embed


def _format_default(notif: Notification) -> discord.Embed:
    return discord.Embed(
        title=notif.title,
        description=truncate(notif.description, 4096),
        color=EmbedColor.INFO,
    )
