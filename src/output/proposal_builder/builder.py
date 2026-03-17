"""Proposal Builder (OUT-01): assembles dashboard-ready proposal response dict."""
import logging

from src.shared.models.proposals import Proposal

logger = logging.getLogger(__name__)


def build_proposal_response(proposal: Proposal) -> dict:
    """Build a dashboard-ready dict from a Proposal."""
    actions_formatted = []
    for action in proposal.actions:
        data = action.action_data or {}
        # Try multiple candidate keys before falling back to empty string
        description = (
            data.get("description")
            or data.get("subject")       # email subject is meaningful as description
            or data.get("summary")       # calendar event summary
            or data.get("title")         # ACC issue title
            or data.get("body", "")[:120]  # truncated email body as last resort
        ) or ""
        actions_formatted.append({
            "action_type": action.action_type,
            "description": description,
            "action_data": data,
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
