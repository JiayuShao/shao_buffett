"""Discord OAuth2 login/callback handling for Quart."""

import aiohttp
import structlog
from quart import Blueprint, redirect, request, session, url_for
from config.settings import settings

log = structlog.get_logger(__name__)

auth_bp = Blueprint("auth", __name__)

DISCORD_API_BASE = "https://discord.com/api/v10"
OAUTH2_AUTHORIZE = "https://discord.com/api/oauth2/authorize"
OAUTH2_TOKEN = f"{DISCORD_API_BASE}/oauth2/token"


def get_authorize_url() -> str:
    """Build the Discord OAuth2 authorization URL."""
    params = {
        "client_id": settings.discord_client_id,
        "redirect_uri": settings.discord_redirect_uri,
        "response_type": "code",
        "scope": "identify guilds",
    }
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{OAUTH2_AUTHORIZE}?{qs}"


@auth_bp.route("/login")
async def login():
    return redirect(get_authorize_url())


@auth_bp.route("/callback")
async def callback():
    code = request.args.get("code")
    if not code:
        return redirect(url_for("auth.login"))

    # Exchange code for token
    async with aiohttp.ClientSession() as http:
        async with http.post(
            OAUTH2_TOKEN,
            data={
                "client_id": settings.discord_client_id,
                "client_secret": settings.discord_client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.discord_redirect_uri,
                "scope": "identify guilds",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        ) as resp:
            if resp.status != 200:
                log.error("oauth_token_error", status=resp.status)
                return redirect(url_for("auth.login"))
            token_data = await resp.json()

        access_token = token_data.get("access_token")

        # Fetch user info
        async with http.get(
            f"{DISCORD_API_BASE}/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
        ) as resp:
            user_data = await resp.json()

    session["user"] = {
        "id": int(user_data["id"]),
        "username": user_data["username"],
        "avatar": user_data.get("avatar"),
        "discriminator": user_data.get("discriminator", "0"),
    }
    session["access_token"] = access_token

    log.info("user_logged_in", user=user_data["username"])
    return redirect(url_for("dashboard_routes.dashboard_page"))


@auth_bp.route("/logout")
async def logout():
    session.clear()
    return redirect("/")
