"""
Unit tests for time_analysis.py — DOM-03.

Uses IMPL_AVAILABLE guard (Path.exists() + stat().st_size > 10) so the file
is always collectable by pytest even before the implementation exists.
Imports are lazy (inside each test function) to prevent settings singleton
from triggering at collection time.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

IMPL_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "src/system/domain_processing/time_analysis.py"
)
IMPL_AVAILABLE = IMPL_PATH.exists() and IMPL_PATH.stat().st_size > 10
pytestmark = pytest.mark.skipif(
    not IMPL_AVAILABLE, reason="time_analysis.py not yet implemented"
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def make_event(quantity: int | None):
    """Build a minimal EnrichedEvent with the given quantity."""
    from src.shared.models.events import NormalizedEvent
    from src.system.context.enrichment import EnrichedEvent

    norm = NormalizedEvent(
        event_id="test-evt-001",
        source="fireflies",
        event_type="material_change",
        quantity=quantity,
        summary="Window material change from aluminum to wood",
    )
    return EnrichedEvent(
        event=norm,
        knowledge_chunks=[],
        acc_floor_plan={},
        supplier_info=None,
        relevant_rules=[],
        historical_matches=[],
    )


def schedule_entry(days_from_now: int, activity: str = "test-activity") -> dict:
    """Return a schedule dict entry N days from today (UTC)."""
    date = (datetime.now(timezone.utc) + timedelta(days=days_from_now)).date()
    return {"date": str(date), "activity": activity, "location": "3rd Floor"}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLeadTimeDays:
    def test_qty_gt_10_returns_42_days(self):
        from src.system.domain_processing.time_analysis import (
            TimeAnalysisResult,
            analyze_time,
        )

        event = make_event(quantity=12)
        result = analyze_time(event, schedule=[])
        assert isinstance(result, TimeAnalysisResult)
        assert result.lead_time_days == 42

    def test_qty_lte_10_returns_21_days(self):
        from src.system.domain_processing.time_analysis import analyze_time

        event = make_event(quantity=8)
        result = analyze_time(event, schedule=[])
        assert result.lead_time_days == 21

    def test_qty_exactly_10_returns_21_days(self):
        from src.system.domain_processing.time_analysis import analyze_time

        event = make_event(quantity=10)
        result = analyze_time(event, schedule=[])
        assert result.lead_time_days == 21

    def test_qty_none_returns_21_days_default(self):
        from src.system.domain_processing.time_analysis import analyze_time

        event = make_event(quantity=None)
        result = analyze_time(event, schedule=[])
        assert result.lead_time_days == 21


class TestConflictDetection:
    def test_empty_schedule_no_conflict(self):
        from src.system.domain_processing.time_analysis import analyze_time

        event = make_event(quantity=12)
        result = analyze_time(event, schedule=[])
        assert result.has_conflict is False
        assert result.schedule_conflicts == []

    def test_entry_within_42day_window_triggers_conflict(self):
        from src.system.domain_processing.time_analysis import analyze_time

        event = make_event(quantity=12)
        result = analyze_time(event, schedule=[schedule_entry(days_from_now=20)])
        assert result.has_conflict is True
        assert len(result.schedule_conflicts) == 1

    def test_entry_beyond_42day_window_no_conflict(self):
        from src.system.domain_processing.time_analysis import analyze_time

        event = make_event(quantity=12)
        result = analyze_time(event, schedule=[schedule_entry(days_from_now=50)])
        assert result.has_conflict is False
        assert result.schedule_conflicts == []

    def test_entry_within_21day_window_triggers_conflict(self):
        from src.system.domain_processing.time_analysis import analyze_time

        event = make_event(quantity=8)
        result = analyze_time(event, schedule=[schedule_entry(days_from_now=15)])
        assert result.has_conflict is True

    def test_entry_beyond_21day_window_no_conflict(self):
        from src.system.domain_processing.time_analysis import analyze_time

        event = make_event(quantity=8)
        result = analyze_time(event, schedule=[schedule_entry(days_from_now=30)])
        assert result.has_conflict is False

    def test_conflict_details_populated_when_conflict(self):
        from src.system.domain_processing.time_analysis import analyze_time

        event = make_event(quantity=12)
        result = analyze_time(event, schedule=[schedule_entry(days_from_now=20)])
        assert result.conflict_details is not None
        assert "42" in result.conflict_details

    def test_conflict_details_none_when_no_conflict(self):
        from src.system.domain_processing.time_analysis import analyze_time

        event = make_event(quantity=12)
        result = analyze_time(event, schedule=[])
        assert result.conflict_details is None

    def test_none_schedule_defaults_to_empty(self):
        from src.system.domain_processing.time_analysis import analyze_time

        event = make_event(quantity=12)
        result = analyze_time(event, schedule=None)
        assert result.has_conflict is False
        assert result.schedule_conflicts == []


class TestGracefulHandling:
    def test_unparseable_date_skipped_no_exception(self):
        from src.system.domain_processing.time_analysis import analyze_time

        event = make_event(quantity=12)
        bad_entry = {"date": "not-a-date-at-all!!!", "activity": "bad-entry"}
        result = analyze_time(event, schedule=[bad_entry])
        # Should not raise; conflict count should be 0 or based only on parseable entries
        assert result.has_conflict is False

    def test_missing_date_key_skipped_no_exception(self):
        from src.system.domain_processing.time_analysis import analyze_time

        event = make_event(quantity=12)
        no_date_entry = {"activity": "no date key here"}
        result = analyze_time(event, schedule=[no_date_entry])
        assert result.has_conflict is False

    def test_mixed_valid_invalid_dates(self):
        from src.system.domain_processing.time_analysis import analyze_time

        event = make_event(quantity=12)
        entries = [
            {"date": "not-valid", "activity": "bad"},
            schedule_entry(days_from_now=10),
        ]
        result = analyze_time(event, schedule=entries)
        # Only the valid entry within the 42-day window counts
        assert result.has_conflict is True
        assert len(result.schedule_conflicts) == 1


class TestTimeAnalysisResultModel:
    def test_result_is_pydantic_model(self):
        from pydantic import BaseModel

        from src.system.domain_processing.time_analysis import TimeAnalysisResult

        assert issubclass(TimeAnalysisResult, BaseModel)

    def test_result_has_required_fields(self):
        from src.system.domain_processing.time_analysis import TimeAnalysisResult

        result = TimeAnalysisResult()
        # All fields must be present with defaults
        assert hasattr(result, "has_conflict")
        assert hasattr(result, "conflict_details")
        assert hasattr(result, "lead_time_days")
        assert hasattr(result, "critical_path_affected")
        assert hasattr(result, "schedule_conflicts")

    def test_result_default_values(self):
        from src.system.domain_processing.time_analysis import TimeAnalysisResult

        result = TimeAnalysisResult()
        assert result.has_conflict is False
        assert result.conflict_details is None
        assert result.lead_time_days == 21
        assert result.critical_path_affected is False
        assert result.schedule_conflicts == []

    def test_result_serializes_to_dict(self):
        from src.system.domain_processing.time_analysis import TimeAnalysisResult

        result = TimeAnalysisResult(has_conflict=True, lead_time_days=42)
        d = result.model_dump()
        assert d["has_conflict"] is True
        assert d["lead_time_days"] == 42
