"""
FastAPI routes — production REST API for GigAI dashboard.

Endpoints:
  GET  /api/health                     — health check
  GET  /api/proposals                  — list all proposals (with pagination)
  POST /api/proposals/{id}/decision    — accept/reject a proposal
  GET  /api/events                     — SSE stream for real-time updates
  GET  /api/audit-log                  — audit trail (LLM calls, pipeline runs)
  GET  /api/team                       — project team directory
  GET  /api/learning/stats             — GigAI learning system statistics
  GET  /api/learning/history           — decision history
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.output.action_gateway.gateway import execute_actions
from src.output.feedback.feedback_loop import record_decision
from src.output.notifications.dashboard_notifier import get_event_stream, notify_dashboard
from src.shared.models.proposals import Proposal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["proposals"])

# In-memory store (backed by DB persistence below)
_proposals: list[dict] = []
_proposal_objects: dict[str, Proposal] = {}


class DecisionRequest(BaseModel):
    decision: str
    reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@router.get("/health")
async def health():
    from src.shared.clients.acc_facade import is_using_mock
    return {
        "status": "ok",
        "version": "2.0.0",
        "acc_mode": "fallback" if is_using_mock() else "live",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/acc/data")
async def get_acc_data():
    """Pull ALL available data from ACC (or mock fallback) for the configured project."""
    from src.shared.clients.acc_facade import pull_all_project_data
    return pull_all_project_data()


@router.get("/acc/budgets")
async def get_acc_budgets():
    from src.shared.clients.acc_facade import get_budgets
    return {"budgets": get_budgets()}


@router.get("/acc/contracts")
async def get_acc_contracts():
    from src.shared.clients.acc_facade import get_contracts
    return {"contracts": get_contracts()}


@router.get("/acc/change-orders")
async def get_acc_change_orders():
    from src.shared.clients.acc_facade import get_change_orders
    return {"change_orders": get_change_orders()}


@router.get("/acc/issues")
async def get_acc_issues():
    from src.shared.clients.acc_facade import get_issues
    return {"issues": get_issues()}


@router.get("/acc/rfis")
async def get_acc_rfis():
    from src.shared.clients.acc_facade import get_rfis
    return {"rfis": get_rfis()}


@router.get("/acc/submittals")
async def get_acc_submittals():
    from src.shared.clients.acc_facade import get_submittals
    return {"submittals": get_submittals()}


@router.get("/acc/daily-logs")
async def get_acc_daily_logs():
    from src.shared.clients.acc_facade import get_daily_logs
    return {"daily_logs": get_daily_logs()}


@router.get("/acc/photos")
async def get_acc_photos():
    from src.shared.clients.acc_facade import get_photos
    return {"photos": get_photos()}


@router.get("/acc/checklists")
async def get_acc_checklists():
    from src.shared.clients.acc_facade import get_checklists
    return {"checklists": get_checklists()}


# ---------------------------------------------------------------------------
# Proposals
# ---------------------------------------------------------------------------

@router.get("/proposals")
async def get_proposals(
    status: Optional[str] = Query(None, description="Filter by status: pending, accepted, rejected"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    results = _proposals
    if status:
        results = [p for p in results if p.get("status", "pending") == status]
    total = len(results)
    page = results[offset:offset + limit]
    return {"proposals": page, "total": total, "limit": limit, "offset": offset}


@router.post("/proposals/{proposal_id}/decision")
async def post_decision(proposal_id: str, request: DecisionRequest):
    proposal_dict = next(
        (p for p in _proposals if p.get("id") == proposal_id), None
    )
    if proposal_dict is None:
        raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")

    stored_proposal = _proposal_objects.get(proposal_id)

    action_results = []
    if request.decision == "accept" and stored_proposal:
        execution = await execute_actions(stored_proposal)
        action_results = [r.model_dump() for r in execution.results]
        proposal_dict["status"] = "accepted"
    elif request.decision == "reject":
        proposal_dict["status"] = "rejected"
    else:
        proposal_dict["status"] = request.decision

    if stored_proposal:
        record_decision(
            proposal_id=proposal_id,
            decision=request.decision,
            reason=request.reason,
            proposal=stored_proposal,
        )

    # Feed decision into learning engine
    from src.intelligence.learning import record_learning
    try:
        record_learning(
            proposal_id=proposal_id,
            decision=request.decision,
            reason=request.reason,
            proposal_context=proposal_dict,
        )
    except Exception as exc:
        logger.debug("Learning record failed (non-critical): %s", exc)

    # Persist to DB (best-effort)
    _persist_decision(proposal_id, request.decision, request.reason)

    return {
        "status": "recorded",
        "proposal_id": proposal_id,
        "decision": request.decision,
        "results": action_results,
    }


# ---------------------------------------------------------------------------
# SSE Events
# ---------------------------------------------------------------------------

@router.get("/events")
async def sse_events():
    return StreamingResponse(get_event_stream(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------------------

@router.get("/audit-log")
async def get_audit_log(
    run_type: Optional[str] = Query(None, description="Filter: normalization, routing, proposal"),
    event_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Return audit trail of LLM calls."""
    try:
        from src.shared.db.postgres import fetch_all
        conditions = []
        params = []
        if run_type:
            conditions.append("run_type = %s")
            params.append(run_type)
        if event_id:
            conditions.append("event_id = %s")
            params.append(event_id)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.extend([limit, offset])
        rows = fetch_all(
            f"SELECT * FROM ai_runs {where} ORDER BY created_at DESC LIMIT %s OFFSET %s",
            tuple(params),
        )
        return {"runs": rows, "limit": limit, "offset": offset}
    except Exception as exc:
        logger.warning("Audit log query failed: %s", exc)
        return {"runs": [], "limit": limit, "offset": offset, "error": str(exc)}


