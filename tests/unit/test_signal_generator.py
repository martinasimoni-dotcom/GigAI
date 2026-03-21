"""
Unit tests for signal_generator.py — DOM-05.

Uses IMPL_AVAILABLE guard (Path.exists() + stat().st_size > 10) so the file
is always collectable by pytest even before the implementation exists.
Imports are lazy (inside each test function) to prevent settings singleton
from triggering at collection time.

Autouse fixture sets required env vars and pops sys.modules to prevent
config.settings ValidationError — same pattern as test_time_analysis.py.
"""
import sys
from pathlib import Path

import pytest

IMPL_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "src/system/domain_processing/signal_generator.py"
)
IMPL_AVAILABLE = IMPL_PATH.exists() and IMPL_PATH.stat().st_size > 10
pytestmark = pytest.mark.skipif(
    not IMPL_AVAILABLE, reason="signal_generator.py not yet implemented"
)

_SETTINGS_MODULES = [
    "src.system.context.enrichment",
    "src.system.context.historical",
    "src.system.context",
    "src.shared.db.vector_store",
    "src.shared.db.postgres",
    "src.system.domain_processing.signal_generator",
    "src.system.domain_processing.time_analysis",
    "src.system.domain_processing.policy_engine",
    "src.system.domain_processing",
    "config.settings",
]


