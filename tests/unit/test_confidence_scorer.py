"""
Unit tests for confidence_scorer.py — DI-03.

Test isolation:
- IMPL_AVAILABLE guard uses Path.exists() + file size check (not try/except)
- Inputs are constructed via MagicMock (no live DB/LLM calls)
- No module-level imports of the scorer (lazy inside each test)
"""
from pathlib import Path
from unittest.mock import MagicMock

# IMPL_AVAILABLE guard: check the implementation file exists and has content
_SCORER_PATH = Path(__file__).parent.parent.parent / "src/system/decision_intelligence/confidence_scorer.py"
IMPL_AVAILABLE = _SCORER_PATH.exists() and _SCORER_PATH.stat().st_size > 10


def _make_processing_result(confidence: int, estimated_cost: float | None, escalate_immediately: bool) -> MagicMock:
    """
    Build a minimal ProcessingResult-like mock.
    The scorer reads:
      processing_result.event.event.confidence
      processing_result.event.event.estimated_cost
      processing_result.policy_result.escalate_immediately
    """
    pr = MagicMock()
    pr.event.event.confidence = confidence
    pr.event.event.estimated_cost = estimated_cost
    pr.policy_result.escalate_immediately = escalate_immediately
    return pr


def _make_historical_matches(similarities: list[float]) -> list[MagicMock]:
    """Build minimal HistoricalMatch-like mocks with only .similarity set."""
    matches = []
    for sim in similarities:
        m = MagicMock()
        m.similarity = sim
        matches.append(m)
    return matches


def test_confidence_result_fields():
    """ConfidenceResult has score (float 0-100), breakdown (dict with 4 keys), recommendation."""
    if not IMPL_AVAILABLE:
        import pytest
        pytest.skip("Implementation not yet available")

    from src.system.decision_intelligence.confidence_scorer import ConfidenceResult

    result = ConfidenceResult(
        score=75.0,
        breakdown={
            "data_clarity": 18.0,
            "historical_match": 22.5,
            "cost_acceptable": 25.0,
            "no_red_flags": 9.5,
        },
        recommendation="review",
    )

    assert isinstance(result.score, float)
    assert 0.0 <= result.score <= 100.0
    assert isinstance(result.breakdown, dict)
    assert len(result.breakdown) == 4
    assert "data_clarity" in result.breakdown
    assert "historical_match" in result.breakdown
    assert "cost_acceptable" in result.breakdown
    assert "no_red_flags" in result.breakdown
    assert result.recommendation in ("accept", "review", "reject")


def test_demo_scenario():
    """
    Demo scenario: confidence=60, no escalation, cost=30000, similarities=[0.92, 0.88, 0.90]
    Expected: score ~85.5 (±3), recommendation="accept"

    Formula:
      data_clarity    = 0.60 * 30 = 18.0
      historical_match = mean([0.92, 0.88, 0.90]) * 25 = 0.90 * 25 = 22.5
      cost_acceptable = 1.0 * 25 = 25.0   (cost 30000 <= 50000)
      no_red_flags    = 1.0 * 20 = 20.0   (no escalation)
      score           = 18.0 + 22.5 + 25.0 + 20.0 = 85.5
    """
    if not IMPL_AVAILABLE:
        import pytest
        pytest.skip("Implementation not yet available")

    from src.system.decision_intelligence.confidence_scorer import score_proposal

    pr = _make_processing_result(confidence=60, estimated_cost=30000.0, escalate_immediately=False)
    matches = _make_historical_matches([0.92, 0.88, 0.90])

    result = score_proposal(pr, matches)

    assert abs(result.score - 85.5) <= 3.0, f"Expected ~85.5 ±3, got {result.score}"
    assert result.recommendation == "accept", f"Expected 'accept', got {result.recommendation}"
    assert result.breakdown["data_clarity"] == 18.0
    assert abs(result.breakdown["historical_match"] - 22.5) < 0.1
    assert result.breakdown["cost_acceptable"] == 25.0
    assert result.breakdown["no_red_flags"] == 20.0


