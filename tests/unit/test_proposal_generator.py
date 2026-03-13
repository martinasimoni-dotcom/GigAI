"""
Unit tests for proposal_generator.py — DI-02.

Test isolation:
- IMPL_AVAILABLE guard uses Path.exists() + file size check (not try/except)
- call_sonnet is mocked — no live API calls
- autouse fixture pops the full import chain and sets env vars
- sys.modules.pop prevents cross-contamination from the module-level anthropic.Anthropic() call in claude.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# IMPL_AVAILABLE guard: check the implementation file exists and has content
_GENERATOR_PATH = Path(__file__).parent.parent.parent / "src/system/decision_intelligence/proposal_generator.py"
IMPL_AVAILABLE = _GENERATOR_PATH.exists() and _GENERATOR_PATH.stat().st_size > 10

# ---------------------------------------------------------------------------
# Valid LLM JSON response used by multiple tests
# ---------------------------------------------------------------------------
_VALID_LLM_JSON = json.dumps({
    "event_summary": "Window material change from aluminum to wood on 3rd floor, 12 units.",
    "affected_stakeholders": ["Jane Miller", "Mike Torres"],
    "recommended_actions": [
        {
            "action_type": "email",
            "recipient": "jane@premiumwood.com",
            "description": "Request lead time quote",
            "priority": "high",
        },
        {
            "action_type": "task",
            "assignee": "Mike Torres",
            "description": "Create procurement order",
            "priority": "high",
        },
        {
            "action_type": "calendar",
            "recipient": "team",
            "description": "Schedule follow-up in 3 days",
            "priority": "medium",
        },
        {
            "action_type": "drawing",
            "recipient": "drawing A-301",
            "description": "Mark affected units",
            "priority": "medium",
        },
    ],
    "confidence_rationale": "Strong historical precedent. Cost within budget.",
})


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    """
    Set required env vars and pop any cached modules that would re-use a
    module-level anthropic.Anthropic() client initialised with no key.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/test")
    monkeypatch.setenv("VOYAGE_API_KEY", "test-key")
    # Pop the full import chain so each test gets a clean module state
    for mod in list(sys.modules.keys()):
        if any(x in mod for x in [
            "src.system.decision_intelligence",
            "src.shared.llm.claude",
            "src.shared.llm",
        ]):
            sys.modules.pop(mod, None)


# ---------------------------------------------------------------------------
# Helper: minimal ProcessingResult mock
# ---------------------------------------------------------------------------

def _make_processing_result(
    event_id: str = "evt-001",
    confidence: int = 72,
    estimated_cost: float = 30_000.0,
    escalate_immediately: bool = False,
    has_conflict: bool = False,
    triggered_rules: list | None = None,
    signals: list | None = None,
    historical_matches: list | None = None,
) -> MagicMock:
    """Build a minimal ProcessingResult-like mock that proposal_generator reads."""
    pr = MagicMock()
    pr.event.event.event_id = event_id
    pr.event.event.confidence = confidence
    pr.event.event.estimated_cost = estimated_cost
    pr.event.knowledge_chunks = []
    pr.event.historical_matches = historical_matches if historical_matches is not None else []
    pr.event.floor_plan_data = {}
    pr.signals = signals if signals is not None else []
    pr.policy_result.triggered_rules = triggered_rules if triggered_rules is not None else []
    pr.policy_result.escalate_immediately = escalate_immediately
    pr.time_result.has_conflict = has_conflict
    return pr


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_generate_proposal_success():
    """
    Happy path: call_sonnet returns valid JSON with all 4 action types.
    generate_proposal() returns a Proposal with:
    - 4 Action objects
    - correct event_id ("evt-001")
    - confidence_score in [0.0, 1.0]
    - valid recommendation
    """
    if not IMPL_AVAILABLE:
        pytest.skip("Implementation not yet available")

    with patch("src.shared.llm.claude.anthropic") as mock_anthropic:
        mock_anthropic.Anthropic.return_value = MagicMock()

        from src.system.decision_intelligence.proposal_generator import generate_proposal

        pr = _make_processing_result()

        with patch("src.shared.llm.claude.call_sonnet", return_value=_VALID_LLM_JSON):
            proposal = generate_proposal(pr)

    assert proposal.event_id == "evt-001"
    assert len(proposal.actions) == 4
    assert 0.0 <= proposal.confidence_score <= 1.0
    assert proposal.recommendation in ("accept", "review", "reject")
    assert proposal.status == "pending"


