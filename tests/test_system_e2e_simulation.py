from __future__ import annotations

from fastapi.testclient import TestClient

from gigai.main import app


def test_system_e2e_simulation_route_returns_full_workflow(monkeypatch) -> None:
    monkeypatch.setenv("GIGAI_GOOGLE_INTEGRATION_ENABLED", "false")
    client = TestClient(app)

    response = client.post(
        "/system/e2e/simulate",
        json={
            "project_id": "project_alpha",
            "meeting_id": "meet_01",
            "transcript": "GigAI focus on East Lobby and create revision cloud for window frame change",
            "available_spaces": ["East Lobby", "West Lobby"],
            "assign_to": "architect_1",
            "participants": ["pm@gigai.local", "architect@gigai.local"],
            "notification_emails": ["pm@gigai.local"],
            "deadline": "2026-03-25",
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "ok"
    assert payload["assigned_architect"] == "architect_1"

    pipeline = payload["pipeline"]
    assert pipeline["event"]["focus_space"] == "East Lobby"
    assert pipeline["decision"]["proposal"]
    assert pipeline["action"]["status"] in {"executed", "approval_required"}

    revision = payload["revision"]
    assert revision["status"] == "recorded"
    assert revision["dashboard"] == "updated"

    mom = payload["mom"]
    assert mom["subject"]
    assert "Minutes of Meeting" in mom["subject"]
    assert mom["email_body"]

    checklist = payload["checklist"]
    assert checklist["speech_recognized"] is True
    assert checklist["intent_structured"] is True
    assert checklist["revit_revision_logged"] is True
    assert checklist["dashboard_updated"] is True
    assert checklist["audit_logged"] is True
