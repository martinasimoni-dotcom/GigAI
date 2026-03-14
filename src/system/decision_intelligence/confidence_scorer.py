"""
Confidence scorer — DI-03.
Weighted 4-factor formula. No LLM calls. No config.settings import.

Exports:
    score_proposal(processing_result, historical_matches) -> ConfidenceResult
    ConfidenceResult: Pydantic v2 model with score, breakdown, recommendation
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from src.system.context.historical import HistoricalMatch
    from src.system.domain_processing.processor import ProcessingResult


class ConfidenceResult(BaseModel):
    """
    Output of the confidence scorer.

    Attributes:
        score: 0.0 to 100.0 weighted composite score
        breakdown: per-factor weighted contributions (four keys)
        recommendation: "accept" (>80), "review" (50-80), "reject" (<50)
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    score: float  # 0.0 to 100.0
    breakdown: dict  # {"data_clarity": float, "historical_match": float, "cost_acceptable": float, "no_red_flags": float}
    recommendation: Literal["accept", "review", "reject"]


def score_proposal(
    processing_result: "ProcessingResult",
    historical_matches: list["HistoricalMatch"],
) -> ConfidenceResult:
    """
    Compute a 0-100 confidence score for a proposal using a 4-factor weighted formula.

    Formula (weights sum to 1.0):
        data_clarity    (0.30): NormalizedEvent.confidence / 100.0
        historical_match (0.25): mean similarity of historical matches, 0.0 if none
        cost_acceptable  (0.25): 1.0 if cost <= 50000 or unknown, 0.0 if cost > 50000
        no_red_flags     (0.20): 1.0 if not escalate_immediately, 0.5 if escalate_immediately

    Recommendation thresholds:
        score > 80  -> "accept"
        50 <= score <= 80 -> "review"
        score < 50  -> "reject"

    Args:
        processing_result: ProcessingResult from domain processor pipeline.
            Reads: .event.event.confidence (int 0-100)
                   .event.event.estimated_cost (Optional[float])
                   .policy_result.escalate_immediately (bool)
        historical_matches: List of HistoricalMatch objects from context retrieval.
            Reads: .similarity (float 0.0-1.0) from each match.

    Returns:
        ConfidenceResult with score, per-factor breakdown, and recommendation.
    """
    # Factor 1: data_clarity (weight 0.30)
    raw_confidence = processing_result.event.event.confidence  # int 0-100
    data_clarity_factor = raw_confidence / 100.0
    data_clarity_contribution = data_clarity_factor * 30.0

    # Factor 2: historical_match (weight 0.25)
    if historical_matches:
        avg_similarity = sum(m.similarity for m in historical_matches) / len(historical_matches)
    else:
        avg_similarity = 0.0
    historical_match_contribution = avg_similarity * 25.0

    # Factor 3: cost_acceptable (weight 0.25)
    estimated_cost = processing_result.event.event.estimated_cost
    if estimated_cost is not None and estimated_cost > 50_000:
        cost_acceptable_factor = 0.0
    else:
        cost_acceptable_factor = 1.0
    cost_acceptable_contribution = cost_acceptable_factor * 25.0

    # Factor 4: no_red_flags (weight 0.20)
    # PolicyResult uses .escalate (not .escalate_immediately); fall back to False if missing.
    escalate = getattr(processing_result.policy_result, "escalate_immediately",
                       getattr(processing_result.policy_result, "escalate", False))
    no_red_flags_factor = 0.5 if escalate else 1.0
    no_red_flags_contribution = no_red_flags_factor * 20.0

    # Composite score (0-100)
    score = (
        data_clarity_contribution
        + historical_match_contribution
        + cost_acceptable_contribution
        + no_red_flags_contribution
    )

    # Recommendation thresholds
    if score > 80.0:
        recommendation: Literal["accept", "review", "reject"] = "accept"
    elif score < 50.0:
        recommendation = "reject"
    else:
        recommendation = "review"

    breakdown = {
        "data_clarity": data_clarity_contribution,
        "historical_match": historical_match_contribution,
        "cost_acceptable": cost_acceptable_contribution,
        "no_red_flags": no_red_flags_contribution,
    }

    return ConfidenceResult(
        score=score,
        breakdown=breakdown,
        recommendation=recommendation,
    )
