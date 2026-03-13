"""Tests for proposal builder."""
from datetime import datetime

from src.shared.models.proposals import Action, Proposal
from src.output.proposal_builder.builder import build_proposal_response


def _make_proposal():
    return Proposal(
        proposal_id="prop-001",
        event_id="evt-001",
        alert={"title": "Window Substitution", "severity": "high"},
        actions=[
            Action(
                action_type="task",
                action_data={"title": "Create RFI", "description": "Review substitution"},
            )
        ],
        confidence_score=0.85,
        recommendation="accept",
        created_at=datetime(2026, 3, 13, 12, 0, 0),
    )


def test_build_proposal_response_fields():
    proposal = _make_proposal()
    result = build_proposal_response(proposal)
    assert result["id"] == "prop-001"
    assert result["event_id"] == "evt-001"
    assert result["confidence_score"] == 85
    assert result["recommendation"] == "accept"
    assert result["alert"]["title"] == "Window Substitution"
    assert len(result["actions"]) == 1
    assert result["actions"][0]["action_type"] == "task"
    assert result["created_at"] == "2026-03-13T12:00:00"


def test_build_proposal_response_confidence_rounding():
    proposal = _make_proposal()
    proposal.confidence_score = 0.756
    result = build_proposal_response(proposal)
    assert result["confidence_score"] == 76
