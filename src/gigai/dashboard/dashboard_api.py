"""GigAI Dashboard API application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gigai.dashboard.routers import dashboard, health, integrations, meetings, tasks


def create_dashboard_app() -> FastAPI:
    """Create FastAPI app with dashboard endpoints."""

    app = FastAPI(
        title="GigAI Meeting Intelligence Dashboard API",
        description="Real-time dashboard for architectural meeting coordination",
        version="0.3.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:8000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(meetings.router)
    app.include_router(tasks.router)
    app.include_router(dashboard.router)
    app.include_router(integrations.router)

    return app


app = create_dashboard_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "gigai.dashboard.dashboard_api:create_dashboard_app",
        factory=True,
        host="0.0.0.0",
        port=8000,
    )
