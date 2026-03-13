"""
Wave 0 test stub for the publish_event Pub/Sub helper.
Test is skipped until implementation is complete.
"""
import pytest

try:
    from src.input.pubsub import publish_event
    IMPORT_OK = True
except (ImportError, Exception):
    IMPORT_OK = False

pytestmark = pytest.mark.skipif(not IMPORT_OK, reason="pubsub not implemented yet")


def test_publish_event():
    """publish_event calls publisher.publish() with bytes and source attribute and returns message id."""
    pytest.skip("not implemented")