@pytest.fixture(autouse=True)
def _setup_env(monkeypatch):
    """Set required env vars and reset module cache for clean isolation."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    monkeypatch.setenv("VOYAGE_API_KEY", "test-voyage-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")

    for mod in _SETTINGS_MODULES:
        sys.modules.pop(mod, None)

    yield

    for mod in _SETTINGS_MODULES:
        sys.modules.pop(mod, None)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def make_enriched_event(quantity: int = 12, event_type: str = "material_change"):
    """Build a minimal EnrichedEvent for tests."""
    from src.shared.models.events import NormalizedEvent
    from src.system.context.enrichment import EnrichedEvent

    norm = NormalizedEvent(
        event_id="test-evt-001",
        source="fireflies",
        event_type=event_type,
        quantity=quantity,
        material_original="aluminum",
        material_new="wood",
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


def make_policy_result(triggered_rules=None, escalate=False, alert_pm=True):
    """Build a PolicyResult fixture."""
    from src.system.domain_processing.policy_engine import PolicyResult

    return PolicyResult(
        triggered_rules=triggered_rules or [],
        rule_details=[],
        escalate=escalate,
        alert_pm=alert_pm,
    )


def make_time_result(has_conflict=False, lead_time_days=21, conflict_details=None):
    """Build a TimeAnalysisResult fixture."""
    from src.system.domain_processing.time_analysis import TimeAnalysisResult

    return TimeAnalysisResult(
        has_conflict=has_conflict,
        conflict_details=conflict_details,
        lead_time_days=lead_time_days,
        schedule_conflicts=[],
    )


def make_config(allowed_signals=None, event_type="material_change"):
    """Build an EventTypeConfig fixture."""
    from src.shared.models.config import EventTypeConfig

    if allowed_signals is None:
        allowed_signals = [
            "material_order_required",
            "schedule_update_needed",
            "drawing_markup_required",
        ]
    return EventTypeConfig(
        event_type=event_type,
        rules_file="knowledge_folder/rules/demo_project.yaml",
        allowed_signals=allowed_signals,
        enrichment_queries=[],
        time_analysis_enabled=True,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDemoSignals:
    def test_demo_signals(self):
        """Demo scenario: RULE-005, RULE-008, RULE-011 + has_conflict → all 3 signals."""
        from src.system.domain_processing.signal_generator import generate_signals

        event = make_enriched_event(quantity=12)
        policy = make_policy_result(triggered_rules=["RULE-005", "RULE-008", "RULE-011"])
        time = make_time_result(has_conflict=True, lead_time_days=42, conflict_details="1 conflict")
        config = make_config()

        signals = generate_signals(event, policy, time, config)
        signal_types = {s.signal_type for s in signals}

        assert "material_order_required" in signal_types, f"Missing material_order_required: {signal_types}"
        assert "schedule_update_needed" in signal_types, f"Missing schedule_update_needed: {signal_types}"
        assert "drawing_markup_required" in signal_types, f"Missing drawing_markup_required: {signal_types}"
        assert len(signals) == 3, f"Expected 3 signals, got {len(signals)}: {signal_types}"


class TestAllowedSignalsFilter:
    def test_allowed_signals_filter(self):
        """Only signals in allowed_signals are returned — even if multiple would map."""
        from src.system.domain_processing.signal_generator import generate_signals

        event = make_enriched_event()
        # All three rules fire (RULE-005 → material, RULE-011 → drawing) + has_conflict → schedule
        policy = make_policy_result(triggered_rules=["RULE-005", "RULE-011"])
        time = make_time_result(has_conflict=True)
        # Only material_order_required in allowed list
        config = make_config(allowed_signals=["material_order_required"])

        signals = generate_signals(event, policy, time, config)
        assert len(signals) == 1
        assert signals[0].signal_type == "material_order_required"

    def test_empty_allowed_signals_returns_empty(self):
        """No signals emitted when allowed_signals is empty."""
        from src.system.domain_processing.signal_generator import generate_signals

        event = make_enriched_event()
        policy = make_policy_result(triggered_rules=["RULE-005", "RULE-011"])
        time = make_time_result(has_conflict=True)
        config = make_config(allowed_signals=[])

        signals = generate_signals(event, policy, time, config)
        assert signals == []


class TestNoTriggers:
    def test_no_triggers_no_conflict_returns_empty(self):
        """No triggered rules and no time conflict → empty list."""
        from src.system.domain_processing.signal_generator import generate_signals

        event = make_enriched_event()
        policy = make_policy_result(triggered_rules=[], alert_pm=False)
        time = make_time_result(has_conflict=False)
        config = make_config()

        signals = generate_signals(event, policy, time, config)
        assert signals == []

    def test_unknown_rules_return_empty(self):
        """Rules not in the mapping table produce no signals."""
        from src.system.domain_processing.signal_generator import generate_signals

        event = make_enriched_event()
        policy = make_policy_result(triggered_rules=["RULE-999", "RULE-888"])
        time = make_time_result(has_conflict=False)
        config = make_config()

        signals = generate_signals(event, policy, time, config)
        assert signals == []


class TestNoDuplicates:
    def test_no_duplicates_multiple_rules_same_signal(self):
        """RULE-005, RULE-007, RULE-015 all map to material_order_required → deduplicated to 1."""
        from src.system.domain_processing.signal_generator import generate_signals

        event = make_enriched_event()
        policy = make_policy_result(triggered_rules=["RULE-005", "RULE-007", "RULE-015"])
        time = make_time_result(has_conflict=False)
        config = make_config(allowed_signals=["material_order_required"])

        signals = generate_signals(event, policy, time, config)
        signal_types = [s.signal_type for s in signals]

        assert signal_types.count("material_order_required") == 1, (
            f"Expected 1 material_order_required, got {signal_types}"
        )


class TestSignalValidPydantic:
    def test_signal_is_valid_pydantic(self):
        """Returned Signal instances pass model_validate — valid Pydantic v2 model."""
        from pydantic import BaseModel

        from src.shared.models.proposals import Signal
        from src.system.domain_processing.signal_generator import generate_signals

        event = make_enriched_event()
        policy = make_policy_result(triggered_rules=["RULE-005"])
        time = make_time_result(has_conflict=False)
        config = make_config(allowed_signals=["material_order_required"])

        signals = generate_signals(event, policy, time, config)
        assert len(signals) == 1

        signal = signals[0]
        assert isinstance(signal, Signal)
        assert issubclass(Signal, BaseModel)

        # Validate fields
        assert isinstance(signal.signal_type, str)
        assert isinstance(signal.priority, int)
        assert signal.priority >= 1
        assert isinstance(signal.payload, dict)
        assert signal.timestamp is not None

        # Re-validate via model_validate
        validated = Signal.model_validate(signal.model_dump())
        assert validated.signal_type == signal.signal_type

    def test_signal_priority_escalate_true(self):
        """When escalate=True, signals get higher priority."""
        from src.system.domain_processing.signal_generator import generate_signals

        event = make_enriched_event()
        policy = make_policy_result(triggered_rules=["RULE-005"], escalate=True)
        time = make_time_result(has_conflict=False)
        config = make_config(allowed_signals=["material_order_required"])

        signals = generate_signals(event, policy, time, config)
        assert len(signals) == 1
        assert signals[0].priority == 2

    def test_signal_priority_not_escalated(self):
        """When escalate=False, signals have priority=1."""
        from src.system.domain_processing.signal_generator import generate_signals

        event = make_enriched_event()
        policy = make_policy_result(triggered_rules=["RULE-005"], escalate=False)
        time = make_time_result(has_conflict=False)
        config = make_config(allowed_signals=["material_order_required"])

        signals = generate_signals(event, policy, time, config)
        assert len(signals) == 1
        assert signals[0].priority == 1


class TestTimeConflictSignal:
    def test_has_conflict_true_adds_schedule_signal(self):
        """has_conflict=True adds schedule_update_needed when it's in allowed_signals."""
        from src.system.domain_processing.signal_generator import generate_signals

        event = make_enriched_event()
        policy = make_policy_result(triggered_rules=[])
        time = make_time_result(has_conflict=True, lead_time_days=42, conflict_details="2 conflicts")
        config = make_config(allowed_signals=["schedule_update_needed"])

        signals = generate_signals(event, policy, time, config)
        assert len(signals) == 1
        assert signals[0].signal_type == "schedule_update_needed"
        assert signals[0].payload["conflict_details"] == "2 conflicts"
        assert signals[0].payload["lead_time_days"] == 42

    def test_has_conflict_false_no_schedule_signal(self):
        """has_conflict=False does not generate schedule_update_needed."""
        from src.system.domain_processing.signal_generator import generate_signals

        event = make_enriched_event()
        policy = make_policy_result(triggered_rules=[])
        time = make_time_result(has_conflict=False)
        config = make_config(allowed_signals=["schedule_update_needed"])

        signals = generate_signals(event, policy, time, config)
        assert signals == []
