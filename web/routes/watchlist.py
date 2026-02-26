"""Web watchlist management routes."""

from quart import Blueprint, render_template, request, session, redirect, url_for
from storage.repositories.watchlist_repo import WatchlistRepository
from storage.database import get_pool
from utils.formatting import validate_ticker

watchlist_bp = Blueprint("watchlist_routes", __name__)


def login_required(f):
    from functools import wraps

    @wraps(f)
    async def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("auth.login"))
        return await f(*args, **kwargs)

    return decorated


@watchlist_bp.route("/")
@login_required
async def watchlist_page():
    user = session["user"]
    pool = await get_pool()
    repo = WatchlistRepository(pool)
    symbols = await repo.get(user["id"])
    return await render_template("dashboard.html", user=user, symbols=symbols, quotes=[], quotes_json="[]")


@watchlist_bp.route("/add", methods=["POST"])
@login_required
async def add_symbol():
    form = await request.form
    symbol = form.get("symbol", "")
    ticker = validate_ticker(symbol)

    if ticker:
        pool = await get_pool()
        repo = WatchlistRepository(pool)
        await repo.add(session["user"]["id"], ticker)

    return redirect(url_for("dashboard_routes.dashboard_page"))


@watchlist_bp.route("/remove/<symbol>", methods=["POST"])
@login_required
async def remove_symbol(symbol: str):
    pool = await get_pool()
    repo = WatchlistRepository(pool)
    await repo.remove(session["user"]["id"], symbol)
    return redirect(url_for("dashboard_routes.dashboard_page"))
