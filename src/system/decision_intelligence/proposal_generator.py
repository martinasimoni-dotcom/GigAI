"""
Proposal generator — DI-02.

Calls Sonnet 4 with enriched context and signals, validates with Pydantic,
retries on ValidationError or JSONDecodeError.

No module-level config.settings import.
call_sonnet is imported lazily inside generate_proposal() to avoid triggering
the module-level anthropic.Anthropic() client at import time (which reads
ANTHROPIC_API_KEY before env vars are injected in tests).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential

from src.shared.models.proposals import Action, Proposal

if TYPE_CHECKING:
    from src.system.domain_processing.processor import ProcessingResult

logger = logging.getLogger(__name__)

# Load prompt file relative to this module — avoids config.settings dependency.
# Layout: src/system/decision_intelligence/proposal_generator.py
#         -> ../../../../config/prompts/proposal.txt
_PROMPT_PATH = (
    Path(__file__).parent.parent.parent.parent / "config" / "prompts" / "proposal.txt"
)


def _build_user_prompt(processing_result: "ProcessingResult") -> str:
    """Serialize ProcessingResult into the user message for Sonnet."""
    event = processing_result.event.event
    context = {
        "event_type": getattr(event, "event_type", None),
        "summary": getattr(event, "summary", None),
        "material_original": getattr(event, "material_original", None),
        "material_new": getattr(event, "material_new", None),
        "location": getattr(event, "location", None),
        "quantity": getattr(event, "quantity", None),
        "estimated_cost": getattr(event, "estimated_cost", None),
        "signals": [
            s.signal_type if hasattr(s, "signal_type") else str(s)
            for s in (processing_result.signals or [])
        ],
        "triggered_rules": processing_result.policy_result.triggered_rules,
        "time_conflict": processing_result.time_result.has_conflict,
        "knowledge_chunks": [
            c.get("content", "") if isinstance(c, dict) else str(c)
            for c in (processing_result.event.knowledge_chunks or [])
        ],
        "historical_matches": [
            {
                "content": getattr(m, "content", ""),
                "outcome": getattr(m, "outcome", None),
                "similarity": getattr(m, "similarity", 0.0),
            }
            for m in (processing_result.event.historical_matches or [])
        ],
        "floor_plan_data": processing_result.event.floor_plan_data,
    }
    return json.dumps(context, indent=2, default=str)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def generate_proposal(processing_result: "ProcessingResult") -> Proposal:
    """
    Generate a coordination proposal using Sonnet 4.

    Calls call_sonnet with the proposal.txt system prompt and a serialized
    ProcessingResult context. Parses and validates the JSON response, mapping
    recommended_actions to Action objects and scoring confidence.

    Retries up to 3 times (with exponential backoff) on json.JSONDecodeError
    or pydantic.ValidationError — errors that occur after the API call succeeds
    but during parsing/validation of the response.

    Note: call_sonnet already has its own tenacity @retry(stop_after_attempt(3))
    for transient API errors. This outer retry targets parse/validation failures
    that call_sonnet's internal retry does not cover.

    Args:
        processing_result: Full ProcessingResult from domain processing pipeline.

    Returns:
        Validated Proposal object with Actions, confidence_score (0.0-1.0),
        and recommendation.

    Raises:
        tenacity.RetryError (wrapping json.JSONDecodeError or ValidationError):
            After 3 failed parse/validation attempts.
    """
    # Lazy imports — keep module-level import chain from triggering
    # anthropic.Anthropic() before ANTHROPIC_API_KEY is available.
    from src.shared.llm.claude import call_sonnet  # noqa: PLC0415
    from src.system.decision_intelligence.confidence_scorer import score_proposal  # noqa: PLC0415

    system_prompt = _PROMPT_PATH.read_text(encoding="utf-8")
    user_prompt = _build_user_prompt(processing_result)

    raw = call_sonnet(prompt=user_prompt, system=system_prompt)

    # json.loads raises JSONDecodeError on bad input — tenacity will retry
    data = json.loads(raw)

    # Map recommended_actions -> Action objects; unknown types fall back to "task"
    _VALID_TYPES = {"email", "task", "calendar", "drawing"}
    actions: list[Action] = []
    for raw_action in data.get("recommended_actions", []):
        action_type = raw_action.get("action_type", "task")
        if action_type not in _VALID_TYPES:
            action_type = "task"
        actions.append(
            Action(
                action_type=action_type,
                action_data=raw_action,
            )
        )

    # Retrieve historical matches already attached to the enriched event
    historical = processing_result.event.historical_matches or []

    # Score confidence — may raise ValidationError, which tenacity will retry
    confidence_result = score_proposal(processing_result, historical)

    # Build the Proposal — ValidationError triggers tenacity retry
    proposal = Proposal(
        event_id=processing_result.event.event.event_id,
        alert={
            "summary": data.get("event_summary", ""),
            "stakeholders": data.get("affected_stakeholders", []),
            "confidence_rationale": data.get("confidence_rationale", ""),
        },
        actions=actions,
        confidence_score=confidence_result.score / 100.0,  # stored as 0.0-1.0
        recommendation=confidence_result.recommendation,
    )

    logger.info(
        {
            "event": "proposal_generated",
            "event_id": proposal.event_id,
            "actions": len(proposal.actions),
            "confidence_score": proposal.confidence_score,
            "recommendation": proposal.recommendation,
        }
    )

    return proposal
