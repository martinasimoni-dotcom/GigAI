"""
Wave 0 test stubs for INPUT-01 (Fireflies webhook) and INPUT-02 (ACC webhook).
All tests are skipped until implementation is complete.
"""
import pytest

pytest_plugins = ("anyio",)

try:
    from httpx import AsyncClient
    from src.main import app
    IMPORT_OK = True
except (ImportError, Exception):
    IMPORT_OK = False

pytestmark = pytest.mark.skipif(not IMPORT_OK, reason="src.main not implemented yet")


@pytest.mark.anyio
async def test_fireflies_valid():
    """POST /webhooks/fireflies with valid payload returns 200 with status ok and message_id."""
    pytest.skip("not implemented")


@pytest.mark.anyio
async def test_fireflies_invalid():
    """POST /webhooks/fireflies with empty payload returns 400."""
    pytest.skip("not implemented")


@pytest.mark.anyio
async def test_acc_valid():
    """POST /webhooks/acc with valid payload returns 200."""
    pytest.skip("not implemented")


@pytest.mark.anyio
async def test_acc_invalid():
    """POST /webhooks/acc with empty payload returns 400."""
    pytest.skip("not implemented")
