"""Tests for ACC, Gmail, Calendar, and Document executors."""
import asyncio
import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.shared.models.proposals import Action


def _make_acc_action():
    return Action(
        action_type="task",
        action_data={
            "title": "Review material substitution",
            "description": "Aluminum → Wood window",
        },
    )


def _make_gmail_action():
    return Action(
        action_type="email",
        action_data={
            "to": "pm@example.com",
            "subject": "Material Change Alert",
            "body": "Please review the proposal.",
        },
    )


def _make_calendar_action():
    return Action(
        action_type="calendar",
        action_data={
            "summary": "Review Meeting",
            "description": "Discuss substitution",
            "start_datetime": "2026-03-14T10:00:00Z",
            "end_datetime": "2026-03-14T11:00:00Z",
        },
    )


def _make_document_action():
    return Action(
        action_type="drawing",
        action_data={
            "drawing_number": "A-101",
            "annotation_text": "Material changed to wood",
        },
    )


# ---------------------------------------------------------------------------
# ACC Executor
# ---------------------------------------------------------------------------

def test_acc_executor_success(monkeypatch):
    monkeypatch.setenv("ACC_PROJECT_ID", "proj-123")
    monkeypatch.setenv("ACC_ISSUES_CONTAINER_ID", "cont-456")
    action = _make_acc_action()

    with patch("src.output.action_gateway.acc_executor.acc_client.create_issue") as mock_create:
        mock_create.return_value = {"id": "issue-789"}
        from src.output.action_gateway.acc_executor import execute_acc_action
        result = asyncio.run(execute_acc_action(action))
        assert result.status == "success"
        assert "issue-789" in result.message
        mock_create.assert_called_once()


def test_acc_executor_missing_env():
    os.environ.pop("ACC_PROJECT_ID", None)
    os.environ.pop("ACC_ISSUES_CONTAINER_ID", None)
    action = _make_acc_action()
    from src.output.action_gateway.acc_executor import execute_acc_action
    with pytest.raises(RuntimeError, match="ACC_PROJECT_ID"):
        asyncio.run(execute_acc_action(action))


# ---------------------------------------------------------------------------
# Gmail Executor
# ---------------------------------------------------------------------------

def test_gmail_executor_success(monkeypatch):
    monkeypatch.setenv("GMAIL_CLIENT_ID", "cid")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "csecret")
    monkeypatch.setenv("GMAIL_REFRESH_TOKEN", "rtoken")
    action = _make_gmail_action()

    mock_creds = MagicMock()
    mock_service = MagicMock()
    mock_service.users.return_value.messages.return_value.send.return_value.execute.return_value = {"id": "msg-001"}

    with patch("google.oauth2.credentials.Credentials", return_value=mock_creds), \
         patch("google.auth.transport.requests.Request"), \
         patch("googleapiclient.discovery.build", return_value=mock_service):
        from src.output.action_gateway.gmail_executor import execute_gmail_action
        result = asyncio.run(execute_gmail_action(action))
        assert result.status == "success"
        assert "msg-001" in result.message


def test_gmail_executor_missing_creds():
    os.environ.pop("GMAIL_CLIENT_ID", None)
    os.environ.pop("GMAIL_CLIENT_SECRET", None)
    os.environ.pop("GMAIL_REFRESH_TOKEN", None)
    action = _make_gmail_action()
    from src.output.action_gateway.gmail_executor import execute_gmail_action
    with pytest.raises(RuntimeError, match="GMAIL_CLIENT_ID"):
        asyncio.run(execute_gmail_action(action))


# ---------------------------------------------------------------------------
# Calendar Executor
# ---------------------------------------------------------------------------

def test_calendar_executor_success(monkeypatch):
    monkeypatch.setenv("GMAIL_CLIENT_ID", "cid")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "csecret")
    monkeypatch.setenv("GMAIL_REFRESH_TOKEN", "rtoken")
    monkeypatch.setenv("GOOGLE_CALENDAR_ID", "primary")
    action = _make_calendar_action()

    mock_creds = MagicMock()
    mock_service = MagicMock()
    mock_service.events.return_value.insert.return_value.execute.return_value = {"id": "evt-001"}

    with patch("google.oauth2.credentials.Credentials", return_value=mock_creds), \
         patch("google.auth.transport.requests.Request"), \
         patch("googleapiclient.discovery.build", return_value=mock_service):
        from src.output.action_gateway.calendar_executor import execute_calendar_action
        result = asyncio.run(execute_calendar_action(action))
        assert result.status == "success"
        assert "evt-001" in result.message


def test_calendar_executor_missing_creds():
    os.environ.pop("GMAIL_CLIENT_ID", None)
    os.environ.pop("GMAIL_CLIENT_SECRET", None)
    os.environ.pop("GMAIL_REFRESH_TOKEN", None)
    action = _make_calendar_action()
    from src.output.action_gateway.calendar_executor import execute_calendar_action
    with pytest.raises(RuntimeError, match="GMAIL_CLIENT_ID"):
        asyncio.run(execute_calendar_action(action))


# ---------------------------------------------------------------------------
# Document Executor
# ---------------------------------------------------------------------------

def test_document_executor_success(monkeypatch):
    monkeypatch.setenv("ACC_PROJECT_ID", "proj-123")
    action = _make_document_action()

    with patch("src.output.action_gateway.document_executor.acc_client.create_drawing_markup") as mock_markup:
        mock_markup.return_value = {"id": "markup-001"}
        from src.output.action_gateway.document_executor import execute_document_action
        result = asyncio.run(execute_document_action(action))
        assert result.status == "success"
        assert "markup-001" in result.message
        mock_markup.assert_called_once()


def test_document_executor_missing_env():
    os.environ.pop("ACC_PROJECT_ID", None)
    action = _make_document_action()
    from src.output.action_gateway.document_executor import execute_document_action
    with pytest.raises(RuntimeError, match="ACC_PROJECT_ID"):
        asyncio.run(execute_document_action(action))
