from fastapi.testclient import TestClient

from gigai.dashboard.dashboard_api import create_dashboard_app
from gigai.storage import publish_bus_event


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


def test_meeting_revisions_include_runtime_revit_events() -> None:
    publish_bus_event(
        "revit.revision_marked",
        {
            "revision_id": "rev_runtime_meeting_01",
            "meeting_id": "meet_runtime_01",
            "meeting_title": "Runtime Meeting",
            "project_id": "project_alpha",
            "space_name": "East Lobby",
            "element_type": "Window",
            "action": "REVISION_MARKED",
            "comment_text": "Bubble remark from Revit",
            "applied_by": "tester",
            "view_name": "Level 01",
            "cloud_id": "cloud_01",
            "note_id": "note_01",
        },
    )

    response = client.get("/api/meetings/meet_runtime_01/revisions")

    assert response.status_code == 200
    payload = response.json()
    assert payload["meeting_id"] == "meet_runtime_01"
    assert any(item["revision_id"] == "rev_runtime_meeting_01" for item in payload["revisions"])
    matching = next(item for item in payload["revisions"] if item["revision_id"] == "rev_runtime_meeting_01")
    assert matching["comment_text"] == "Bubble remark from Revit"
    assert matching["view_name"] == "Level 01"


def test_dashboard_websocket_streams_new_revision_events() -> None:
    with client.websocket_connect("/ws/dashboard/test-session") as websocket:
        publish_bus_event(
            "revit.revision_marked",
            {
                "revision_id": "rev_ws_01",
                "meeting_id": "meet_ws_01",
                "meeting_title": "Realtime Meeting",
                "space_name": "West Core",
                "element_type": "Door",
                "action": "REVISION_MARKED",
                "comment_text": "Realtime revision bubble",
                "applied_by": "tester",
            },
        )

        received = None
        for _ in range(4):
            payload = websocket.receive_json()
            if payload.get("type") == "revision_marked" and payload.get("revision", {}).get("revision_id") == "rev_ws_01":
                received = payload
                break

        assert received is not None
        assert received["revision"]["comment_text"] == "Realtime revision bubble"


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
