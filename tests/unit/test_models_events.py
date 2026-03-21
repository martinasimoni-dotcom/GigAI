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


def test_normalized_event_new_fields_defaults():
    """New fields must have correct defaults."""
    _, NormalizedEvent = _import_models()
    event = NormalizedEvent(
        event_id="e5", source="acc", event_type="material_change", summary="test summary"
    )
    assert event.review_required is False
    assert event.confidence == 50
    assert event.estimated_cost is None


def test_normalized_event_confidence_bounds():
    """confidence must be 0-100 inclusive."""
    from pydantic import ValidationError
    _, NormalizedEvent = _import_models()
    # Valid bounds
    NormalizedEvent(event_id="e6", source="acc", event_type="mc", summary="s", confidence=0)
    NormalizedEvent(event_id="e7", source="acc", event_type="mc", summary="s", confidence=100)
    # Out of bounds
    with pytest.raises(ValidationError):
        NormalizedEvent(event_id="e8", source="acc", event_type="mc", summary="s", confidence=101)
    with pytest.raises(ValidationError):
        NormalizedEvent(event_id="e9", source="acc", event_type="mc", summary="s", confidence=-1)


def test_normalized_event_new_fields_set():
    """New fields accept explicit values."""
    _, NormalizedEvent = _import_models()
    event = NormalizedEvent(
        event_id="e10", source="acc", event_type="material_change", summary="test",
        review_required=True, confidence=65, estimated_cost=75000.0,
    )
    assert event.review_required is True
    assert event.confidence == 65
    assert event.estimated_cost == 75000.0
