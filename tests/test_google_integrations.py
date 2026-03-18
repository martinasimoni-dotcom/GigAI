from gigai.orchestrator import process_webhook
from gigai.google_integrations.workspace_client import GoogleActionResult


def _base_payload() -> dict:
    return {
        "id": "evt_google_integration",
        "eventType": "issue.updated",
        "projectId": "project_alpha",
        "artifactId": "issue_google_1",
        "status": "open",
        "due_overrun_days": 0,
        "participants": [
            {"email": "architect.one@example.com"},
            {"email": "architect.two@example.com"},
        ],
    }


def test_google_email_and_calendar_are_used_when_available(monkeypatch) -> None:
    monkeypatch.setenv("GIGAI_GOOGLE_INTEGRATION_ENABLED", "true")
    monkeypatch.setenv("GMAIL_CLIENT_ID", "cid")
    monkeypatch.setenv("GMAIL_CLIENT_SECRET", "secret")
    monkeypatch.setenv("GMAIL_REFRESH_TOKEN", "refresh")

    monkeypatch.setattr(
        "gigai.google_integrations.workspace_client.GoogleWorkspaceClient.send_email",
        lambda self, to_emails, subject, body: GoogleActionResult(
            "sent", {"message_id": "msg_123", "to": to_emails}
        ),
    )
    monkeypatch.setattr(
        "gigai.google_integrations.workspace_client.GoogleWorkspaceClient.create_calendar_event",
        lambda self, summary, description, start_datetime, end_datetime, attendees: GoogleActionResult(
            "event_created", {"event_id": "cal_123", "html_link": "https://calendar.google.com/e/123"}
        ),
    )

    result = process_webhook(_base_payload())

    assert result.action.outputs["email"] == "sent_via_google"
    assert result.action.outputs["google_email"] == "sent"
    assert result.action.outputs["google_email_message_id"] == "msg_123"
    assert result.action.outputs["google_calendar"] == "event_created"
    assert result.action.outputs["google_calendar_event_id"] == "cal_123"


def test_google_email_skipped_without_credentials_preserves_pipeline(monkeypatch) -> None:
    monkeypatch.setenv("GIGAI_GOOGLE_INTEGRATION_ENABLED", "true")
    monkeypatch.delenv("GMAIL_CLIENT_ID", raising=False)
    monkeypatch.delenv("GMAIL_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("GMAIL_REFRESH_TOKEN", raising=False)

    result = process_webhook(_base_payload())

    assert result.action.status == "executed"
    assert result.action.outputs["google_email"] == "skipped"
    assert result.action.outputs["google_calendar"] == "skipped"
