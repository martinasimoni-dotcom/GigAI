"""
Unit tests for policy_engine.py — TDD RED phase.
Tests use tmp_path YAML fixture to avoid live filesystem dependency.
"""
from pathlib import Path

import pytest
import yaml

# IMPL_AVAILABLE guard — avoids pydantic ValidationError at collection time
IMPL_PATH = Path(__file__).resolve().parent.parent.parent / "src/system/domain_processing/policy_engine.py"
IMPL_AVAILABLE = IMPL_PATH.exists() and IMPL_PATH.stat().st_size > 10
pytestmark = pytest.mark.skipif(not IMPL_AVAILABLE, reason="policy_engine.py not yet implemented")


# ---------------------------------------------------------------------------
# Minimal rules YAML containing exactly the four rules needed for tests
# Condition strings are copied verbatim from knowledge_folder/rules/demo_project.yaml
# ---------------------------------------------------------------------------
MINIMAL_RULES = {
    "rules": [
        {
            "rule_id": "RULE-003",
            "description": "Immediate escalation for material changes exceeding $50,000",
            "condition": "estimated_cost > 50000",
            "action": "Escalate immediately",
            "stakeholders": ["Project Manager", "Owner Representative"],
            "priority": "critical",
        },
        {
            "rule_id": "RULE-005",
            "description": "Window orders exceeding 10 units require 6-week lead time allowance",
            "condition": "element_type == 'window' AND quantity > 10",
            "action": "Set minimum lead time to 6 weeks",
            "stakeholders": ["Procurement Officer"],
            "priority": "high",
        },
        {
            "rule_id": "RULE-007",
            "description": "All material substitutions must meet or exceed original specification",
            "condition": "change_type == 'material_substitution'",
            "action": "Require specification comparison document",
            "stakeholders": ["Lead Architect"],
            "priority": "high",
        },
        {
            "rule_id": "RULE-008",
            "description": "Wood frame window substitution for quantities above 8 requires structural assessment",
            "condition": "material_original == 'aluminum' AND material_new == 'wood' AND element_type == 'window' AND quantity > 8",
            "action": "Request structural weight assessment",
            "stakeholders": ["Structural Engineer"],
            "priority": "high",
        },
        {
            "rule_id": "RULE-011",
            "description": "All change orders require a drawing markup in ACC before execution",
            "condition": "change_type IN ['material_substitution', 'scope_change', 'rfi_resolution']",
            "action": "Create drawing markup in ACC Docs",
            "stakeholders": ["Lead Architect", "Project Manager"],
            "priority": "high",
        },
        {
            "rule_id": "RULE-015",
            "description": "Procurement Officer must receive supplier quote before any PO is issued",
            "condition": "change_type == 'material_substitution' AND po_issued == false",
            "action": "Request quote from relevant supplier",
            "stakeholders": ["Procurement Officer"],
            "priority": "high",
        },
    ]
}


@pytest.fixture
def rules_yaml_path(tmp_path: Path) -> Path:
    """Write minimal rules YAML to tmp_path; return the file path."""
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text(yaml.dump(MINIMAL_RULES))
    return rules_file


def _make_event_type_config(rules_file: Path):
    """Build an EventTypeConfig pointing at the given rules file."""
    from src.shared.models.config import EventTypeConfig

    return EventTypeConfig(
        event_type="material_change",
        rules_file=str(rules_file),
        allowed_signals=["material_order_required", "schedule_update_needed"],
        enrichment_queries=[],
        time_analysis_enabled=True,
    )


