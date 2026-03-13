"""
Wave 0 test stubs for CTX-02: Historical Retrieval.

Tests are collectable before implementation exists.
Guards with Path.exists() to avoid ValidationError at collection time.
Real assertions are added in Plan 02.
"""
import sys
from pathlib import Path

import pytest

# Wave 0 guard: check if implementation file exists and has content
_IMPL_PATH = Path(__file__).parent.parent.parent / "src" / "system" / "context" / "historical.py"
IMPL_AVAILABLE = _IMPL_PATH.exists() and _IMPL_PATH.stat().st_size > 10

pytestmark = pytest.mark.skipif(
    not IMPL_AVAILABLE,
    reason="src/system/context/historical.py not yet implemented",
)


@pytest.fixture(autouse=True)
def _setup_env(monkeypatch):
    """Set required env vars and reset module cache for clean isolation."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    monkeypatch.setenv("VOYAGE_API_KEY", "test-voyage-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")

    # Pop module cache so each test gets a fresh import
    for mod in ["src.system.context.historical", "src.system.context", "config.settings"]:
        sys.modules.pop(mod, None)

    yield

    # Clean up after test
    for mod in ["src.system.context.historical", "src.system.context", "config.settings"]:
        sys.modules.pop(mod, None)


def _make_event():
    """Return a NormalizedEvent for the demo scenario (aluminum -> wood, 3rd floor, 12 units)."""
    from src.shared.models.events import NormalizedEvent

    return NormalizedEvent(
        event_id="e-demo",
        source="fireflies",
        event_type="material_change",
        material_original="aluminum",
        material_new="wood",
        location="3rd floor",
        quantity=12,
        summary="Change third-floor windows from aluminum to wood, 12 units.",
    )


def test_retrieve_historical_returns_list():
    """retrieve_historical() should return a list."""
    from src.system.context.historical import retrieve_historical  # noqa: F401
    assert True


def test_retrieve_historical_returns_historical_match_instances():
    """Each item in result should be a HistoricalMatch instance."""
    assert True


def test_retrieve_historical_sorted_by_similarity():
    """Results should be sorted by similarity descending."""
    assert True


def test_retrieve_historical_outcome_from_metadata():
    """HistoricalMatch.outcome should be populated from metadata['outcome']."""
    assert True


def test_retrieve_historical_empty_db_returns_empty_list():
    """When search() returns [], retrieve_historical() should return []."""
    assert True
