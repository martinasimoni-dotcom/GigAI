"""
GigAI FastAPI application entry point.
Registers all input-layer webhook routers and exposes the ASGI app.
"""
import asyncio
import logging

from fastapi import FastAPI

from src.input.webhooks import fireflies, acc
from src.api.routes import router as output_router
from src.api.demo import router as demo_router
from src.api.middleware import add_middleware

logger = logging.getLogger(__name__)

POLL_INTERVAL = 60  # seconds between each Fireflies + Gmail poll


def _ensure_db_tables() -> None:
    """Create tables required by the pollers if they don't exist yet."""
    from src.shared.db.postgres import get_connection, release_connection
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS processed_events (
                    id SERIAL PRIMARY KEY,
                    source TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE (source, source_id)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_chunks (
                    id SERIAL PRIMARY KEY,
                    content TEXT NOT NULL,
                    embedding vector(1024),
                    source TEXT,
                    metadata JSONB,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
        conn.commit()
        logger.info("DB tables verified/created.")
    except Exception as exc:
        logger.warning("DB table creation skipped (vector extension may not be ready): %s", exc)
        conn.rollback()
    finally:
        release_connection(conn)


async def _polling_loop() -> None:
    """Background task: poll Fireflies and Gmail every POLL_INTERVAL seconds."""
    from src.input.pollers import fireflies_poller, gmail_poller

    logger.info("Polling loop started — interval=%ds", POLL_INTERVAL)
    while True:
        try:
            ff_count = fireflies_poller.poll_once()
            if ff_count:
                logger.info("Fireflies: %d new transcript(s) processed", ff_count)
        except Exception as exc:
            logger.error("Fireflies poller error: %s", exc)

        try:
            gm_count = gmail_poller.poll_once()
            if gm_count:
                logger.info("Gmail: %d new email(s) processed", gm_count)
        except Exception as exc:
            logger.error("Gmail poller error: %s", exc)

        await asyncio.sleep(POLL_INTERVAL)


def _validate_startup() -> None:
    """
    Validate required environment variables and dependencies at startup.
    Logs warnings for missing optional services so operators know what is disabled.
    Raises RuntimeError if a hard requirement (Anthropic, Voyage, DB) is missing.
    """
    from config.settings import settings

    # Hard requirements — app cannot function without these
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set. LLM calls will fail.")
    if not settings.voyage_api_key:
        raise RuntimeError("VOYAGE_API_KEY is not set. Embedding calls will fail.")
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set. Database operations will fail.")

    # Soft requirements — log warnings so operators know features are disabled
    if not settings.google_cloud_project:
        logger.warning(
            "GOOGLE_CLOUD_PROJECT not set — Pub/Sub event publishing is disabled. "
            "Webhooks will fail when they try to publish events."
        )
    if not settings.acc_client_id or not settings.acc_client_secret:
        logger.warning(
            "ACC_CLIENT_ID / ACC_CLIENT_SECRET not set — "
            "ACC floor plan enrichment and issue creation are disabled."
        )
    if not settings.gmail_client_id or not settings.gmail_client_secret or not settings.gmail_refresh_token:
        logger.warning(
            "GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET / GMAIL_REFRESH_TOKEN not set — "
            "email and calendar actions will be skipped."
        )

    logger.info("GigAI startup validation passed.")


app = FastAPI(
    title="GigAI",
    description="Material Change Coordination Automation — Input Layer",
    version="1.0.0",
)

# Register webhook routers
app.include_router(fireflies.router)
app.include_router(acc.router)

# Register output API router
app.include_router(output_router)

# Register demo trigger router
app.include_router(demo_router)

# Apply middleware (CORS, API key auth, global error handler)
add_middleware(app)


@app.on_event("startup")
async def on_startup() -> None:
    """Run startup validation, create DB tables, and start background pollers."""
    _validate_startup()
    _ensure_db_tables()
    asyncio.create_task(_polling_loop())


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}
