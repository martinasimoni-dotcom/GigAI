"""
Unit tests for src/input/pubsub.publish_event().
Pub/Sub client is mocked — no GCP credentials or live topic needed.
"""
import json
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest

from src.shared.models.events import RawEvent


@pytest.fixture(autouse=True)
def reset_pubsub_globals(monkeypatch):
    """Set required env vars, clear cached modules, and reset publisher singleton between tests."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("VOYAGE_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    # Remove cached settings + pubsub modules so they reimport with the correct env
    sys.modules.pop("config.settings", None)
    sys.modules.pop("src.input.pubsub", None)
    import src.input.pubsub as pubsub_module
    pubsub_module._publisher = None
    pubsub_module._topic_path = None
    yield
    pubsub_module._publisher = None
    pubsub_module._topic_path = None


def _make_raw_event(source="fireflies") -> RawEvent:
    return RawEvent(
        event_id="test-123",
        source=source,
        raw_payload={"transcript": "test content"},
    )


def test_publish_event(mock_pubsub_publisher):
    """publish_event() calls publisher.publish() once and returns message_id."""
    import src.input.pubsub as pubsub_module
    with patch.object(pubsub_module.pubsub_v1, "PublisherClient", return_value=mock_pubsub_publisher):
        from src.input.pubsub import publish_event
        result = publish_event(_make_raw_event("fireflies"))
    assert result == "test-message-id"
    mock_pubsub_publisher.publish.assert_called_once()


def test_publish_event_bytes(mock_pubsub_publisher):
    """Data argument to publisher.publish() must be bytes, not str."""
    import src.input.pubsub as pubsub_module
    with patch.object(pubsub_module.pubsub_v1, "PublisherClient", return_value=mock_pubsub_publisher):
        from src.input.pubsub import publish_event
        publish_event(_make_raw_event())
    call_args = mock_pubsub_publisher.publish.call_args
    data_arg = call_args[0][1]  # positional arg 2
    assert isinstance(data_arg, bytes), f"Expected bytes, got {type(data_arg)}"


def test_publish_event_json_serializable(mock_pubsub_publisher):
    """RawEvent with datetime received_at does not cause TypeError during serialization."""
    import src.input.pubsub as pubsub_module
    event = RawEvent(
        event_id="dt-test",
        source="acc",
        raw_payload={"eventType": "material_change"},
        received_at=datetime(2026, 3, 13, 12, 0, 0, tzinfo=timezone.utc),
    )
    with patch.object(pubsub_module.pubsub_v1, "PublisherClient", return_value=mock_pubsub_publisher):
        from src.input.pubsub import publish_event
        # Should not raise TypeError: Object of type datetime is not JSON serializable
        result = publish_event(event)
    assert result == "test-message-id"
    # Verify data is valid JSON bytes containing an ISO string for received_at
    call_data = mock_pubsub_publisher.publish.call_args[0][1]
    parsed = json.loads(call_data.decode("utf-8"))
    assert "received_at" in parsed
    assert isinstance(parsed["received_at"], str)  # datetime converted to ISO string


def test_publish_event_source_attribute(mock_pubsub_publisher):
    """source is passed as a Pub/Sub message attribute for filtering."""
    import src.input.pubsub as pubsub_module
    with patch.object(pubsub_module.pubsub_v1, "PublisherClient", return_value=mock_pubsub_publisher):
        from src.input.pubsub import publish_event
        publish_event(_make_raw_event("gmail"))
    call_kwargs = mock_pubsub_publisher.publish.call_args[1]
    assert call_kwargs.get("source") == "gmail"
