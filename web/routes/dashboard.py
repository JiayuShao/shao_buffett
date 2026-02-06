"""Web dashboard routes — interactive Plotly charts."""

import json
from quart import Blueprint, render_template, session, redirect, url_for, current_app
import structlog

log = structlog.get_logger(__name__)

dashboard_bp = Blueprint("dashboard_routes", __name__)


def login_required(f):
    """Decorator to require login."""
    from functools import wraps

    @wraps(f)
    async def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("auth.login"))
        return await f(*args, **kwargs)

    return decorated


@dashboard_bp.route("/dashboard")
@login_required
async def dashboard_page():
    user = session["user"]
    dm = current_app.data_manager  # type: ignore[attr-defined]

    # Get user's watchlist
    from storage.repositories.watchlist_repo import WatchlistRepository
    from storage.database import get_pool

    pool = await get_pool()
    repo = WatchlistRepository(pool)
    symbols = await repo.get(user["id"])

    # Fetch quotes for watchlist
    quotes = []
    if dm:
        for symbol in symbols[:20]:
            try:
                q = await dm.get_quote(symbol)
                quotes.append(q)
            except Exception:
                quotes.append({"symbol": symbol, "price": 0, "change_pct": 0})

    return await render_template(
        "dashboard.html",
        user=user,
        symbols=symbols,
        quotes=quotes,
        quotes_json=json.dumps(quotes, default=str),
    )
