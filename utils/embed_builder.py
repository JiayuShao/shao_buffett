"""Discord embed construction helpers."""

import discord
from config.constants import EmbedColor
from utils.formatting import truncate


def make_embed(
    title: str,
    description: str = "",
    color: EmbedColor | int = EmbedColor.INFO,
    footer: str | None = None,
    thumbnail: str | None = None,
    image: str | None = None,
) -> discord.Embed:
    """Create a standard embed with consistent styling."""
    embed = discord.Embed(
        title=title,
        description=truncate(description, 4096) if description else None,
        color=int(color),
    )
    if footer:
        embed.set_footer(text=footer)
    else:
        embed.set_footer(text="Shao Buffett • AI Financial Agent")
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    if image:
        embed.set_image(url=image)
    return embed


def error_embed(message: str) -> discord.Embed:
    """Create an error embed."""
    return make_embed(
        title="Error",
        description=message,
        color=EmbedColor.ERROR,
    )


def success_embed(message: str) -> discord.Embed:
    """Create a success embed."""
    return make_embed(
        title="Success",
        description=message,
        color=EmbedColor.SUCCESS,
    )


def price_embed(
    symbol: str,
    price: float,
    change: float,
    change_pct: float,
    **kwargs: str | float | None,
) -> discord.Embed:
    """Create a stock price embed."""
    color = EmbedColor.BULLISH if change >= 0 else EmbedColor.BEARISH
    sign = "+" if change >= 0 else ""
    arrow = "▲" if change >= 0 else "▼"

    embed = make_embed(
        title=f"{symbol} ${price:.2f}",
        description=f"{arrow} {sign}{change:.2f} ({sign}{change_pct:.2f}%)",
        color=color,
    )

    for key, value in kwargs.items():
        if value is not None:
            name = key.replace("_", " ").title()
            embed.add_field(name=name, value=str(value), inline=True)

    return embed


def news_embed(
    title: str,
    source: str,
    summary: str,
    url: str | None = None,
    sentiment: float | None = None,
    symbols: list[str] | None = None,
) -> discord.Embed:
    """Create a news article embed."""
    color = EmbedColor.NEWS
    if sentiment is not None:
        if sentiment > 0.2:
            color = EmbedColor.BULLISH
        elif sentiment < -0.2:
            color = EmbedColor.BEARISH

    embed = make_embed(
        title=truncate(title, 256),
        description=truncate(summary, 4096),
        color=color,
    )
    embed.add_field(name="Source", value=source, inline=True)
    if symbols:
        embed.add_field(name="Tickers", value=", ".join(symbols[:10]), inline=True)
    if sentiment is not None:
        label = "Bullish" if sentiment > 0.2 else "Bearish" if sentiment < -0.2 else "Neutral"
        embed.add_field(name="Sentiment", value=f"{label} ({sentiment:.2f})", inline=True)
    if url:
        embed.url = url

    return embed
