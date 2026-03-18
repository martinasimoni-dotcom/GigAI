from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel


class MeetingListItem(BaseModel):
    meeting_id: str
    title: str
    date: datetime
    project: str
    participants_count: int 
    changes_detected: int
    tasks_assigned: int
    status: str


class TaskListItem(BaseModel):
    task_id: str
    space: str
    action: str
    assigned_to: str
    assigned_to_name: str
    priority: str
    deadline: str
    status: str
    days_until_due: int


class DashboardSummary(BaseModel):
    total_meetings: int
    total_changes: int
    total_tasks: int
    total_revisions: int
    pending_tasks: int
    overdue_tasks: int
    completed_tasks: int
    high_priority_tasks: int
    architects_in_team: int


class RevisionListItem(BaseModel):
    revision_id: str
    space: str
    element: str
    action: str
    applied_at: str
    status: str


class TaskStatusUpdateRequest(BaseModel):
    new_status: str


class TranscriptResponse(BaseModel):
    meeting_id: str
    transcript: str
    transcript_text: str
    lines: int
    url: str


MeetingList = List[MeetingListItem]
TaskList = List[TaskListItem]
