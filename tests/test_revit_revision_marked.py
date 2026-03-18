from __future__ import annotations

from fastapi.testclient import TestClient

from gigai.main import app
from gigai.storage import list_bus_events


def test_revit_revision_marked_records_event_and_returns_email_status(monkeypatch) -> None:
    monkeypatch.setenv("GIGAI_GOOGLE_INTEGRATION_ENABLED", "false")
    client = TestClient(app)

    response = client.post(
        "/revit/revision-marked",
        json={
            "revision_id": "rev_123",
            "meeting_id": "meet_abc",
            "project_id": "project_alpha",
            "space_name": "Studio 504",
            "element_type": "window",
            "action": "REVISION_MARKED",
            "comment_text": "Revision cloud placed",
            "applied_by": "tester",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "recorded"
    assert payload["dashboard"] == "updated"
    assert payload["event_topic"] == "revit.revision_marked"
    assert payload["revision_id"] == "rev_123"
    assert payload["email"]["status"] in {"disabled", "skipped", "sent"}

    events = list_bus_events(limit=20)
    assert any(event["topic"] == "revit.revision_marked" for event in events)
