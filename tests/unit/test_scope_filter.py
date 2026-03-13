"""
Unit tests for scope_filter module (PROC-03).
Stubs are collectable before implementation; tests skip until scope_filter.py has content.
"""
import sys
from pathlib import Path

import pytest

_IMPL_PATH = (
    Path(__file__).parent.parent.parent
    / "src" / "system" / "data_processing" / "scope_filter.py"
)
IMPL_AVAILABLE = _IMPL_PATH.exists() and _IMPL_PATH.stat().st_size > 10

pytestmark = pytest.mark.skipif(
    not IMPL_AVAILABLE, reason="scope_filter.py not yet implemented"
)


@pytest.fixture(autouse=True)
def _setup_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("VOYAGE_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    for mod in [
        "src.system.data_processing.scope_filter",
        "src.system.data_processing",
        "config.settings",
    ]:
        sys.modules.pop(mod, None)


_DEMO_SCOPE = {
    "locations": ["3rd floor", "third floor", "floor 3", "lobby", "basement"],
    "project_id": "demo_project",
}


def _make_event(**kwargs):
    from src.shared.models.events import NormalizedEvent
    defaults = dict(
        event_id="e1", source="fireflies", event_type="material_change",
        location="3rd floor", summary="Change windows.", confidence=85,
    )
    defaults.update(kwargs)
    return NormalizedEvent(**defaults)


# --- PROC-03: in-scope location ---

def test_filter_event_in_scope_passes():
    """Event with a known location passes the scope filter."""
    from src.system.data_processing import scope_filter
    event = _make_event(location="3rd floor")
    result = scope_filter.filter_event(event, _DEMO_SCOPE)
    assert result.passed is True
    assert result.escalate_immediately is False


def test_filter_event_out_of_scope_rejected():
    """Event at an unknown location is rejected with alert_pm=True."""
    from src.system.data_processing import scope_filter
    event = _make_event(location="neighboring property")
    result = scope_filter.filter_event(event, _DEMO_SCOPE)
    assert result.passed is False
    assert result.alert_pm is True
    assert "scope" in result.reason.lower() or "location" in result.reason.lower()


def test_filter_event_high_cost_escalates():
    """Event with estimated_cost > 50000 sets escalate_immediately=True."""
    from src.system.data_processing import scope_filter
    event = _make_event(location="3rd floor", estimated_cost=75000.0)
    result = scope_filter.filter_event(event, _DEMO_SCOPE)
    assert result.escalate_immediately is True


def test_filter_event_no_cost_no_escalation():
    """Event with no estimated_cost does not escalate."""
    from src.system.data_processing import scope_filter
    event = _make_event(location="3rd floor", estimated_cost=None)
    result = scope_filter.filter_event(event, _DEMO_SCOPE)
    assert result.escalate_immediately is False


def test_filter_event_returns_filter_result_model():
    """filter_event() returns a FilterResult with required fields."""
    from src.system.data_processing import scope_filter
    event = _make_event(location="lobby")
    result = scope_filter.filter_event(event, _DEMO_SCOPE)
    assert hasattr(result, "passed")
    assert hasattr(result, "reason")
    assert hasattr(result, "escalate_immediately")
    assert hasattr(result, "alert_pm")
