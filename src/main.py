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


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}
