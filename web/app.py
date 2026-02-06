"""Quart app factory with Discord OAuth setup."""

import structlog
from quart import Quart
from config.settings import settings

log = structlog.get_logger(__name__)


def create_app(bot=None, data_manager=None) -> Quart:
    """Create and configure the Quart web application."""
    app = Quart(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.secret_key = settings.web_secret_key

    # Store references for routes
    app.bot = bot  # type: ignore[attr-defined]
    app.data_manager = data_manager  # type: ignore[attr-defined]

    # Register blueprints
    from web.auth import auth_bp
    from web.routes.dashboard import dashboard_bp
    from web.routes.watchlist import watchlist_bp
    from web.routes.alerts import alerts_bp
    from web.routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(watchlist_bp, url_prefix="/watchlist")
    app.register_blueprint(alerts_bp, url_prefix="/alerts")
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.route("/")
    async def index():
        from quart import session, redirect, url_for, render_template
        if "user" in session:
            return redirect(url_for("dashboard_routes.dashboard_page"))
        return await render_template("login.html")

    @app.route("/health")
    async def health():
        return {"status": "ok"}, 200

    return app


async def start_web(bot=None, data_manager=None) -> None:
    """Start the web dashboard."""
    app = create_app(bot=bot, data_manager=data_manager)
    log.info("starting_web_dashboard", port=settings.web_port)
    await app.run_task(host="0.0.0.0", port=settings.web_port)