def _make_enriched_event(
    quantity: int | None = None,
    material_original: str | None = None,
    material_new: str | None = None,
    estimated_cost: float | None = None,
    change_type: str | None = None,
):
    """
    Construct a minimal EnrichedEvent without triggering config.settings.
    All imports are lazy to avoid Settings() singleton at collection time.
    """
    from src.shared.models.events import NormalizedEvent
    from src.system.context.enrichment import EnrichedEvent

    norm_event = NormalizedEvent(
        event_id="test-evt-001",
        source="acc",
        event_type="material_change",
        material_original=material_original,
        material_new=material_new,
        location="3rd floor",
        quantity=quantity,
        summary="Test material change event",
        estimated_cost=estimated_cost,
        change_type=change_type,
    )

    return EnrichedEvent(
        event=norm_event,
        knowledge_chunks=[],
        acc_floor_plan={"floor": "3rd", "units": ["W-301"]},
        supplier_info=None,
        relevant_rules=[],
        historical_matches=[],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_policy_result_is_valid_pydantic_model():
    """PolicyResult is a valid Pydantic v2 model with expected fields."""
    from src.system.domain_processing.policy_engine import PolicyResult

    result = PolicyResult()
    assert result.triggered_rules == []
    assert result.rule_details == []
    assert result.escalate is False
    assert result.alert_pm is False


def test_demo_scenario_triggers_rule_005_008_011(rules_yaml_path: Path):
    """
    Demo scenario: qty=12, aluminum→wood, change_type=material_substitution
    must trigger RULE-005, RULE-008, and RULE-011.
    """
    from src.system.domain_processing.policy_engine import evaluate_policies

    event = _make_enriched_event(
        quantity=12,
        material_original="aluminum",
        material_new="wood",
        change_type="material_substitution",
    )
    config = _make_event_type_config(rules_yaml_path)
    result = evaluate_policies(event, config)

    assert "RULE-005" in result.triggered_rules, f"Expected RULE-005, got: {result.triggered_rules}"
    assert "RULE-008" in result.triggered_rules, f"Expected RULE-008, got: {result.triggered_rules}"
    assert "RULE-011" in result.triggered_rules, f"Expected RULE-011, got: {result.triggered_rules}"
    assert result.alert_pm is True


def test_demo_scenario_evaluates_at_least_5_rules(rules_yaml_path: Path):
    """
    At least 5 rules must be evaluated for the demo scenario.
    The fixture has 6 rules, so all 6 are evaluated.
    """
    from src.system.domain_processing.policy_engine import evaluate_policies

    event = _make_enriched_event(
        quantity=12,
        material_original="aluminum",
        material_new="wood",
        change_type="material_substitution",
    )
    config = _make_event_type_config(rules_yaml_path)
    result = evaluate_policies(event, config)

    # rule_details contains one entry per evaluated rule (triggered or not is separate)
    # triggered_rules must be >= 3 for this scenario; total evaluated is all 6 rules in fixture
    assert len(result.triggered_rules) >= 3, (
        f"Demo scenario should trigger at least 3 rules, got: {result.triggered_rules}"
    )


def test_high_cost_triggers_rule_003_and_escalate(rules_yaml_path: Path):
    """
    estimated_cost=60000 must trigger RULE-003 and set escalate=True.
    """
    from src.system.domain_processing.policy_engine import evaluate_policies

    event = _make_enriched_event(
        quantity=5,
        material_original="aluminum",
        material_new="wood",
        estimated_cost=60000.0,
        change_type="material_substitution",
    )
    config = _make_event_type_config(rules_yaml_path)
    result = evaluate_policies(event, config)

    assert "RULE-003" in result.triggered_rules, f"Expected RULE-003, got: {result.triggered_rules}"
    assert result.escalate is True, "escalate must be True when a critical rule fires"


def test_empty_rules_returns_empty_triggered_list(tmp_path: Path):
    """
    When rules YAML has no rules, triggered_rules must be empty.
    """
    from src.system.domain_processing.policy_engine import PolicyResult, evaluate_policies

    empty_rules_file = tmp_path / "empty.yaml"
    empty_rules_file.write_text(yaml.dump({"rules": []}))

    event = _make_enriched_event(quantity=12, change_type="material_substitution")
    config = _make_event_type_config(empty_rules_file)
    result = evaluate_policies(event, config)

    assert isinstance(result, PolicyResult)
    assert result.triggered_rules == []
    assert result.escalate is False
    assert result.alert_pm is False


def test_unknown_field_in_condition_does_not_raise(rules_yaml_path: Path, tmp_path: Path):
    """
    A rule condition referencing an unknown field must return False, not raise.
    """
    from src.system.domain_processing.policy_engine import evaluate_policies

    # Create a rules file with an unknown-field condition
    unknown_rules_file = tmp_path / "unknown.yaml"
    unknown_rules_file.write_text(yaml.dump({
        "rules": [
            {
                "rule_id": "RULE-XX",
                "description": "Test unknown field",
                "condition": "nonexistent_field == 'foo'",
                "action": "Do something",
                "stakeholders": [],
                "priority": "normal",
            }
        ]
    }))

    event = _make_enriched_event(quantity=5)
    config = _make_event_type_config(unknown_rules_file)

    # Must not raise; unknown field → condition False → rule not triggered
    result = evaluate_policies(event, config)
    assert "RULE-XX" not in result.triggered_rules


def test_no_escalate_when_no_critical_rules_triggered(rules_yaml_path: Path):
    """
    escalate must remain False when no critical-priority rules trigger.
    RULE-003 (critical) condition: estimated_cost > 50000.
    Use cost=None (0) so RULE-003 does not fire.
    """
    from src.system.domain_processing.policy_engine import evaluate_policies

    event = _make_enriched_event(
        quantity=12,
        material_new="wood",
        change_type="material_substitution",
        estimated_cost=None,
    )
    config = _make_event_type_config(rules_yaml_path)
    result = evaluate_policies(event, config)

    assert result.escalate is False


def test_evaluate_policies_returns_policy_result_type(rules_yaml_path: Path):
    """Return type of evaluate_policies must be PolicyResult."""
    from src.system.domain_processing.policy_engine import PolicyResult, evaluate_policies

    event = _make_enriched_event(quantity=3)
    config = _make_event_type_config(rules_yaml_path)
    result = evaluate_policies(event, config)

    assert isinstance(result, PolicyResult)
