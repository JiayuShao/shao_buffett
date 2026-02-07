"""Pydantic Settings for Shao Buffett configuration."""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # Discord
    discord_token: str
    discord_guild_id: int = 0
    notification_channel_id: int = 0

    # Anthropic
    anthropic_api_key: str

    # Financial APIs
    finnhub_api_key: str = ""
    fred_api_key: str = ""
    marketaux_api_key: str = ""
    fmp_api_key: str = ""

    # PostgreSQL
    database_url: str = "postgresql://shao_buffett:shao_buffett@localhost:5432/shao_buffett"

    # Web Dashboard
    web_secret_key: str = "change-me"
    discord_client_id: str = ""
    discord_client_secret: str = ""
    discord_redirect_uri: str = "http://localhost:5000/callback"
    web_port: int = 5000

    # Operational
    log_level: str = "INFO"
    opus_daily_budget: int = Field(default=20, description="Max Opus calls per day")

    # Default watchlist
    default_watchlist: list[str] = Field(
        default=["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"]
    )


settings = Settings()  # type: ignore[call-arg]