# ---------------------------------------------------------------------------
# Team Directory
# ---------------------------------------------------------------------------

@router.get("/team")
async def get_team():
    """Return project team directory."""
    from src.shared.clients.acc_facade import get_team_directory
    return {"team": get_team_directory()}


# ---------------------------------------------------------------------------
# Learning System
# ---------------------------------------------------------------------------

@router.get("/learning/stats")
async def learning_stats():
    """Return GigAI learning system statistics."""
    from src.intelligence.learning import get_learning_stats
    return get_learning_stats()


@router.get("/learning/history")
async def learning_history(limit: int = Query(50, ge=1, le=200)):
    """Return decision history for learning analysis."""
    from src.intelligence.learning import get_decision_history
    return {"decisions": get_decision_history(limit)}


# ---------------------------------------------------------------------------
# Store + Persist helpers
# ---------------------------------------------------------------------------

def store_proposal(proposal: Proposal, proposal_response: dict) -> None:
    """Called by pipeline after proposal generation."""
    proposal_response["status"] = "pending"
    _proposals.append(proposal_response)
    _proposal_objects[proposal.proposal_id] = proposal
    notify_dashboard(proposal_response)
    _persist_proposal(proposal, proposal_response)
    logger.info("Proposal stored: id=%s", proposal.proposal_id)


def _persist_proposal(proposal: Proposal, response: dict) -> None:
    """Best-effort write to proposals table."""
    try:
        import json
        from src.shared.db.postgres import execute
        execute(
            """
            INSERT INTO proposals (proposal_id, event_id, alert, actions,
                                   confidence_score, recommendation, status)
            VALUES (%s::uuid, %s::uuid, %s::jsonb, %s::jsonb, %s, %s, %s)
            ON CONFLICT (proposal_id) DO NOTHING
            """,
            (
                proposal.proposal_id,
                proposal.event_id if proposal.event_id else None,
                json.dumps(response.get("alert", {})),
                json.dumps(response.get("actions", [])),
                proposal.confidence_score,
                proposal.recommendation,
                "pending",
            ),
        )
    except Exception as exc:
        logger.debug("Proposal DB persist failed (non-critical): %s", exc)


def _persist_decision(proposal_id: str, decision: str, reason: str | None) -> None:
    """Best-effort write to feedback table."""
    try:
        from src.shared.db.postgres import execute
        execute(
            """
            INSERT INTO feedback (proposal_id, decision, rejection_reason)
            VALUES (%s::uuid, %s, %s)
            """,
            (proposal_id, decision, reason),
        )
    except Exception as exc:
        logger.debug("Decision DB persist failed (non-critical): %s", exc)
