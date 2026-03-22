from __future__ import annotations

import json
from pathlib import Path
import shutil
import uuid

from gigai.acc_rfi_automation.config import AccRfiAutomationConfig
from gigai.acc_rfi_automation.normalize import normalize_rfis
from gigai.acc_rfi_automation.service import RfiAutomationService
from gigai.google_integrations.workspace_client import GoogleActionResult


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "acc_rfi_automation"


class FakeGoogleClient:
    def __init__(self) -> None:
        self.sent_emails: list[dict] = []
        self.created_events: list[dict] = []

    def send_email(self, to_emails, subject, body, cc_emails=None):
        self.sent_emails.append(
            {"to": to_emails, "subject": subject, "body": body, "cc": cc_emails or []}
        )
        return GoogleActionResult("sent", {"message_id": f"msg_{len(self.sent_emails)}"})

    def create_calendar_event(self, summary, description, start_datetime, end_datetime, attendees):
        self.created_events.append(
            {
                "summary": summary,
                "description": description,
                "start": start_datetime,
                "end": end_datetime,
                "attendees": attendees,
            }
        )
        return GoogleActionResult("event_created", {"event_id": f"evt_{len(self.created_events)}"})


def _fixture_path(name: str) -> Path:
    return FIXTURE_ROOT / name


def test_normalize_rfis_extracts_required_fields() -> None:
    payload = json.loads(_fixture_path("rfis_response.json").read_text(encoding="utf-8"))

    items = normalize_rfis(payload["results"])

    assert len(items) == 2
    assert items[0].id == "RFI-101"
    assert items[0].created_by == "Coordinator A"
    assert items[0].assigned_to == ["architect.one@example.com"]


def test_rfi_service_sends_email_and_calendar_once(monkeypatch) -> None:
    workspace_root = Path(".pytest_runtime") / f"acc_rfi_{uuid.uuid4().hex}"
    workspace_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("GIGAI_ACC_RFI_ROOT", str(workspace_root))

    try:
        config = AccRfiAutomationConfig.from_env(
            project_id="project_alpha",
            rfis_input_path=_fixture_path("rfis_response.json"),
        )
        fake_google = FakeGoogleClient()
        service = RfiAutomationService(config, google_client=fake_google)

        summary_first = service.run_once()
        summary_second = service.run_once()

        assert summary_first.email_sent == 1
        assert summary_first.calendar_created == 1
        assert summary_first.skipped == 1
        assert len(fake_google.sent_emails) == 1
        assert len(fake_google.created_events) == 1
        assert fake_google.sent_emails[0]["cc"] == ["Coordinator A"]

        assert summary_second.email_sent == 0
        assert summary_second.calendar_created == 0
        assert summary_second.skipped == 2

        log_content = (workspace_root / "acc-rfi-automation.log").read_text(encoding="utf-8")
        assert "RFI-101 -> Email Sent" in log_content
        assert "RFI-101 -> Calendar Created" in log_content
        assert "RFI-101 -> Skipped (Already Processed)" in log_content
        assert "RFI-102 -> Skipped (Status=closed)" in log_content
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)
