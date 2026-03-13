"""
Unit tests for webhook endpoints (INPUT-01, INPUT-02).
Uses httpx.AsyncClient to POST to the FastAPI app with publish_event mocked.
"""
import sys
import pytest
from unittest.mock import patch, MagicMock
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
    test reimports with valid settings — matching the pattern established in
    test_pubsub.py and test_postgres.py.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("VOYAGE_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    _MODS_TO_CLEAR = [
        "config.settings",
        "src.input.pubsub",
        "src.input.webhooks.fireflies",
        "src.input.webhooks.acc",
        "src.input.webhooks",  # must clear package so submodule attrs are re-bound
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


@pytest.fixture
def mock_publish():
    """Mock publish_event to return a fixed message_id without hitting Pub/Sub."""
    with patch("src.input.webhooks.fireflies.publish_event", return_value="test-message-id") as m_f, \
         patch("src.input.webhooks.acc.publish_event", return_value="test-message-id") as m_a:
        yield {"fireflies": m_f, "acc": m_a}


@pytest.mark.anyio
async def test_fireflies_valid(app, mock_publish):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/webhooks/fireflies", json={"transcript": "window change", "meeting": "site call"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "message_id" in body


@pytest.mark.anyio
async def test_fireflies_with_meeting_only(app, mock_publish):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/webhooks/fireflies", json={"meeting": "budget discussion"})
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_fireflies_invalid_empty(app, mock_publish):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/webhooks/fireflies", json={})
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_fireflies_invalid_wrong_keys(app, mock_publish):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/webhooks/fireflies", json={"unrelated": "data", "foo": "bar"})
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_fireflies_publishes_raw_event(app, mock_publish):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/webhooks/fireflies", json={"transcript": "material change"})
    mock_publish["fireflies"].assert_called_once()
    call_args = mock_publish["fireflies"].call_args[0][0]
    assert call_args.source == "fireflies"
    assert call_args.raw_payload == {"transcript": "material change"}


@pytest.mark.anyio
async def test_acc_valid(app, mock_publish):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/webhooks/acc", json={"eventType": "material_change", "resource": "floors"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "message_id" in body


@pytest.mark.anyio
async def test_acc_valid_minimal(app, mock_publish):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/webhooks/acc", json={"type": "update"})
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_acc_invalid_empty(app, mock_publish):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/webhooks/acc", json={})
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_acc_publishes_raw_event(app, mock_publish):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/webhooks/acc", json={"eventType": "material_change"})
    mock_publish["acc"].assert_called_once()
    call_args = mock_publish["acc"].call_args[0][0]
    assert call_args.source == "acc"