def test_generate_proposal_retries_on_json_error():
    """
    call_sonnet returns invalid JSON twice, then valid JSON on the third call.
    generate_proposal() should retry and ultimately return a valid Proposal.
    """
    if not IMPL_AVAILABLE:
        pytest.skip("Implementation not yet available")

    call_count = {"n": 0}

    def side_effect(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] < 3:
            return "this is not json {{{"
        return _VALID_LLM_JSON

    with patch("src.shared.llm.claude.anthropic") as mock_anthropic:
        mock_anthropic.Anthropic.return_value = MagicMock()

        from src.system.decision_intelligence.proposal_generator import generate_proposal

        # Patch with a zero-wait retry to keep the test fast
        from tenacity import retry, stop_after_attempt, wait_none
        import src.system.decision_intelligence.proposal_generator as gen_mod

        original_fn = gen_mod.generate_proposal.__wrapped__

        fast_generate = retry(
            stop=stop_after_attempt(3),
            wait=wait_none(),
            reraise=True,
        )(original_fn)

        pr = _make_processing_result()

        with patch("src.shared.llm.claude.call_sonnet", side_effect=side_effect):
            proposal = fast_generate(pr)

    assert proposal is not None
    assert call_count["n"] == 3
    assert len(proposal.actions) == 4


def test_generate_proposal_raises_after_max_retries():
    """
    call_sonnet always returns invalid JSON.
    generate_proposal() must raise after 3 attempts (tenacity reraises).
    """
    if not IMPL_AVAILABLE:
        pytest.skip("Implementation not yet available")

    with patch("src.shared.llm.claude.anthropic") as mock_anthropic:
        mock_anthropic.Anthropic.return_value = MagicMock()

        from tenacity import retry, stop_after_attempt, wait_none
        import src.system.decision_intelligence.proposal_generator as gen_mod

        original_fn = gen_mod.generate_proposal.__wrapped__

        fast_generate = retry(
            stop=stop_after_attempt(3),
            wait=wait_none(),
            reraise=True,
        )(original_fn)

        pr = _make_processing_result()

        with patch("src.shared.llm.claude.call_sonnet", return_value="NOT VALID JSON !!!"):
            with pytest.raises((json.JSONDecodeError, Exception)):
                fast_generate(pr)


def test_confidence_score_stored_as_fraction():
    """
    ConfidenceResult.score is 0-100; Proposal.confidence_score must be score/100.
    With confidence=95, no escalation, cost=30000, no historical matches:
      score = 0.95*30 + 0.0*25 + 1.0*25 + 1.0*20 = 28.5 + 0 + 25 + 20 = 73.5 → 0.735
    Proposal.confidence_score must be in [0.0, 1.0].
    """
    if not IMPL_AVAILABLE:
        pytest.skip("Implementation not yet available")

    with patch("src.shared.llm.claude.anthropic") as mock_anthropic:
        mock_anthropic.Anthropic.return_value = MagicMock()

        from src.system.decision_intelligence.proposal_generator import generate_proposal

        pr = _make_processing_result(confidence=95, estimated_cost=30_000.0)

        with patch("src.shared.llm.claude.call_sonnet", return_value=_VALID_LLM_JSON):
            proposal = generate_proposal(pr)

    # Must be stored as a fraction, not 0-100
    assert 0.0 <= proposal.confidence_score <= 1.0, (
        f"confidence_score must be in [0.0, 1.0], got {proposal.confidence_score}"
    )
    # With no historical matches, confidence=95, cost=30000, escalate=False:
    # score = 0.95*30 + 0*25 + 25 + 20 = 73.5 → 0.735
    expected_score = (0.95 * 30 + 0.0 * 25 + 1.0 * 25 + 1.0 * 20) / 100.0
    assert abs(proposal.confidence_score - expected_score) < 0.02, (
        f"Expected ~{expected_score:.3f}, got {proposal.confidence_score:.3f}"
    )


def test_actions_mapped_from_llm():
    """
    recommended_actions from LLM map to Action objects with:
    - correct action_type for each action
    - action_data dict containing the original LLM action fields
    """
    if not IMPL_AVAILABLE:
        pytest.skip("Implementation not yet available")

    with patch("src.shared.llm.claude.anthropic") as mock_anthropic:
        mock_anthropic.Anthropic.return_value = MagicMock()

        from src.system.decision_intelligence.proposal_generator import generate_proposal

        pr = _make_processing_result()

        with patch("src.shared.llm.claude.call_sonnet", return_value=_VALID_LLM_JSON):
            proposal = generate_proposal(pr)

    action_types = [a.action_type for a in proposal.actions]
    assert "email" in action_types, f"Missing 'email' action, got: {action_types}"
    assert "task" in action_types, f"Missing 'task' action, got: {action_types}"
    assert "calendar" in action_types, f"Missing 'calendar' action, got: {action_types}"
    assert "drawing" in action_types, f"Missing 'drawing' action, got: {action_types}"

    # Each action_data must be a dict containing at least 'action_type' and 'description'
    for action in proposal.actions:
        assert isinstance(action.action_data, dict), f"action_data must be dict, got {type(action.action_data)}"
        assert "action_type" in action.action_data, f"action_data missing 'action_type' key"
        assert "description" in action.action_data, f"action_data missing 'description' key"
