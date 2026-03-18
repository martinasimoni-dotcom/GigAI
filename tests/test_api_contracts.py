from fastapi import BackgroundTasks

from gigai.main import bim360_webhook, reject, replay, revit_location_marked_mom
from gigai.orchestrator import process_webhook


def test_bim360_webhook_returns_accepted_contract() -> None:
    background_tasks = BackgroundTasks()

    accepted = bim360_webhook(
        {
            "id": "evt_contract_webhook",
            "eventType": "issue.updated",
            "projectId": "project_alpha",
            "status": "open",
        },
        background_tasks,
    )

    assert accepted.status == "accepted"
    assert accepted.event_id == "evt_contract_webhook"
    assert accepted.idempotent is False
    assert len(background_tasks.tasks) == 1


def test_replay_endpoint_reprocesses_event() -> None:
    result = process_webhook(
        {
            "id": "evt_contract_replay",
            "eventType": "issue.updated",
            "projectId": "project_alpha",
            "status": "open",
        }
    )

    replayed = replay(result.event.event_id)

    assert replayed.event.event_id == result.event.event_id
    assert replayed.decision.event_id == result.event.event_id


def test_reject_endpoint_resolves_pending_approval() -> None:
    result = process_webhook(
        {
            "id": "evt_contract_reject",
            "eventType": "issue.updated",
            "projectId": "project_alpha",
            "status": "blocked",
            "due_overrun_days": 6,
        }
    )

    resolved = reject(result.action.approval_id or "", {"actor": "pm_bob", "note": "needs revision"})

    assert resolved.status == "rejected"
    assert resolved.action_status == "rejected"


def test_revit_location_marked_mom_contract() -> None:
    payload = {
        "event_type": "Revit Location Marked",
        "project": {
            "name": "Residential Tower A",
            "assigned_team": "Architecture Coordination Team",
            "task_references": ["TASK-100", "TASK-101"],
            "related_revisions": ["REV-22"],
        },
        "bim": {
            "marked_location": "Studio Unit 504",
            "element_ids": ["123456", "123457"],
            "element_categories": ["Window", "Wall"],
            "sheet_numbers": ["A-501"],
            "model_version": "R5",
        },
        "meeting": {
            "timestamp": "2026-03-17 10:30",
            "duration": "45 minutes",
            "participants": ["Architect A", "PM B"],
        },
        "detected_changes": {
            "key_discussions": ["Window opening adjustment for daylight."],
            "decisions": ["Increase opening width in Studio Unit 504."],
            "issues": ["Potential clash with wall finish alignment."],
            "action_items": [
                {
                    "task": "Update window family dimensions",
                    "responsible": "Architect A",
                    "deadline": "2026-03-20",
                }
            ],
        },
        "attachments": ["A-501.pdf", "Snapshot_Studio504.png"],
    }

    response = revit_location_marked_mom(payload)

    assert response["event_confirmation"] == "Meeting Completed"
    assert "Minutes of Meeting" in response["subject"]
    assert "Studio Unit 504" in response["subject"]
    assert "1. Meeting Details" in response["email_body"]
    assert "5. Action Items" in response["email_body"]
