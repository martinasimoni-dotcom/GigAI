"""
Unit tests for CTX-02 (retrieve_historical) and CTX-01 (enrich_event).

All tests use mocked search() — no live DB or API calls required.
"""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Wave 0 guard: check if implementation file exists and has content
_IMPL_PATH = Path(__file__).parent.parent.parent / "src" / "system" / "context" / "enrichment.py"
IMPL_AVAILABLE = _IMPL_PATH.exists() and _IMPL_PATH.stat().st_size > 10

pytestmark = pytest.mark.skipif(
    not IMPL_AVAILABLE,
    reason="src/system/context/enrichment.py not yet implemented",
)


@pytest.fixture(autouse=True)
def _setup_env(monkeypatch):
    """Set required env vars and reset module cache for clean isolation."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    monkeypatch.setenv("VOYAGE_API_KEY", "test-voyage-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")

    # Pop module cache so each test gets a fresh import
    for mod in [
        "src.system.context.enrichment",
        "src.system.context.historical",
        "src.system.context",
        "config.settings",
    ]:
        sys.modules.pop(mod, None)

    yield

    # Clean up after test
    for mod in [
        "src.system.context.enrichment",
        "src.system.context.historical",
        "src.system.context",
        "config.settings",
    ]:
        sys.modules.pop(mod, None)


def _mock_row(content, source="knowledge_folder/historical_patterns", similarity=0.9, metadata=None):
    return {
        "id": content[:8],
        "content": content,
        "source": source,
        "metadata": metadata or {},
        "similarity": similarity,
    }


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


# ---------------------------------------------------------------------------
# CTX-02: retrieve_historical tests
# ---------------------------------------------------------------------------


def test_retrieve_historical_returns_list():
    """retrieve_historical() should return a list with the mocked result."""
    import src.system.context.historical as historical
    from src.system.context.historical import retrieve_historical, HistoricalMatch

    mock_rows = [
        _mock_row(
            "EVT-012 aluminum to wood 12 units",
            metadata={"outcome": "approved", "success_rate": 0.95},
        )
    ]
    with patch.object(historical, "search", return_value=mock_rows):
        result = retrieve_historical(_make_event())

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].outcome == "approved"


def test_retrieve_historical_returns_historical_match_instances():
    """Each item in result should be a HistoricalMatch instance."""
    import src.system.context.historical as historical
    from src.system.context.historical import retrieve_historical, HistoricalMatch

    mock_rows = [
        _mock_row("EVT-001 aluminum to glass", similarity=0.85),
        _mock_row("EVT-002 steel to wood railing", similarity=0.72),
        _mock_row("EVT-003 concrete to timber beam", similarity=0.68),
    ]
    with patch.object(historical, "search", return_value=mock_rows):
        result = retrieve_historical(_make_event())

    assert all(isinstance(m, HistoricalMatch) for m in result)


def test_retrieve_historical_sorted_by_similarity():
    """Results should be sorted by similarity descending."""
    import src.system.context.historical as historical
    from src.system.context.historical import retrieve_historical

    mock_rows = [
        _mock_row("Low similarity hit", similarity=0.7),
        _mock_row("High similarity hit", similarity=0.95),
        _mock_row("Medium similarity hit", similarity=0.8),
    ]
    with patch.object(historical, "search", return_value=mock_rows):
        result = retrieve_historical(_make_event())

    assert result[0].similarity == 0.95


def test_retrieve_historical_outcome_from_metadata():
    """HistoricalMatch.outcome and success_rate should be populated from metadata."""
    import src.system.context.historical as historical
    from src.system.context.historical import retrieve_historical

    mock_rows = [
        _mock_row(
            "EVT-007 rejected change",
            metadata={"outcome": "rejected", "success_rate": 0.3},
        )
    ]
    with patch.object(historical, "search", return_value=mock_rows):
        result = retrieve_historical(_make_event())

    assert result[0].outcome == "rejected"
    assert result[0].success_rate == 0.3


def test_retrieve_historical_empty_db_returns_empty_list():
    """When search() returns [], retrieve_historical() should return []."""
    import src.system.context.historical as historical
    from src.system.context.historical import retrieve_historical

    with patch.object(historical, "search", return_value=[]):
        result = retrieve_historical(_make_event())

    assert result == []


# ---------------------------------------------------------------------------
# CTX-01: enrich_event tests
# ---------------------------------------------------------------------------


def test_enrich_event_returns_enriched_event(monkeypatch):
    """enrich_event() should return a valid EnrichedEvent with the original event."""
    import src.system.context.enrichment as enrichment
    from src.system.context.enrichment import enrich_event, EnrichedEvent

    monkeypatch.delenv("ACC_TOKEN", raising=False)

    with patch.object(enrichment, "search", return_value=[]), \
         patch.object(enrichment, "retrieve_historical", return_value=[]):
        result = enrich_event(_make_event())

    assert isinstance(result, EnrichedEvent)
    assert result.event.event_id == "e-demo"


def test_enrich_event_stub_returns_w_unit_ids(monkeypatch):
    """When ACC_TOKEN is not set, acc_floor_plan should contain W-301..W-312."""
    import src.system.context.enrichment as enrichment
    from src.system.context.enrichment import enrich_event

    monkeypatch.delenv("ACC_TOKEN", raising=False)

    with patch.object(enrichment, "search", return_value=[]), \
         patch.object(enrichment, "retrieve_historical", return_value=[]):
        result = enrich_event(_make_event())

    assert "W-301" in result.acc_floor_plan["units"]
    assert "W-312" in result.acc_floor_plan["units"]
    assert len(result.acc_floor_plan["units"]) == 12


def test_enrich_event_supplier_info_from_search(monkeypatch):
    """supplier_info should be populated from the first supplier search result."""
    import src.system.context.enrichment as enrichment
    from src.system.context.enrichment import enrich_event

    monkeypatch.delenv("ACC_TOKEN", raising=False)

    mock_supplier_row = _mock_row(
        "Premium Wood Co pricing $45/sqft",
        source="knowledge_folder/team_directory",
        similarity=0.88,
    )

    def _mock_search(query_text, top_k=5, source_filter=None):
        # Return supplier row only for supplier query (first call)
        if "supplier" in query_text:
            return [mock_supplier_row]
        return []

    with patch.object(enrichment, "search", side_effect=_mock_search), \
         patch.object(enrichment, "retrieve_historical", return_value=[]):
        result = enrich_event(_make_event())

    assert result.supplier_info is not None
    assert result.supplier_info["similarity"] == 0.88
