"""Plotly figure to PNG rendering via Kaleido for Discord."""

import io
import discord
import plotly.graph_objects as go
import structlog

log = structlog.get_logger(__name__)


def render_to_bytes(fig: go.Figure, format: str = "png") -> bytes:
    """Render a Plotly figure to PNG bytes."""
    return fig.to_image(format=format, engine="kaleido")


def render_to_discord_file(fig: go.Figure, filename: str = "chart.png") -> discord.File:
    """Render a Plotly figure and wrap in a discord.File."""
    image_bytes = render_to_bytes(fig)
    return discord.File(io.BytesIO(image_bytes), filename=filename)
