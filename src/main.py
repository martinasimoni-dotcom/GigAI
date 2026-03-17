"""
GigAI FastAPI application entry point.
Registers all input-layer webhook routers and exposes the ASGI app.
"""
import logging

from fastapi import FastAPI

from src.input.webhooks import fireflies, acc
from src.api.routes import router as output_router
from src.api.middleware import add_middleware

logger = logging.getLogger(__name__)


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

# Apply middleware (CORS, API key auth, global error handler)
add_middleware(app)


@app.on_event("startup")
async def on_startup() -> None:
    """Run startup validation when the app boots."""
    _validate_startup()


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}
