"""FastAPI middleware (OUT-12): CORS, API key auth, global error handler."""
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

PUBLIC_PATHS = {"/api/health", "/health"}


class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        api_key = os.getenv("API_KEY")
        if not api_key:
            return await call_next(request)
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)
        provided = request.headers.get("X-API-Key", "")
        if provided != api_key:
            logger.warning("Unauthorized request to %s", request.url.path)
            return JSONResponse(
                {"error": "Unauthorized", "type": "AuthenticationError"},
                status_code=401,
            )
        return await call_next(request)


def add_middleware(app: FastAPI) -> None:
    """Apply all middleware and exception handlers to the app."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(APIKeyMiddleware)

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        return JSONResponse(
            {"error": str(exc), "type": type(exc).__name__},
            status_code=500,
        )
