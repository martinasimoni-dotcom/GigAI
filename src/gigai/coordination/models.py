from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, Field


class TeamContact(BaseModel):
    name: str
    email: str
    role: str = "architect"


class RevitElementInput(BaseModel):
    element_id: str
    category: str
    level: str
    material: str | None = None
    x: float | None = None
    y: float | None = None
    z: float | None = None


class CoordinationRequest(BaseModel):
    project_id: str
    transcript: str
    project_name: str | None = None
    meeting_id: str | None = None
    fireflies_transcript_id: str | None = None
    drawing_id: str | None = None
    available_spaces: list[str] = Field(default_factory=list)
    available_revit_elements: list[RevitElementInput] = Field(default_factory=list)
    team_contacts: list[TeamContact] = Field(default_factory=list)
    execute_actions: bool = False
    due_at: datetime | None = None
    source: Literal["voice", "fireflies", "mixed"] = "voice"


class NormalizedChange(BaseModel):
    element: str
    location: str
    change_type: str
    from_material: str | None = None
    to_material: str | None = None
    quantity: int = 0
    confidence: float = Field(ge=0.0, le=1.0)


class BIMTarget(BaseModel):
    element_id: str
    category: str
    level: str
    material: str | None = None
    x: float | None = None
    y: float | None = None
    z: float | None = None


class DomainValidation(BaseModel):
    valid: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class RevitAction(BaseModel):
    highlight_element_ids: list[str] = Field(default_factory=list)
    revision_bubble_element_ids: list[str] = Field(default_factory=list)
    parameter_updates: list[dict[str, str]] = Field(default_factory=list)


class ACCAction(BaseModel):
    drawing_id: str | None = None
    markup_title: str
    markup_body: str


class EmailAction(BaseModel):
    subject: str
    body: str
    recipients: list[str] = Field(default_factory=list)


class TaskAction(BaseModel):
    title: str
    assignee: str | None = None
    due_at: datetime
    description: str


class CalendarAction(BaseModel):
    summary: str
    description: str
    start_at: datetime
    end_at: datetime
    attendees: list[str] = Field(default_factory=list)


class CoordinationPlan(BaseModel):
    plan_id: str
    project_id: str
    meeting_id: str | None = None
    transcript: str
    normalized_change: NormalizedChange
    matched_targets: list[BIMTarget] = Field(default_factory=list)
    validation: DomainValidation
    revit_action: RevitAction
    acc_action: ACCAction
    email_action: EmailAction
    task_action: TaskAction
    calendar_action: CalendarAction
    recommendation: Literal["accept", "review", "reject"]
    status: Literal["pending", "approved", "rejected", "executed"] = "pending"
    execution_results: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CoordinationPlanResponse(BaseModel):
    plan: CoordinationPlan


class CoordinationDecisionUpdate(BaseModel):
    decision: Literal["accept", "reject"]
    actor: str = "pm_user_1"
    note: str | None = None
    execute_actions: bool = True


def default_due_date() -> datetime:
    return datetime.now(UTC) + timedelta(days=3)
