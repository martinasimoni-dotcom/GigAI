"""Tests for dashboard notifier, ACC notifier, and email notifier."""
import asyncio
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.shared.models.proposals import Action, Proposal


def _make_proposal():
    return Proposal(
        proposal_id="prop-001",
        event_id="evt-001",
        alert={"title": "Window Substitution"},
        actions=[],
        confidence_score=0.85,
        recommendation="accept",
        created_at=datetime(2026, 3, 13, 12, 0, 0),
    )


# ---------------------------------------------------------------------------
# Dashboard notifier tests
# ---------------------------------------------------------------------------

def test_notify_dashboard_enqueues():
    import src.output.notifications.dashboard_notifier as mod
    # Replace the module-level queue with a fresh one for test isolation
    original_queue = mod._queue
    mod._queue = asyncio.Queue(maxsize=100)
    try:
        mod.notify_dashboard({"id": "test-1", "data": "hello"})
        item = mod._queue.get_nowait()
        assert item == {"id": "test-1", "data": "hello"}
    finally:
        mod._queue = original_queue


def test_notify_dashboard_queue_full_drops_silently():
    import src.output.notifications.dashboard_notifier as mod
    original_queue = mod._queue
    mod._queue = asyncio.Queue(maxsize=1)
    try:
        mod.notify_dashboard({"id": "1"})
        # Second notification should be dropped, not raise
        mod.notify_dashboard({"id": "2"})
    finally:
        mod._queue = original_queue


# ---------------------------------------------------------------------------
# ACC notifier tests
# ---------------------------------------------------------------------------

def test_acc_notifier_success(monkeypatch):
    monkeypatch.setenv("ACC_ACCOUNT_ID", "acct-123")
    monkeypatch.setenv("ACC_PROJECT_ID", "proj-456")
    proposal = _make_proposal()

    with patch("src.output.notifications.acc_notifier.acc_client.send_acc_notification") as mock_send:
        mock_send.return_value = {"id": "notif-1"}
        from src.output.notifications.acc_notifier import notify_acc
        notify_acc(proposal)
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]
        assert call_kwargs["account_id"] == "acct-123"
        assert call_kwargs["project_id"] == "proj-456"


def test_acc_notifier_missing_env():
    import os
    os.environ.pop("ACC_ACCOUNT_ID", None)
    os.environ.pop("ACC_PROJECT_ID", None)
    proposal = _make_proposal()
    from src.output.notifications.acc_notifier import notify_acc
    with pytest.raises(RuntimeError, match="ACC_ACCOUNT_ID"):
        notify_acc(proposal)


# ---------------------------------------------------------------------------
# Email notifier tests
# ---------------------------------------------------------------------------

def test_notify_email_success(monkeypatch):
    monkeypatch.setenv("GMAIL_CLIENT_ID", "cid")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "csecret")
    monkeypatch.setenv("GMAIL_REFRESH_TOKEN", "rtoken")
    proposal = _make_proposal()

    mock_creds = MagicMock()
    mock_service = MagicMock()
    mock_send_result = mock_service.users.return_value.messages.return_value.send.return_value
    mock_send_result.execute.return_value = {"id": "msg-1"}

    with patch("google.oauth2.credentials.Credentials", return_value=mock_creds), \
         patch("google.auth.transport.requests.Request"), \
         patch("googleapiclient.discovery.build", return_value=mock_service):
        from src.output.notifications.email_notifier import notify_email
        notify_email(proposal, "recipient@example.com")
        mock_service.users.return_value.messages.return_value.send.assert_called_once()


def test_notify_email_missing_creds():
    import os
    os.environ.pop("GMAIL_CLIENT_ID", None)
    os.environ.pop("GMAIL_CLIENT_SECRET", None)
    os.environ.pop("GMAIL_REFRESH_TOKEN", None)
    proposal = _make_proposal()
    from src.output.notifications.email_notifier import notify_email
    with pytest.raises(RuntimeError, match="GMAIL_CLIENT_ID"):
        notify_email(proposal, "someone@example.com")
