"""
Synchronous pipeline runner.

Runs the full event processing pipeline in-process:
  RawEvent -> normalize -> route -> process -> generate_proposal -> store

Used by /demo/trigger and by the Fireflies webhook when DEMO_MODE=true.
No Pub/Sub required — ideal for local runs and presentations.
"""
import logging
import time

from src.shared.models.events import RawEvent

logger = logging.getLogger(__name__)


def run_pipeline(raw_event: RawEvent) -> dict:
    """
    Run the full GigAI pipeline synchronously for a single RawEvent.

    Returns a proposal_response dict ready for the dashboard.
    Raises on unrecoverable errors.
    """
    t0 = time.perf_counter()
    logger.info("Pipeline start — event_id=%s source=%s", raw_event.event_id, raw_event.source)

    # Step 1 — Normalize (Haiku LLM)
    from src.system.data_processing.normalizer import normalize_event
    normalized = normalize_event(raw_event)
    logger.info("Normalized — event_type=%s confidence=%d", normalized.event_type, normalized.confidence)

    # Step 2 — Route
    from src.system.data_processing.router import route_event
    routed = route_event(normalized)

    # Step 3 — Domain processing (enrich + time + policy + signals)
    from src.system.domain_processing.processor import process_event
    processing_result = process_event(routed)
    logger.info(
        "Processed — rules=%s signals=%d",
        processing_result.policy_result.triggered_rules,
        len(processing_result.signals),
    )

    # Step 4 — Generate proposal (Sonnet LLM)
    from src.system.decision_intelligence.proposal_generator import generate_proposal
    proposal = generate_proposal(processing_result)

    # Step 5 — Score breakdown (pure math, no LLM)
    from src.system.decision_intelligence.confidence_scorer import score_proposal
    historical = processing_result.event.historical_matches or []
    confidence_result = score_proposal(processing_result, historical)

    pipeline_ms = int((time.perf_counter() - t0) * 1000)
    logger.info(
        "Proposal generated — id=%s score=%.1f rec=%s actions=%d pipeline_ms=%d",
        proposal.proposal_id,
        confidence_result.score,
        confidence_result.recommendation,
        len(proposal.actions),
        pipeline_ms,
    )

    # confidence_score on Proposal is stored 0.0-1.0; multiply by 100 for display
    display_score = round(confidence_result.score, 1)

    proposal_response = {
        "id": proposal.proposal_id,
        "event_id": proposal.event_id,
        "alert": {
            "title": _make_title(normalized),
            "summary": proposal.alert.get("summary", ""),
            "stakeholders": proposal.alert.get("stakeholders", []),
            "confidence_rationale": proposal.alert.get("confidence_rationale", ""),
        },
        "actions": [
            {"action_type": a.action_type, **(a.action_data or {})}
            for a in proposal.actions
        ],
        "confidence_score": display_score,
        "confidence_breakdown": {
            "data_clarity":     {"value": round(confidence_result.breakdown.get("data_clarity", 0), 1),     "weight": 30, "label": "Data Clarity"},
            "historical_match": {"value": round(confidence_result.breakdown.get("historical_match", 0), 1), "weight": 25, "label": "Historical Match"},
            "cost_acceptable":  {"value": round(confidence_result.breakdown.get("cost_acceptable", 0), 1),  "weight": 25, "label": "Cost Acceptable"},
            "no_red_flags":     {"value": round(confidence_result.breakdown.get("no_red_flags", 0), 1),     "weight": 20, "label": "No Red Flags"},
        },
        "triggered_rules": processing_result.policy_result.triggered_rules,
        "signals": [s.signal_type for s in processing_result.signals],
        "recommendation": confidence_result.recommendation,
        "pipeline_ms": pipeline_ms,
        "time_saved_minutes": 45,   # baseline from presentation slide 33
        "status": "pending",
    }

    # Store + push to dashboard via SSE
    from src.api.routes import store_proposal
    store_proposal(proposal, proposal_response)

    return proposal_response


def _make_title(normalized) -> str:
    orig = normalized.material_original or "material"
    new  = normalized.material_new or "alternative"
    loc  = normalized.location or "project site"
    qty  = f" ({normalized.quantity} units)" if normalized.quantity else ""
    return f"Material Change: {orig.title()} \u2192 {new.title()}{qty} \u2014 {loc.title()}"
