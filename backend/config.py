from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

# Resolve .env from the project root (one level above this file's directory)
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):

    # -------------------------------------------------------------------------
    # Anthropic Claude
    # -------------------------------------------------------------------------
    ANTHROPIC_API_KEY: str
    CLAUDE_HAIKU_MODEL: str = "claude-haiku-4-5-20251001"
    CLAUDE_SONNET_MODEL: str = "claude-sonnet-4-6"

    # -------------------------------------------------------------------------
    # Autodesk Construction Cloud (ACC)
    # -------------------------------------------------------------------------
    ACC_CLIENT_ID: str
    ACC_CLIENT_SECRET: str
    ACC_ACCESS_TOKEN: Optional[str] = None   # short-lived JWT — paste from Postman
    ACC_REFRESH_TOKEN: Optional[str] = None  # long-lived — paste from Postman, auto-refreshed
    ACC_HUB_ID: Optional[str] = None
    ACC_PROJECT_ID: Optional[str] = None
    ACC_CONTAINER_ID: Optional[str] = None
    ACC_REGION: str = "EMEA"  # "US" or "EMEA" — project is hosted on acc.autodesk.eu

    # -------------------------------------------------------------------------
    # Gmail API
    # -------------------------------------------------------------------------
    GMAIL_ENABLED: bool = False
    GMAIL_CLIENT_ID: Optional[str] = None
    GMAIL_CLIENT_SECRET: Optional[str] = None
    GMAIL_REFRESH_TOKEN: Optional[str] = None
    GMAIL_FROM_EMAIL: str = "gigai@yourdomain.com"
    GMAIL_FROM_NAME: str = "GigAI Material Coordinator"

    # -------------------------------------------------------------------------
    # Google Calendar API (shares Gmail OAuth credentials)
    # -------------------------------------------------------------------------
    GOOGLE_CALENDAR_ENABLED: bool = False
    GOOGLE_CALENDAR_ID: str = "primary"

    # -------------------------------------------------------------------------
    # Google Cloud Platform (GCP) — only required for Pub/Sub
    # -------------------------------------------------------------------------
    GCP_PROJECT_ID: Optional[str] = None
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None
    PUBSUB_TOPIC_EVENTS: str = "gigai-events"
    PUBSUB_SUBSCRIPTION_EVENTS: str = "gigai-events-sub"

    # -------------------------------------------------------------------------
    # Voyage AI (vector embeddings)
    # -------------------------------------------------------------------------
    VOYAGE_AI_ENABLED: bool = False
    VOYAGE_API_KEY: Optional[str] = None
    VOYAGE_MODEL: str = "voyage-2"

    # -------------------------------------------------------------------------
    # Fireflies.ai (meeting transcripts via webhook)
    # -------------------------------------------------------------------------
    FIREFLIES_ENABLED: bool = False
    FIREFLIES_WEBHOOK_SECRET: Optional[str] = None

    # -------------------------------------------------------------------------
    # Database
    # Uses psycopg v3 driver — connection string must start with
    # postgresql+psycopg:// (not postgresql+psycopg2://)
    # -------------------------------------------------------------------------
    DATABASE_URL: str = "postgresql+psycopg://gigai:gigai@localhost:5432/gigai"

    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------
    APP_PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:5173"
    CONFIDENCE_AUTO_APPROVE_THRESHOLD: float = 0.80

    # -------------------------------------------------------------------------
    # ACC Polling (replaces webhooks — no ngrok required)
    # -------------------------------------------------------------------------
    POLLING_ENABLED: bool = True
    POLLING_INTERVAL_MINUTES: int = 5

    # -------------------------------------------------------------------------
    # Feature flags
    # -------------------------------------------------------------------------
    ENABLE_AUTO_APPROVE: bool = True
    ENABLE_WEBSOCKET_NOTIFICATIONS: bool = True
    ENABLE_EMAIL_NOTIFICATIONS: bool = True
    ENABLE_ACC_NOTIFICATIONS: bool = True

    # -------------------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------------------
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False

    # -------------------------------------------------------------------------
    # Security
    # -------------------------------------------------------------------------
    JWT_SECRET: str = "changeme"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000,http://localhost:8001,http://127.0.0.1:8001"

    class Config:
        env_file = str(_ENV_FILE)


settings = Settings()
