"""Plotly chart builders for financial data."""

import plotly.graph_objects as go
from typing import Any


def comparison_chart(
    symbols: list[str],
    quotes: list[dict[str, Any]],
    title: str = "Stock Comparison",
) -> go.Figure:
    """Create a bar chart comparing stock prices and changes."""
    names = []
    prices = []
    changes = []
    colors = []

    for quote in quotes:
        sym = quote.get("symbol", "")
        names.append(sym)
        prices.append(quote.get("price", 0))
        change = quote.get("change_pct", 0)
        changes.append(change)
        colors.append("#00C853" if change >= 0 else "#FF1744")

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=names,
        y=changes,
        marker_color=colors,
        text=[f"{c:+.2f}%" for c in changes],
        textposition="auto",
        name="Change %",
    ))

    fig.update_layout(
        title=title,
        yaxis_title="Change %",
        template="plotly_dark",
        height=400,
        width=700,
        margin=dict(l=50, r=30, t=50, b=40),
    )

    return fig


def sector_heatmap(sectors: list[dict[str, Any]], title: str = "Sector Performance") -> go.Figure:
    """Create a treemap/heatmap of sector performance."""
    names = []
    values = []
    colors_list = []

    for s in sectors:
        name = s.get("sector", s.get("name", "Unknown"))
        change = s.get("changesPercentage", 0)
        if isinstance(change, str):
            change = float(change.replace("%", ""))
        names.append(name)
        values.append(abs(change) + 0.1)  # Ensure positive for treemap
        colors_list.append(change)

    fig = go.Figure(go.Treemap(
        labels=names,
        parents=[""] * len(names),
        values=values,
        marker=dict(
            colors=colors_list,
            colorscale=[[0, "#FF1744"], [0.5, "#9E9E9E"], [1, "#00C853"]],
            cmid=0,
            showscale=True,
        ),
        texttemplate="%{label}<br>%{color:+.2f}%",
        hovertemplate="%{label}: %{color:+.2f}%<extra></extra>",
    ))

    fig.update_layout(
        title=title,
        template="plotly_dark",
        height=500,
        width=700,
        margin=dict(l=10, r=10, t=50, b=10),
    )

    return fig


def earnings_chart(
    symbol: str,
    earnings: list[dict[str, Any]],
    title: str | None = None,
) -> go.Figure:
    """Create an earnings history chart (actual vs estimate)."""
    periods = []
    actuals = []
    estimates = []

    for e in reversed(earnings[:8]):  # Last 8 quarters, chronological
        periods.append(e.get("period", ""))
        actuals.append(e.get("actual", 0))
        estimates.append(e.get("estimate", 0))

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=periods,
        y=actuals,
        name="Actual EPS",
        marker_color="#2979FF",
    ))

    fig.add_trace(go.Scatter(
        x=periods,
        y=estimates,
        name="Estimate",
        mode="lines+markers",
        line=dict(color="#FFD600", dash="dash"),
    ))

    fig.update_layout(
        title=title or f"{symbol} — Earnings History",
        yaxis_title="EPS ($)",
        template="plotly_dark",
        height=400,
        width=700,
        margin=dict(l=50, r=30, t=50, b=40),
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
    )

    return fig


def macro_trend_chart(
    series_name: str,
    observations: list[dict[str, Any]],
    title: str | None = None,
) -> go.Figure:
    """Create a line chart for a macro data series."""
    dates = []
    values = []

    for obs in reversed(observations):
        val = obs.get("value", ".")
        if val == ".":
            continue
        dates.append(obs.get("date", ""))
        values.append(float(val))

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=dates,
        y=values,
        mode="lines",
        fill="tozeroy",
        line=dict(color="#7C4DFF"),
        fillcolor="rgba(124,77,255,0.1)",
    ))

    fig.update_layout(
        title=title or f"{series_name} Trend",
        template="plotly_dark",
        height=400,
        width=700,
        margin=dict(l=50, r=30, t=50, b=40),
    )

    return fig
