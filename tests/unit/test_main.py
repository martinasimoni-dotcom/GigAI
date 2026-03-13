"""
Wave 0 test stubs for FastAPI app wiring (health endpoint and router registration).
All tests are skipped until implementation is complete.
"""
import pytest

try:
    from src.main import app
    IMPORT_OK = True
except (ImportError, Exception):
    IMPORT_OK = False

pytestmark = pytest.mark.skipif(not IMPORT_OK, reason="src.main not implemented yet")


def test_health_endpoint():
    """GET /health returns {status: ok}."""
    pytest.skip("not implemented")


def test_routers_included():
    """FastAPI app has routes matching /webhooks/fireflies and /webhooks/acc."""
    pytest.skip("not implemented")
