from __future__ import annotations

from datetime import datetime, timedelta

from gigai.dashboard.models import DashboardSummary, MeetingListItem, TaskListItem, TranscriptResponse
from gigai.storage import list_bus_events


def _runtime_revisions_from_bus(limit: int = 200) -> list[dict]:
    revisions: list[dict] = []
    for row in list_bus_events(limit=limit):
        if row.get("topic") != "revit.revision_marked":
            continue
        payload = row.get("payload_json") or {}
        revision_id = str(payload.get("revision_id") or f"rev_{row.get('id')}")
        revisions.append(
            {
                "revision_id": revision_id,
                "meeting_id": str(payload.get("meeting_id") or "meeting_unknown"),
                "meeting_title": str(payload.get("meeting_title") or "Revit Revision"),
                "space_name": str(payload.get("space_name") or "Unknown Space"),
                "element_type": str(payload.get("element_type") or "element"),
                "action": str(payload.get("action") or "REVISION_MARKED"),
                "comment_text": str(payload.get("comment_text") or ""),
                "applied_at": str(payload.get("applied_at") or row.get("created_at") or datetime.now().isoformat()),
                "applied_by": str(payload.get("applied_by") or "Revit User"),
                "priority": str(payload.get("priority") or "HIGH"),
            }
        )
    return revisions


def build_meetings() -> list[MeetingListItem]:
    return [
        MeetingListItem(
            meeting_id="meet_20260315_001",
            title="Architecture Coordination - Phase 5",
            date=datetime.now() - timedelta(hours=2),
            project="Residential Tower A",
            participants_count=4,
            changes_detected=4,
            tasks_assigned=4,
            status="completed",
        ),
        MeetingListItem(
            meeting_id="meet_20260314_001",
            title="Design Review - Facade",
            date=datetime.now() - timedelta(days=1),
            project="Residential Tower A",
            participants_count=3,
            changes_detected=2,
            tasks_assigned=2,
            status="completed",
        ),
    ]


def build_meeting_detail(meeting_id: str) -> dict:
    return {
        "meeting_id": meeting_id,
        "title": "Architecture Coordination - Phase 5",
        "date": datetime.now() - timedelta(hours=2),
        "project": "Residential Tower A",
        "duration_minutes": 45,
        "participants": ["Architect_A", "Architect_B", "Architect_C"],
        "transcript_url": "https://fireflies.ai/...",
        "summary": "Discussed design changes for studio units and corridor modifications",
        "changes": [
            {
                "space": "Studio 504",
                "action": "resize",
                "element": "window",
                "description": "Increase window width from 1.2m to 2.4m",
                "confidence": 0.92,
            }
        ],
        "tasks": [
            {
                "task_id": "task_001",
                "assigned_to": "Alice Johnson",
                "priority": "HIGH",
                "deadline": "2026-03-22",
                "status": "pending",
            }
        ],
    }


def build_meeting_transcript(meeting_id: str) -> TranscriptResponse:
    transcript = (
        "Architect_A: Good morning everyone. Let's start with the studio units. "
        "We need to increase the window size in Studio Unit 504.\n"
        "Architect_A: The existing window is 1.2 meters wide. We should expand it to at least 2.4 meters for better natural light.\n"
        "Architect_B: Agreed. That will significantly improve the daylight factor."
    )
    return TranscriptResponse(
        meeting_id=meeting_id,
        transcript=transcript,
        transcript_text=transcript,
        lines=15,
        url="https://fireflies.ai/...",
    )


def build_tasks() -> list[TaskListItem]:
    return [
        TaskListItem(
            task_id="task_001",
            space="Studio 504",
            action="resize",
            assigned_to="alice.johnson@company.com",
            assigned_to_name="Alice Johnson",
            priority="HIGH",
            deadline="2026-03-22",
            status="pending",
            days_until_due=7,
        ),
        TaskListItem(
            task_id="task_002",
            space="Corridor B",
            action="move",
            assigned_to="david.lee@company.com",
            assigned_to_name="David Lee",
            priority="MEDIUM",
            deadline="2026-03-29",
            status="pending",
            days_until_due=14,
        ),
    ]


def build_task_detail(task_id: str) -> dict:
    return {
        "task_id": task_id,
        "assignment_id": "assign_001",
        "decision_id": "d_001",
        "change_id": "change_001",
        "space": "Studio 504",
        "action": "resize",
        "description": "Increase window width from 1.2m to 2.4m",
        "assigned_to": "alice.johnson@company.com",
        "assigned_to_name": "Alice Johnson",
        "assigned_to_role": "Unit Designer",
        "priority": "HIGH",
        "deadline": "2026-03-22",
        "status": "pending",
        "created_at": "2026-03-15T10:32:00",
        "updated_at": "2026-03-15T10:32:00",
        "meeting_reference": "meet_20260315_001",
        "revision_cloud_id": "rev_cloud_001",
        "email_sent": True,
        "calendar_event_id": "cal_xyz789",
    }


def build_meeting_revisions(meeting_id: str) -> dict:
    return {
        "meeting_id": meeting_id,
        "revisions": [
            {
                "revision_id": "rev_001",
                "space": "Studio 504",
                "element": "window",
                "action": "resize",
                "cloud_id": "rev_cloud_001",
                "applied": True,
                "comment": "DESIGN CHANGE: Resize window...",
            }
        ],
    }


