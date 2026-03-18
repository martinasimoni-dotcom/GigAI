from fastapi.testclient import TestClient

from gigai.dashboard.dashboard_api import create_dashboard_app


client = TestClient(create_dashboard_app())


def test_dashboard_health_contract() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["service"] == "gigai_dashboard_api"


def test_revisions_contract() -> None:
    response = client.get("/api/revisions")

    assert response.status_code == 200
    payload = response.json()
    assert "revisions" in payload
    assert "total" in payload
    assert len(payload["revisions"]) == payload["total"]


def test_architects_contract() -> None:
    response = client.get("/api/dashboard/architects")

    assert response.status_code == 200
    payload = response.json()
    assert "architects" in payload
    assert "stats" in payload
    assert payload["stats"]["total_members"] == len(payload["architects"])


def test_task_status_update_accepts_json_body() -> None:
    response = client.post(
        "/api/tasks/task_001/status",
        json={"new_status": "completed"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["task_id"] == "task_001"
    assert payload["new_status"] == "completed"


def test_meeting_transcript_contains_compatibility_fields() -> None:
    response = client.get("/api/meetings/meet_20260315_001/transcript")

    assert response.status_code == 200
    payload = response.json()
    assert payload["transcript"] == payload["transcript_text"]
    assert "Studio Unit 504" in payload["transcript"]


def test_voice_command_requires_transcript_or_fireflies_input() -> None:
    response = client.post("/voice/command", json={})

    assert response.status_code == 400
