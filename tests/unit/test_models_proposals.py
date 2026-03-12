"""
Proposal model tests (FOUND-07): verify Signal, Action, and Proposal Pydantic v2 models.
"""
import pytest


def _import_models():
    try:
        from src.shared.models.proposals import Action, Proposal, Signal
        return Signal, Action, Proposal
    except ImportError as e:
        pytest.skip(f"proposals models not yet implemented: {e}")


def test_signal_valid():
    """Signal must instantiate with valid fields."""
    Signal, _, _ = _import_models()
    signal = Signal(signal_type="material_order_required", priority=1, payload={})
    assert signal.signal_type == "material_order_required"
    assert signal.priority == 1


def test_action_valid():
    """Action must instantiate with a valid action_type."""
    _, Action, _ = _import_models()
    action = Action(action_type="email", action_data={"to": "test@test.com"})
    assert action.action_type == "email"


def test_action_invalid_type():
    """Action must reject action_type='sms' (not in Literal)."""
    from pydantic import ValidationError
    _, Action, _ = _import_models()
    with pytest.raises(ValidationError):
        Action(action_type="sms", action_data={})


def test_proposal_confidence_score_bounds():
    """Proposal must reject confidence_score > 1.0."""
    from pydantic import ValidationError
    _, Action, Proposal = _import_models()
    with pytest.raises(ValidationError):
        Proposal(
            event_id="e1",
            alert={"title": "Test"},
            confidence_score=1.5,
            recommendation="accept",
        )


def test_proposal_valid():
    """Proposal must instantiate correctly and default status to 'pending'."""
    _, Action, Proposal = _import_models()
    action = Action(action_type="email", action_data={"to": "pm@example.com"})
    proposal = Proposal(
        event_id="e1",
        alert={"title": "Window material change"},
        actions=[action],
        confidence_score=0.86,
        recommendation="accept",
    )
    assert proposal.status == "pending"
    assert len(proposal.actions) == 1
    assert proposal.confidence_score == 0.86