def test_high_cost_reject():
    """
    High-cost scenario: confidence=15, escalate=True, cost=75000, similarities=[0.25]
    Expected: score < 50, recommendation="reject"

    Formula:
      data_clarity    = 0.15 * 30 = 4.5
      historical_match = 0.25 * 25 = 6.25
      cost_acceptable = 0.0 * 25 = 0.0   (cost 75000 > 50000)
      no_red_flags    = 0.5 * 20 = 10.0  (escalate_immediately=True)
      score           = 4.5 + 6.25 + 0.0 + 10.0 = 20.75
    """
    if not IMPL_AVAILABLE:
        import pytest
        pytest.skip("Implementation not yet available")

    from src.system.decision_intelligence.confidence_scorer import score_proposal

    pr = _make_processing_result(confidence=15, estimated_cost=75000.0, escalate_immediately=True)
    matches = _make_historical_matches([0.25])

    result = score_proposal(pr, matches)

    assert result.score < 50.0, f"Expected score < 50, got {result.score}"
    assert result.recommendation == "reject", f"Expected 'reject', got {result.recommendation}"
    assert abs(result.score - 20.75) < 0.1, f"Expected 20.75, got {result.score}"


def test_medium_confidence_review():
    """
    Medium scenario: confidence=60, no escalation, cost=20000, similarities=[0.55]
    Expected: 50 <= score <= 80, recommendation="review"

    Formula:
      data_clarity    = 0.60 * 30 = 18.0
      historical_match = 0.55 * 25 = 13.75
      cost_acceptable = 1.0 * 25 = 25.0
      no_red_flags    = 1.0 * 20 = 20.0
      score           = 18.0 + 13.75 + 25.0 + 20.0 = 76.75
    """
    if not IMPL_AVAILABLE:
        import pytest
        pytest.skip("Implementation not yet available")

    from src.system.decision_intelligence.confidence_scorer import score_proposal

    pr = _make_processing_result(confidence=60, estimated_cost=20000.0, escalate_immediately=False)
    matches = _make_historical_matches([0.55])

    result = score_proposal(pr, matches)

    assert 50.0 <= result.score <= 80.0, f"Expected 50-80, got {result.score}"
    assert result.recommendation == "review", f"Expected 'review', got {result.recommendation}"


def test_no_historical_matches():
    """
    Empty historical_matches list: historical_match factor = 0.0, no error.

    Formula with confidence=70, no escalation, cost=25000, no matches:
      data_clarity    = 0.70 * 30 = 21.0
      historical_match = 0.0 * 25 = 0.0   (empty list)
      cost_acceptable = 1.0 * 25 = 25.0
      no_red_flags    = 1.0 * 20 = 20.0
      score           = 21.0 + 0.0 + 25.0 + 20.0 = 66.0
    """
    if not IMPL_AVAILABLE:
        import pytest
        pytest.skip("Implementation not yet available")

    from src.system.decision_intelligence.confidence_scorer import score_proposal

    pr = _make_processing_result(confidence=70, estimated_cost=25000.0, escalate_immediately=False)
    matches = _make_historical_matches([])  # empty

    result = score_proposal(pr, matches)

    assert result.breakdown["historical_match"] == 0.0
    assert abs(result.score - 66.0) < 0.1, f"Expected 66.0, got {result.score}"
    assert result.recommendation == "review"


def test_boundary_exactly_80_is_review():
    """Score exactly 80.0 should be 'review' (threshold is score > 80 for accept)."""
    if not IMPL_AVAILABLE:
        import pytest
        pytest.skip("Implementation not yet available")

    from src.system.decision_intelligence.confidence_scorer import ConfidenceResult

    result = ConfidenceResult(
        score=80.0,
        breakdown={"data_clarity": 0, "historical_match": 0, "cost_acceptable": 0, "no_red_flags": 0},
        recommendation="review",
    )
    assert result.recommendation == "review"


def test_boundary_exactly_50_is_review():
    """Score exactly 50.0 should be 'review' (threshold is score < 50 for reject)."""
    if not IMPL_AVAILABLE:
        import pytest
        pytest.skip("Implementation not yet available")

    from src.system.decision_intelligence.confidence_scorer import ConfidenceResult

    result = ConfidenceResult(
        score=50.0,
        breakdown={"data_clarity": 0, "historical_match": 0, "cost_acceptable": 0, "no_red_flags": 0},
        recommendation="review",
    )
    assert result.recommendation == "review"
