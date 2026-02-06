"""JSON API endpoints for AJAX auto-refresh."""

from quart import Blueprint, session, jsonify, current_app
from storage.repositories.watchlist_repo import WatchlistRepository
from storage.database import get_pool

api_bp = Blueprint("api", __name__)


def login_required(f):
    from functools import wraps

    @wraps(f)
    async def decorated(*args, **kwargs):
        if "user" not in session:
            return jsonify({"error": "unauthorized"}), 401
        return await f(*args, **kwargs)

    return decorated


@api_bp.route("/quotes")
@login_required
async def get_quotes():
    """Get current quotes for user's watchlist."""
    dm = current_app.data_manager  # type: ignore[attr-defined]
    if not dm:
        return jsonify({"error": "data manager unavailable"}), 503

    pool = await get_pool()
    repo = WatchlistRepository(pool)
    symbols = await repo.get(session["user"]["id"])

    quotes = []
    for symbol in symbols[:20]:
        try:
            q = await dm.get_quote(symbol)
            quotes.append(q)
        except Exception:
            quotes.append({"symbol": symbol, "price": 0, "change_pct": 0})

    return jsonify(quotes)


@api_bp.route("/sectors")
@login_required
async def get_sectors():
    """Get sector performance data."""
    dm = current_app.data_manager  # type: ignore[attr-defined]
    if not dm:
        return jsonify({"error": "data manager unavailable"}), 503

    try:
        sectors = await dm.get_sector_performance()
        return jsonify(sectors)
    except Exception:
        return jsonify([])


@api_bp.route("/macro")
@login_required
async def get_macro():
    """Get macro indicators snapshot."""
    dm = current_app.data_manager  # type: ignore[attr-defined]
    if not dm:
        return jsonify({"error": "data manager unavailable"}), 503

    try:
        data = await dm.get_macro_data()
        return jsonify(data)
    except Exception:
        return jsonify({})


@api_bp.route("/news")
@login_required
async def get_news():
    """Get latest news."""
    dm = current_app.data_manager  # type: ignore[attr-defined]
    if not dm:
        return jsonify({"error": "data manager unavailable"}), 503

    try:
        articles = await dm.get_news(limit=10)
        return jsonify(articles)
    except Exception:
        return jsonify([])
