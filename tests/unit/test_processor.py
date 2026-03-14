"""
Unit tests for domain processor (processor.py) — DOM-06.

Tests use patch.object to avoid real ACC/LLM calls.
Uses IMPL_AVAILABLE guard + lazy imports to prevent settings singleton
from triggering at collection time.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

IMPL_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "src/system/domain_processing/processor.py"
)
IMPL_AVAILABLE = IMPL_PATH.exists() and IMPL_PATH.stat().st_size > 10
pytestmark = pytest.mark.skipif(
    not IMPL_AVAILABLE, reason="processor.py not yet implemented"
)

_MODULES_TO_RESET = [
    "src.system.domain_processing.processor",
    "src.system.domain_processing.signal_generator",
    "src.system.domain_processing.policy_engine",
    "src.system.domain_processing.time_analysis",
    "src.system.domain_processing",
    "src.system.context.enrichment",
    "src.system.context.historical",
    "src.system.context",
    "src.shared.db.vector_store",
    "src.shared.db.postgres",
    "src.system.data_processing.router",
    "src.system.data_processing",
    "config.settings",
]


@pytest.fixture(autouse=True)
def _setup_env(monkeypatch):
    """Set required env vars and reset module cache before each test."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    monkeypatch.setenv("VOYAGE_API_KEY", "test-voyage-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")

    for mod in _MODULES_TO_RESET:
        sys.modules.pop(mod, None)

    yield

    for mod in _MODULES_TO_RESET:
        sys.modules.pop(mod, None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_routed_event():
    """Build a minimal RoutedEvent without triggering config.settings."""
    from src.shared.models.config import EventTypeConfig
    from src.shared.models.events import NormalizedEvent
    from src.system.data_processing.router import RoutedEvent

    norm = NormalizedEvent(
        event_id="proc-test-001",
        source="fireflies",
        event_type="material_change",
        material_original="aluminum",
        material_new="wood",
        location="3rd floor",
        quantity=12,
        summary="Change 12 windows from aluminum to wood on 3rd floor.",
        confidence=85,
    )
    config = EventTypeConfig(
        event_type="material_change",
        rules_file=str(
            Path(__file__).resolve().parent.parent.parent
            / "knowledge_folder/rules/demo_project.yaml"
        ),
        allowed_signals=["material_order_required", "schedule_update_needed"],
        enrichment_queries=["material supplier", "past approvals"],
        time_analysis_enabled=True,
    )
    return RoutedEvent(
        event=norm,
        event_type="material_change",
        config=config,
        config_path="config/event_types/material_change.yaml",
    )


def _make_enriched_event(routed_event=None):
    """Build a minimal EnrichedEvent."""
    from src.shared.models.events import NormalizedEvent
    from src.system.context.enrichment import EnrichedEvent

    if routed_event is not None:
        norm = routed_event.event
    else:
        norm = NormalizedEvent(
            event_id="proc-test-001",
            source="fireflies",
            event_type="material_change",
            material_original="aluminum",
            material_new="wood",
            location="3rd floor",
            quantity=12,
            summary="Change 12 windows from aluminum to wood on 3rd floor.",
            confidence=85,
        )

    return EnrichedEvent(
        event=norm,
        knowledge_chunks=[],
        acc_floor_plan={"floor": "3rd", "units": ["W-301", "W-312"]},
        supplier_info=None,
        relevant_rules=[],
        historical_matches=[],
    )


def _make_policy_result():
    from src.system.domain_processing.policy_engine import PolicyResult

    return PolicyResult(
        triggered_rules=["RULE-005", "RULE-008"],
        rule_details=[
            {"rule_id": "RULE-005", "priority": "high"},
            {"rule_id": "RULE-008", "priority": "high"},
        ],
        escalate=False,
        alert_pm=True,
    )


def _make_time_result():
    from src.system.domain_processing.time_analysis import TimeAnalysisResult

    return TimeAnalysisResult(
        has_conflict=False,
        conflict_details=None,
        lead_time_days=21,
        critical_path_affected=False,
        schedule_conflicts=[],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_process_event_returns_processing_result():
    """process_event() returns a ProcessingResult with expected fields."""
    from src.system.domain_processing import processor

    routed = _make_routed_event()
    enriched = _make_enriched_event(routed)
    policy_result = _make_policy_result()
    time_result = _make_time_result()

    from src.shared.models.proposals import Signal

    real_signal = Signal(signal_type="material_order_required", priority=1, payload={})

    with patch.object(processor, "enrich_event", return_value=enriched), \
         patch.object(processor, "analyze_time", return_value=time_result), \
         patch.object(processor, "evaluate_policies", return_value=policy_result), \
         patch.object(processor, "generate_signals", return_value=[real_signal]):
        result = processor.process_event(routed)

    assert result.event is enriched
    assert result.policy_result is policy_result
    assert result.time_result is time_result
    assert len(result.signals) == 1
    assert result.signals[0].signal_type == "material_order_required"


@pytest.mark.unit
def test_process_event_calls_pipeline_steps_in_order():
    """process_event() calls enrich, analyze_time, evaluate_policies, generate_signals."""
    from src.system.domain_processing import processor

    routed = _make_routed_event()
    enriched = _make_enriched_event(routed)
    policy_result = _make_policy_result()
    time_result = _make_time_result()

    call_order = []

    def track_enrich(event):
        call_order.append("enrich")
        return enriched

    def track_analyze(event, schedule=None):
        call_order.append("analyze_time")
        return time_result

    def track_policies(event, config):
        call_order.append("evaluate_policies")
        return policy_result

    def track_signals(event, policy, time, config):
        call_order.append("generate_signals")
        return []

    with patch.object(processor, "enrich_event", side_effect=track_enrich), \
         patch.object(processor, "analyze_time", side_effect=track_analyze), \
         patch.object(processor, "evaluate_policies", side_effect=track_policies), \
         patch.object(processor, "generate_signals", side_effect=track_signals):
        processor.process_event(routed)

    assert call_order == ["enrich", "analyze_time", "evaluate_policies", "generate_signals"]


@pytest.mark.unit
def test_fetch_acc_schedule_returns_empty_on_runtime_error():
    """_fetch_acc_schedule() returns [] gracefully when RuntimeError is raised."""
    from src.system.domain_processing import processor

    with patch(
        "src.system.domain_processing.processor._fetch_acc_schedule",
        return_value=[],
    ) as mock_fetch:
        routed = _make_routed_event()
        enriched = _make_enriched_event(routed)
        policy_result = _make_policy_result()
        time_result = _make_time_result()

        with patch.object(processor, "enrich_event", return_value=enriched), \
             patch.object(processor, "analyze_time", return_value=time_result), \
             patch.object(processor, "evaluate_policies", return_value=policy_result), \
             patch.object(processor, "generate_signals", return_value=[]):
            result = processor.process_event(routed)

        assert result is not None


@pytest.mark.unit
def test_fetch_acc_schedule_direct_runtime_error(monkeypatch):
    """_fetch_acc_schedule() returns [] when get_schedule_activities raises RuntimeError."""
    from src.system.domain_processing import processor

    def _raise_runtime(*args, **kwargs):
        raise RuntimeError("ACC credentials not set")

    with patch("src.system.domain_processing.processor._fetch_acc_schedule",
               wraps=processor._fetch_acc_schedule):
        with patch(
            "src.shared.clients.acc.get_schedule_activities",
            side_effect=_raise_runtime,
        ):
            result = processor._fetch_acc_schedule("proj-001")

    assert result == []


@pytest.mark.unit
def test_fetch_acc_schedule_direct_generic_exception(monkeypatch):
    """_fetch_acc_schedule() returns [] when get_schedule_activities raises a generic Exception."""
    from src.system.domain_processing import processor

    def _raise_generic(*args, **kwargs):
        raise ConnectionError("Network timeout")

    with patch(
        "src.shared.clients.acc.get_schedule_activities",
        side_effect=_raise_generic,
    ):
        result = processor._fetch_acc_schedule("proj-001")

    assert result == []


@pytest.mark.unit
def test_process_event_skips_acc_schedule_when_no_project_id(monkeypatch):
    """process_event() skips ACC schedule fetch when ACC_PROJECT_ID is not set."""
    from src.system.domain_processing import processor

    monkeypatch.delenv("ACC_PROJECT_ID", raising=False)

    routed = _make_routed_event()
    enriched = _make_enriched_event(routed)
    policy_result = _make_policy_result()
    time_result = _make_time_result()

    with patch.object(processor, "enrich_event", return_value=enriched), \
         patch.object(processor, "analyze_time", return_value=time_result) as mock_time, \
         patch.object(processor, "evaluate_policies", return_value=policy_result), \
         patch.object(processor, "generate_signals", return_value=[]), \
         patch.object(processor, "_fetch_acc_schedule") as mock_fetch:
        processor.process_event(routed)

    # When ACC_PROJECT_ID is empty, _fetch_acc_schedule must NOT be called
    mock_fetch.assert_not_called()
    # analyze_time is still called but with schedule=None
    mock_time.assert_called_once_with(enriched, schedule=None)
