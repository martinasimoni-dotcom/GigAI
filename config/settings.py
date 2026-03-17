"""
Application settings loaded from environment variables.
Required fields (no default) fail fast at startup if missing.
"""
import logging

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Required fields (no default = fails fast if missing) ---
    anthropic_api_key: str
    voyage_api_key: str
    database_url: str

    # --- Google Cloud ---
    google_cloud_project: str = ""
    pubsub_topic_raw_events: str = "raw-events"
    pubsub_topic_normalized_events: str = "normalized-events"
    pubsub_topic_enriched_events: str = "enriched-events"
    pubsub_topic_signals: str = "signals"

    # --- Autodesk Construction Cloud ---
    acc_client_id: str = ""
    acc_client_secret: str = ""

    # --- External services ---
    fireflies_api_key: str = ""
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    gmail_refresh_token: str = ""
    google_calendar_id: str = "primary"


settings = Settings()
