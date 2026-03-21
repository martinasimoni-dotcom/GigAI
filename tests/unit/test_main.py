"""
Unit tests for src/main.py FastAPI app wiring (INPUT-01, INPUT-02 integration).
Verifies /health endpoint and that all webhook routers are included.
"""
import sys
import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport

pytest_plugins = ("anyio",)


@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    """Run async tests only on asyncio — trio is not installed in this environment."""
    return request.param


@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    """Set required env vars and clear cached settings/app modules before each test.

    src.main imports src.input.webhooks.{fireflies,acc} which import
    src.input.pubsub which imports config.settings.  The module-level
    settings = Settings() singleton raises ValidationError if the required
    env vars are absent.  We must setenv + pop the cached modules so every
    test reimports with valid settings.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("VOYAGE_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    _MODS_TO_CLEAR = [
        "config.settings",
        "src.input.pubsub",
        "src.input.webhooks.fireflies",
        "src.input.webhooks.acc",
        "src.input.webhooks",
        "src.main",
    ]
    for mod in _MODS_TO_CLEAR:
        sys.modules.pop(mod, None)
    yield
    for mod in _MODS_TO_CLEAR:
        sys.modules.pop(mod, None)


@pytest.fixture
def app():
    from src.main import app as fastapi_app
    return fastapi_app


@pytest.mark.anyio
async def test_health_endpoint(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_routers_included(app):
    """Both webhook routes must be registered on the app."""
    routes = [route.path for route in app.routes]
    assert "/webhooks/fireflies" in routes, f"Missing /webhooks/fireflies. Routes: {routes}"
    assert "/webhooks/acc" in routes, f"Missing /webhooks/acc. Routes: {routes}"


def test_app_is_fastapi(app):
    from fastapi import FastAPI
    assert isinstance(app, FastAPI)


@pytest.mark.anyio
async def test_fireflies_route_via_app(app):
    """End-to-end: POST /webhooks/fireflies returns 200 through main app."""
    # When Pub/Sub is not configured, the webhook runs the pipeline directly.
    # When Pub/Sub is configured, it publishes to Pub/Sub via publish_event.
    with patch("src.pipeline.runner.run_pipeline", return_value={"id": "prop-001"}) as mock_pipe, \
         patch("src.input.pubsub.publish_event", return_value="msg-id-1"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/webhooks/fireflies", json={"transcript": "window change"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.anyio
async def test_acc_route_via_app(app):
    """End-to-end: POST /webhooks/acc returns 200 through main app."""
    with patch("src.input.webhooks.acc.publish_event", return_value="msg-id-2"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/webhooks/acc", json={"eventType": "material_change"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