def build_dashboard_summary() -> DashboardSummary:
    runtime_revisions = _runtime_revisions_from_bus(limit=500)
    return DashboardSummary(
        total_meetings=12,
        total_changes=34,
        total_tasks=34,
        total_revisions=34 + len(runtime_revisions),
        pending_tasks=8,
        overdue_tasks=2,
        completed_tasks=24,
        high_priority_tasks=5,
        architects_in_team=7,
    )


def build_timeline() -> dict:
    return {
        "meetings": [
            {
                "id": "meet_001",
                "title": "Architecture Coordination",
                "start": "2026-03-15T10:00:00",
                "end": "2026-03-15T10:45:00",
                "type": "meeting",
            }
        ],
        "tasks": [
            {
                "id": "task_001",
                "title": "Resize window - Studio 504",
                "start": "2026-03-15T10:32:00",
                "end": "2026-03-22",
                "type": "task",
                "status": "pending",
                "priority": "HIGH",
            }
        ],
    }


def build_meeting_decisions(meeting_id: str) -> dict:
    return {
        "meeting_id": meeting_id,
        "decisions": [
            {
                "order": 1,
                "space": "Studio 504",
                "element": "window",
                "action": "RESIZE",
                "description": "Increase window width from 1.2m to 2.4m for better daylight",
                "assigned_to": "Alice Johnson",
                "priority": "HIGH",
                "deadline": "2026-03-22",
            },
            {
                "order": 2,
                "space": "Corridor B",
                "element": "wall",
                "action": "MOVE",
                "description": "Move wall 300mm to the south for better clearance",
                "assigned_to": "David Lee",
                "priority": "MEDIUM",
                "deadline": "2026-03-29",
            },
        ],
    }


def build_revisions() -> dict:
    static_revisions = [
            {
                "revision_id": "rev_001",
                "meeting_id": "meet_20260315_001",
                "meeting_title": "Architecture Coordination - Phase 5",
                "space_name": "Studio 504",
                "element_type": "window",
                "action": "RESIZE",
                "comment_text": "DESIGN CHANGE: Increase window width from 1.2m to 2.4m. Natural daylight improvement.",
                "applied_at": (datetime.now() - timedelta(hours=1)).isoformat(),
                "applied_by": "System",
                "priority": "HIGH",
            },
            {
                "revision_id": "rev_002",
                "meeting_id": "meet_20260315_001",
                "meeting_title": "Architecture Coordination - Phase 5",
                "space_name": "Corridor B",
                "element_type": "wall",
                "action": "MOVE",
                "comment_text": "DESIGN CHANGE: Move wall 300mm south. Improves floor clearance.",
                "applied_at": (datetime.now() - timedelta(hours=2)).isoformat(),
                "applied_by": "System",
                "priority": "MEDIUM",
            },
        ]

    runtime_revisions = _runtime_revisions_from_bus(limit=500)
    merged = runtime_revisions + static_revisions

    seen: set[str] = set()
    deduped: list[dict] = []
    for revision in merged:
        revision_id = str(revision.get("revision_id") or "")
        if revision_id and revision_id in seen:
            continue
        if revision_id:
            seen.add(revision_id)
        deduped.append(revision)

    return {
        "revisions": deduped,
        "total": len(deduped),
    }


def build_team_workload() -> dict:
    return {
        "architects": [
            {
                "name": "Alice Johnson",
                "role": "Unit Designer",
                "email": "alice.johnson@company.com",
                "pending_tasks": 3,
                "in_progress_tasks": 2,
                "completed_tasks": 8,
                "workload_percentage": 75,
                "overdue_count": 0,
                "upcoming_deadline": (datetime.now() + timedelta(days=3)).isoformat(),
            },
            {
                "name": "David Lee",
                "role": "M&E Lead",
                "email": "david.lee@company.com",
                "pending_tasks": 2,
                "in_progress_tasks": 1,
                "completed_tasks": 5,
                "workload_percentage": 50,
                "overdue_count": 0,
                "upcoming_deadline": (datetime.now() + timedelta(days=5)).isoformat(),
            },
            {
                "name": "Sarah Chen",
                "role": "Facade Designer",
                "email": "sarah.chen@company.com",
                "pending_tasks": 1,
                "in_progress_tasks": 0,
                "completed_tasks": 12,
                "workload_percentage": 25,
                "overdue_count": 0,
                "upcoming_deadline": (datetime.now() + timedelta(days=7)).isoformat(),
            },
            {
                "name": "Marcus Williams",
                "role": "Structural Lead",
                "email": "marcus.williams@company.com",
                "pending_tasks": 2,
                "in_progress_tasks": 3,
                "completed_tasks": 6,
                "workload_percentage": 85,
                "overdue_count": 1,
                "upcoming_deadline": (datetime.now() + timedelta(days=2)).isoformat(),
            },
        ],
        "stats": {
            "total_members": 4,
            "total_tasks": 9,
            "avg_workload": 58.75,
            "overdue_count": 1,
            "completion_rate": 78,
        },
    }


def build_webhook_response() -> dict:
    return {"status": "received", "message": "Meeting end webhook processed"}


def build_export_response(meeting_id: str) -> dict:
    return {
        "status": "success",
        "message": f"PDF generated for meeting {meeting_id}",
        "download_url": f"/api/files/meeting_{meeting_id}.pdf",
    }


def build_dashboard_update() -> dict:
    return {
        "type": "dashboard_update",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "pending_tasks": 8,
            "overdue_tasks": 2,
            "completed_today": 3,
        },
    }
