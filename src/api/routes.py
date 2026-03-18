"""FastAPI routes (OUT-11): all REST endpoints."""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.output.action_gateway.gateway import execute_actions
from src.output.feedback.feedback_loop import record_decision
from src.output.notifications.dashboard_notifier import get_event_stream, notify_dashboard
from src.shared.models.proposals import Proposal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["proposals"])

_proposals: list[dict] = []
_proposal_objects: dict[str, Proposal] = {}


class DecisionRequest(BaseModel):
    decision: str
    reason: Optional[str] = None


@router.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


@router.get("/proposals")
async def get_proposals():
    return _proposals


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

    if stored_proposal:
        record_decision(
            proposal_id=proposal_id,
            decision=request.decision,
            reason=request.reason,
            proposal=stored_proposal,
        )

    return {
        "status": "recorded",
        "proposal_id": proposal_id,
        "decision": request.decision,
        "results": action_results,
    }


@router.get("/events")
async def sse_events():
    return StreamingResponse(get_event_stream(), media_type="text/event-stream")


def store_proposal(proposal: Proposal, proposal_response: dict) -> None:
    """Called by main pipeline after proposal generation."""
    _proposals.append(proposal_response)
    _proposal_objects[proposal.proposal_id] = proposal
    notify_dashboard(proposal_response)
    logger.info("Proposal stored: id=%s", proposal.proposal_id)
