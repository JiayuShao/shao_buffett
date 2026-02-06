"""Web alerts management routes."""

from quart import Blueprint, request, session, redirect, url_for, jsonify
from storage.repositories.alert_repo import AlertRepository
from storage.database import get_pool
from utils.formatting import validate_ticker

alerts_bp = Blueprint("alerts_routes", __name__)


def login_required(f):
    from functools import wraps

    @wraps(f)
    async def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("auth.login"))
        return await f(*args, **kwargs)

    return decorated


@alerts_bp.route("/")
@login_required
async def alerts_page():
    pool = await get_pool()
    repo = AlertRepository(pool)
    alerts = await repo.get_active(session["user"]["id"])
    return jsonify([{
        "id": a["id"],
        "symbol": a["symbol"],
        "condition": a["condition"],
        "threshold": float(a["threshold"]),
    } for a in alerts])


@alerts_bp.route("/create", methods=["POST"])
@login_required
async def create_alert():
    data = await request.get_json()
    symbol = validate_ticker(data.get("symbol", ""))
    if not symbol:
        return jsonify({"error": "Invalid symbol"}), 400

    pool = await get_pool()
    repo = AlertRepository(pool)
    alert_id = await repo.create(
        session["user"]["id"],
        symbol,
        data.get("condition", "above"),
        float(data.get("threshold", 0)),
    )

    if alert_id:
        return jsonify({"id": alert_id})
    return jsonify({"error": "Alert limit reached"}), 400


@alerts_bp.route("/delete/<int:alert_id>", methods=["POST"])
@login_required
async def delete_alert(alert_id: int):
    pool = await get_pool()
    repo = AlertRepository(pool)
    removed = await repo.remove(alert_id, session["user"]["id"])
    return jsonify({"removed": removed})
