"""Tests for the Action Gateway — parallel dispatch and exception isolation."""
import asyncio
import os
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from src.output.action_gateway import ActionResult
from src.shared.models.proposals import Action, Proposal

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("VOYAGE_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")


def _make_proposal_with_actions():
    return Proposal(
        proposal_id="prop-gw-001",
        event_id="evt-gw-001",
        alert={"title": "Window Substitution"},
        actions=[
            Action(action_type="task", action_data={"title": "T", "description": "D"}),
            Action(action_type="email", action_data={"to": "a@b.com", "subject": "S", "body": "B"}),
            Action(action_type="calendar", action_data={
                "summary": "M", "description": "D",
                "start_datetime": "2026-03-14T10:00:00Z",
                "end_datetime": "2026-03-14T11:00:00Z",
            }),
            Action(action_type="drawing", action_data={"drawing_number": "A-1", "annotation_text": "X"}),
        ],
        confidence_score=0.9,
        recommendation="accept",
        created_at=datetime(2026, 3, 13, 12, 0, 0),
    )


def test_execute_actions_all_success():
    proposal = _make_proposal_with_actions()
    success_result = ActionResult(action_type="task", status="success", message="ok")
    mock_fn = AsyncMock(return_value=success_result)

    with patch("src.output.action_gateway.acc_executor.execute_acc_action", new=mock_fn), \
         patch("src.output.action_gateway.gmail_executor.execute_gmail_action", new=mock_fn), \
         patch("src.output.action_gateway.calendar_executor.execute_calendar_action", new=mock_fn), \
         patch("src.output.action_gateway.document_executor.execute_document_action", new=mock_fn):

        from src.output.action_gateway.gateway import execute_actions
        result = asyncio.run(execute_actions(proposal))
        assert result.success_count == 4
        assert result.failure_count == 0
        assert result.proposal_id == "prop-gw-001"


def test_execute_actions_partial_failure():
    proposal = _make_proposal_with_actions()
    success_result = ActionResult(action_type="email", status="success", message="ok")

    with patch("src.output.action_gateway.acc_executor.execute_acc_action",
               new=AsyncMock(side_effect=RuntimeError("ACC env missing"))), \
         patch("src.output.action_gateway.gmail_executor.execute_gmail_action",
               new=AsyncMock(return_value=success_result)), \
         patch("src.output.action_gateway.calendar_executor.execute_calendar_action",
               new=AsyncMock(return_value=success_result)), \
         patch("src.output.action_gateway.document_executor.execute_document_action",
               new=AsyncMock(return_value=success_result)):

        from src.output.action_gateway.gateway import execute_actions
        result = asyncio.run(execute_actions(proposal))
        assert result.failure_count == 1
        assert result.success_count == 3
        failed = [r for r in result.results if r.status == "failed"]
        assert len(failed) == 1
        assert "ACC env missing" in failed[0].error


def test_execute_actions_unknown_type():
    proposal = Proposal(
        proposal_id="prop-unk",
        event_id="evt-unk",
        alert={},
        actions=[Action(action_type="drawing", action_data={"drawing_number": "X", "annotation_text": "Y"})],
        confidence_score=0.5,
        recommendation="review",
        created_at=datetime(2026, 3, 13),
    )
    with patch("src.output.action_gateway.gateway.EXECUTOR_MAP", {}):
        from src.output.action_gateway.gateway import execute_actions
        result = asyncio.run(execute_actions(proposal))
        assert result.failure_count == 1
        assert "Unknown action_type" in result.results[0].error
