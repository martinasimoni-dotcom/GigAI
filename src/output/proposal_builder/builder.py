"""Proposal Builder (OUT-01): assembles dashboard-ready proposal response dict."""
import logging

from src.shared.models.proposals import Proposal

logger = logging.getLogger(__name__)


def build_proposal_response(proposal: Proposal) -> dict:
    """Build a dashboard-ready dict from a Proposal."""
    actions_formatted = []
    for action in proposal.actions:
        actions_formatted.append({
            "action_type": action.action_type,
            "description": action.action_data.get("description", ""),
            "action_data": action.action_data,
        })

    return {
        "id": proposal.proposal_id,
        "event_id": proposal.event_id,
        "alert": proposal.alert,
        "actions": actions_formatted,
        "confidence_score": round(proposal.confidence_score * 100),
        "recommendation": proposal.recommendation,
        "created_at": proposal.created_at.isoformat(),
    }
