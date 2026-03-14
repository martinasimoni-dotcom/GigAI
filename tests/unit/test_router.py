"""
Unit tests for router module (PROC-04, PROC-05).
Stubs are collectable before implementation; tests skip until router.py has content.
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_IMPL_PATH = (
    Path(__file__).parent.parent.parent
    / "src" / "system" / "data_processing" / "router.py"
)
IMPL_AVAILABLE = _IMPL_PATH.exists() and _IMPL_PATH.stat().st_size > 10

pytestmark = pytest.mark.skipif(
    not IMPL_AVAILABLE, reason="router.py not yet implemented"
)


@pytest.fixture(autouse=True)
def _setup_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("VOYAGE_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    for mod in [
        "src.system.data_processing.router",
        "src.system.data_processing",
        "config.settings",
    ]:
        sys.modules.pop(mod, None)


def _make_event(**kwargs):
    from src.shared.models.events import NormalizedEvent
    defaults = dict(
        event_id="e1", source="fireflies", event_type="material_change",
        location="3rd floor", summary="Change windows.", confidence=85,
    )
    defaults.update(kwargs)
    return NormalizedEvent(**defaults)


_ROUTING_MATERIAL = json.dumps({"event_type": "material_change", "confidence": 90})
_ROUTING_OTHER = json.dumps({"event_type": "other", "confidence": 40})


# --- PROC-05: route_event() happy path ---

def test_route_event_returns_routed_event():
    """route_event() returns RoutedEvent with event_type and loaded config."""
    from src.system.data_processing import router

    mock_publisher = MagicMock()
    mock_publisher.topic_path.return_value = "projects/test/topics/normalized-events"
    mock_future = MagicMock()
    mock_future.result.return_value = "msg-id-1"
    mock_publisher.publish.return_value = mock_future

    with patch.object(router, "call_haiku", return_value=_ROUTING_MATERIAL), \
         patch("google.cloud.pubsub_v1.PublisherClient", return_value=mock_publisher):
        result = router.route_event(_make_event())

    assert result.event_type == "material_change"
    assert result.config.event_type == "material_change"
    assert result.config_path.endswith("material_change.yaml")


def test_route_event_fallback_to_other_on_unknown_type():
    """router falls back to 'other' when Haiku returns an unrecognised event_type."""
    from src.system.data_processing import router

    unknown_response = json.dumps({"event_type": "completely_unknown_type", "confidence": 30})

    mock_publisher = MagicMock()
    mock_publisher.topic_path.return_value = "projects/test/topics/normalized-events"
    mock_future = MagicMock()
    mock_future.result.return_value = "msg-id-2"
    mock_publisher.publish.return_value = mock_future

    with patch.object(router, "call_haiku", return_value=unknown_response), \
         patch("google.cloud.pubsub_v1.PublisherClient", return_value=mock_publisher):
        result = router.route_event(_make_event())

    assert result.event_type == "other"


def test_route_event_publishes_to_normalized_events():
    """route_event() calls publisher.publish() for the normalized-events topic."""
    from src.system.data_processing import router

    mock_publisher = MagicMock()
    mock_publisher.topic_path.return_value = "projects/test/topics/normalized-events"
    mock_future = MagicMock()
    mock_future.result.return_value = "msg-id-3"
    mock_publisher.publish.return_value = mock_future

    with patch.object(router, "call_haiku", return_value=_ROUTING_MATERIAL), \
         patch("google.cloud.pubsub_v1.PublisherClient", return_value=mock_publisher):
        router.route_event(_make_event())

    assert mock_publisher.publish.called


# --- PROC-04: routing prompt file content ---

def test_routing_prompt_file_exists():
    """config/prompts/routing.txt must exist and list all known event types."""
    prompt_path = (
        Path(__file__).parent.parent.parent / "config" / "prompts" / "routing.txt"
    )
    assert prompt_path.exists(), "routing.txt not found"
    content = prompt_path.read_text()
    for event_type in ["material_change", "schedule_update", "rfi_request", "other"]:
        assert event_type in content, f"'{event_type}' not found in routing.txt"


@pytest.mark.unit
def test_route_event_falls_back_when_yaml_config_missing(tmp_path):
    """route_event() falls back to other.yaml when the primary config YAML is missing."""
    import shutil
    from src.system.data_processing import router

    # Create a minimal config_dir with only other.yaml — no material_change.yaml
    config_dir = tmp_path / "event_types"
    config_dir.mkdir()

    # Copy real other.yaml from the project config
    real_config_dir = (
        Path(__file__).parent.parent.parent / "config" / "event_types"
    )
    shutil.copy(real_config_dir / "other.yaml", config_dir / "other.yaml")
    # Do NOT copy material_change.yaml — trigger the fallback

    mock_publisher = MagicMock()
    mock_publisher.topic_path.return_value = "projects/test/topics/normalized-events"
    mock_future = MagicMock()
    mock_future.result.return_value = "msg-id-fallback"
    mock_publisher.publish.return_value = mock_future

    # Haiku returns material_change but the YAML file is missing — router must fall back
    with patch.object(router, "call_haiku", return_value=_ROUTING_MATERIAL), \
         patch("google.cloud.pubsub_v1.PublisherClient", return_value=mock_publisher):
        result = router.route_event(_make_event(), config_dir=config_dir)

    assert result.event_type == "other"
    assert result.config.event_type == "other"


@pytest.mark.unit
def test_route_event_with_material_change_config_loads_enrichment_queries():
    """route_event() with material_change classification loads EventTypeConfig with queries."""
    from src.system.data_processing import router

    mock_publisher = MagicMock()
    mock_publisher.topic_path.return_value = "projects/test/topics/normalized-events"
    mock_future = MagicMock()
    mock_future.result.return_value = "msg-id-4"
    mock_publisher.publish.return_value = mock_future

    with patch.object(router, "call_haiku", return_value=_ROUTING_MATERIAL), \
         patch("google.cloud.pubsub_v1.PublisherClient", return_value=mock_publisher):
        result = router.route_event(_make_event())

    assert result.event_type == "material_change"
    assert isinstance(result.config.enrichment_queries, list)
    assert len(result.config.enrichment_queries) > 0
