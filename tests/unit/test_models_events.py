"""
Event model tests (FOUND-06): verify RawEvent and NormalizedEvent Pydantic v2 models.
"""
import pytest


def _import_models():
    try:
        from src.shared.models.events import NormalizedEvent, RawEvent
        return RawEvent, NormalizedEvent
    except ImportError as e:
        pytest.skip(f"events models not yet implemented: {e}")


def test_raw_event_valid():
    """RawEvent must instantiate with valid source."""
    RawEvent, _ = _import_models()
    event = RawEvent(event_id="e1", source="fireflies", raw_payload={"text": "test"})
    assert event.event_id == "e1"
    assert event.source == "fireflies"


def test_raw_event_invalid_source():
    """RawEvent must reject source='slack' (not in Literal)."""
    from pydantic import ValidationError
    RawEvent, _ = _import_models()
    with pytest.raises(ValidationError):
        RawEvent(event_id="e1", source="slack", raw_payload={})


def test_normalized_event_valid():
    """NormalizedEvent must instantiate with all required fields."""
    _, NormalizedEvent = _import_models()
    event = NormalizedEvent(
        event_id="e2",
        source="fireflies",
        event_type="material_change",
        summary="Window material changed from aluminum to wood",
    )
    assert event.event_id == "e2"
    assert event.summary == "Window material changed from aluminum to wood"


def test_normalized_event_empty_summary():
    """NormalizedEvent must reject an empty summary."""
    from pydantic import ValidationError
    _, NormalizedEvent = _import_models()
    with pytest.raises(ValidationError):
        NormalizedEvent(
            event_id="e3",
            source="acc",
            event_type="material_change",
            summary="",
        )


def test_normalized_event_extra_fields_forbidden():
    """NormalizedEvent must reject extra fields (extra='forbid')."""
    from pydantic import ValidationError
    _, NormalizedEvent = _import_models()
    with pytest.raises(ValidationError):
        NormalizedEvent(
            event_id="e4",
            source="gmail",
            event_type="material_change",
            summary="Valid summary",
            unexpected_field="should fail",
        )
