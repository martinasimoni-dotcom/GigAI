"""
EventTypeConfig model tests (FOUND-08): verify EventTypeConfig Pydantic v2 model.
"""
import pytest


def _import_model():
    try:
        from src.shared.models.config import EventTypeConfig
        return EventTypeConfig
    except ImportError as e:
        pytest.skip(f"config model not yet implemented: {e}")


def test_event_type_config_valid():
    """EventTypeConfig must instantiate with all required fields."""
    EventTypeConfig = _import_model()
    cfg = EventTypeConfig(
        event_type="material_change",
        rules_file="demo.yaml",
        allowed_signals=[],
        enrichment_queries=[],
        time_analysis_enabled=True,
    )
    assert cfg.event_type == "material_change"
    assert cfg.time_analysis_enabled is True


def test_event_type_config_defaults():
    """EventTypeConfig allowed_signals and enrichment_queries must default to []."""
    EventTypeConfig = _import_model()
    cfg = EventTypeConfig(
        event_type="schedule_update",
        rules_file="stub.yaml",
    )
    assert cfg.allowed_signals == []
    assert cfg.enrichment_queries == []
    assert cfg.time_analysis_enabled is False
