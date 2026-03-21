"""
GigAI FastAPI application entry point.
Registers all routers and exposes the ASGI app.
"""
import asyncio
import logging

from fastapi import FastAPI

from src.input.webhooks import fireflies, acc
from src.api.routes import router as output_router
from src.api.projects import router as projects_router
from src.api.employees import router as employees_router
from src.api.schedule import router as schedule_router
from src.inbox.routes import router as inbox_router
from src.rfi.routes import router as rfi_router
from src.decisions.routes import router as decisions_router
from src.api.middleware import add_middleware

logger = logging.getLogger(__name__)



def _ensure_db_tables() -> None:
    """Create tables required by the system if they don't exist yet."""
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
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ai_runs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    event_id TEXT,
                    run_type TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    prompt_summary TEXT,
                    response_summary TEXT,
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    latency_ms INTEGER,
                    success BOOLEAN NOT NULL DEFAULT TRUE,
                    error_message TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS proposals (
                    proposal_id UUID PRIMARY KEY,
                    event_id UUID,
                    alert JSONB,
                    actions JSONB,
                    confidence_score FLOAT,
                    recommendation TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id SERIAL PRIMARY KEY,
                    proposal_id UUID,
                    decision TEXT NOT NULL,
                    rejection_reason TEXT,
                    recorded_at TIMESTAMPTZ DEFAULT NOW()
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

    from config.settings import settings
    logger.info("Polling loop started — interval=%ds", settings.poll_interval_seconds)
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

        await asyncio.sleep(settings.poll_interval_seconds)


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
            "Pipeline will run events synchronously."
        )
    if not settings.acc_client_id or not settings.acc_client_secret:
        logger.warning(
            "ACC_CLIENT_ID / ACC_CLIENT_SECRET not set — "
            "Using ACC fallback data. Configure credentials for live ACC integration."
        )
    if not settings.gmail_client_id or not settings.gmail_client_secret or not settings.gmail_refresh_token:
        logger.warning(
            "GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET / GMAIL_REFRESH_TOKEN not set — "
            "email and calendar actions will be skipped."
        )

    logger.info("GigAI startup validation passed.")


app = FastAPI(
    title="GigAI",
    description="AI-Powered Construction Material Change Coordination Platform",
    version="1.0.0",
)

# Register webhook routers
app.include_router(fireflies.router)
app.include_router(acc.router)

# Register core API routers
app.include_router(output_router)
app.include_router(projects_router)
app.include_router(employees_router)
app.include_router(schedule_router)
app.include_router(inbox_router)
app.include_router(rfi_router)
app.include_router(decisions_router)

# Apply middleware (CORS, API key auth, global error handler)
add_middleware(app)


@app.on_event("startup")
async def on_startup() -> None:
    """Run startup validation, create DB tables, and start background pollers."""
    _validate_startup()
    _ensure_db_tables()

    # Seed inbox with sample data
    try:
        from src.inbox.seed import seed_inbox
        count = seed_inbox()
        logger.info("Unified inbox seeded with %d items", count)
    except Exception as exc:
        logger.warning("Inbox seed skipped: %s", exc)

    # Seed RFI queue (auto-detects from inbox + adds lifecycle demos)
    try:
        from src.rfi.seed import seed_rfis
        rfi_count = seed_rfis()
        logger.info("RFI queue seeded with %d items", rfi_count)
    except Exception as exc:
        logger.warning("RFI seed skipped: %s", exc)

    # Seed decision tracker (auto-detects from inbox)
    try:
        from src.decisions.seed import seed_decisions
        dec_count = seed_decisions()
        logger.info("Decision tracker seeded with %d decisions", dec_count)
    except Exception as exc:
        logger.warning("Decision seed skipped: %s", exc)

    asyncio.create_task(_polling_loop())


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}
