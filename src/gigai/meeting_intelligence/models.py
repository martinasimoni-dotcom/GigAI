"""
Data models for Meeting Intelligence Module
"""

from datetime import datetime, date
from typing import Any, Optional
from pydantic import BaseModel, Field


class ArchitecturalChange(BaseModel):
    """Represents a detected design change from meeting transcript"""

    change_id: str = Field(default_factory=lambda: f"change_{datetime.now().timestamp()}")
    project: str
    space: str  # e.g., "Studio Unit 504"
    element_type: str  # e.g., "window", "door", "wall"
    action: str  # e.g., "resize", "move", "modify", "add", "remove"
    description: str
    timestamp: datetime
    confidence: float = Field(ge=0.0, le=1.0)
    speaker: Optional[str] = None
    transcript_reference: str  # Timestamp in transcript, e.g., "10:21:32"
    extracted_properties: dict[str, Any] = Field(default_factory=dict)
    affected_elements: list[str] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "change_id": "change_1710505200",
                "project": "Residential Tower A",
                "space": "Studio Unit 504",
                "element_type": "window",
                "action": "resize",
                "description": "Increase window width to improve daylight (min 2.4m width target)",
                "timestamp": "2026-03-15T10:21:32",
                "confidence": 0.92,
                "speaker": "Architect_A",
                "transcript_reference": "10:21:32",
                "affected_elements": ["W-101", "W-102"],
                "extracted_properties": {"target_width": "2.4m"}
            }
        }


class BIMElement(BaseModel):
    """Represents a BIM element (window, door, wall, etc.)"""

    element_id: str  # Revit ElementId
    element_type: str  # "window", "door", "wall", "room", etc.
    space_name: str  # Room/space containing element
    space_id: Optional[str] = None  # Revit Room ElementId
    family: Optional[str] = None  # Revit Family name
    symbol: Optional[str] = None  # Revit Type
    current_properties: dict[str, Any] = Field(default_factory=dict)
    location: dict[str, float] = Field(default_factory=dict)  # x, y, z coordinates
    parameters: dict[str, Any] = Field(default_factory=dict)
    level: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "element_id": "123456",
                "element_type": "window",
                "space_name": "Studio 504",
                "space_id": "789012",
                "family": "Fixed Window",
                "symbol": "1200x1500",
                "current_properties": {"width": 1.2, "height": 1.5},
                "location": {"x": 10.5, "y": 5.2, "z": 1.0},
                "parameters": {"Mark": "W-101", "Comments": "Client view"},
                "level": "Level 05"
            }
        }


class MeetingContext(BaseModel):
    """Context information about a meeting"""

    meeting_id: str
    fireflies_meeting_id: Optional[str] = None
    title: str
    project_id: str
    project_name: str
    date: datetime
    duration_minutes: int
    participants: list[str] = Field(default_factory=list)
    transcript_text: Optional[str] = None
    transcript_url: Optional[str] = None
    summary: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_schema_extra = {
            "example": {
                "meeting_id": "meet_20260315_001",
                "fireflies_meeting_id": "ff_abc123",
                "title": "Architecture Coordination - Phase 5",
                "project_id": "proj_123",
                "project_name": "Residential Tower A",
                "date": "2026-03-15T10:15:00",
                "duration_minutes": 45,
                "participants": ["Architect_A", "Architect_B", "Architect_C"],
                "transcript_url": "https://app.fireflies.ai/...",
                "summary": "Discussed design changes for studio units and corridor modifications"
            }
        }


class TaskAssignment(BaseModel):
    """Task assignment to an architect"""

    assignment_id: str = Field(default_factory=lambda: f"assign_{datetime.now().timestamp()}")
    decision_id: str  # Reference to GigAI decision
    change_id: str  # Reference to architectural change
    assigned_to: str  # Email address
    assigned_to_name: str
    assigned_to_role: str  # "Unit Designer", "M&E Lead", etc.
    space: str
    action: str
    description: str
    priority: str = Field(pattern="^(LOW|MEDIUM|HIGH)$")
    deadline: date
    calendar_event_id: Optional[str] = None
    email_sent: bool = False
    status: str = Field(default="pending", pattern="^(pending|in_progress|completed|on_hold)$")
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_schema_extra = {
            "example": {
                "assignment_id": "assign_1710505200",
                "decision_id": "d_456",
                "change_id": "change_1710505200",
                "assigned_to": "alice@company.com",
                "assigned_to_name": "Alice Johnson",
                "assigned_to_role": "Unit Designer",
                "space": "Studio 504",
                "action": "resize",
                "description": "Increase window width to 2.4m",
                "priority": "HIGH",
                "deadline": "2026-03-22",
                "calendar_event_id": "cal_xyz789",
                "email_sent": True,
                "status": "in_progress"
            }
        }


class RevisionMarker(BaseModel):
    """Revit revision cloud and comment"""

    revision_id: str = Field(default_factory=lambda: f"rev_{datetime.now().timestamp()}")
    decision_id: str
    change_id: str
    revit_element_id: str
    revit_project_id: str
    space_name: str
    revision_type: str = Field(default="NEW_REVISION")
    revision_number: Optional[int] = None
    revision_date: datetime = Field(default_factory=datetime.now)

    # Revision cloud properties
    cloud_id: Optional[str] = None  # Revit RevisionCloud ElementId
    shape_type: str = Field(default="CLOUD")  # CLOUD, POLYGON, RECTANGLE
    color: str = Field(default="FF0000")  # Red hex color

    # Attached comment
    comment_text: str
    comment_details: dict[str, str] = Field(default_factory=dict)
    requested_by: str  # Meeting speaker

    # Status
    applied: bool = False
    applied_at: Optional[datetime] = None
    applied_by: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "revision_id": "rev_1710505200",
                "decision_id": "d_456",
                "change_id": "change_1710505200",
                "revit_element_id": "123456",
                "revit_project_id": "rvt_proj_001",
                "space_name": "Studio 504",
                "revision_number": 1,
                "revision_date": "2026-03-15T10:30:00",
                "cloud_id": "rev_cloud_001",
                "color": "FF0000",
                "comment_text": "DESIGN CHANGE: Increase window width to 2.4m for improved daylight",
                "comment_details": {
                    "action": "resize",
                    "element": "window",
                    "target_width": "2.4m",
                    "reason": "improve daylight"
                },
                "requested_by": "Architect_A",
                "applied": True,
                "applied_at": "2026-03-15T10:32:00",
                "applied_by": "GigAI_System"
            }
        }


class MeetingMinutes(BaseModel):
    """Structured meeting minutes"""

    meeting_id: str
    title: str
    date: datetime
    participants: list[str]
    duration_minutes: int
    project: str

    decisions: list[dict[str, Any]] = Field(default_factory=list)
    summary: str
    action_items: list[dict[str, Any]] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    next_steps: str

    generated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_schema_extra = {
            "example": {
                "meeting_id": "meet_20260315_001",
                "title": "Architecture Coordination - Phase 5",
                "date": "2026-03-15T10:15:00",
                "participants": ["Architect_A", "Architect_B"],
                "duration_minutes": 45,
                "project": "Residential Tower A",
                "decisions": [
                    {
                        "order": 1,
                        "space": "Studio 504",
                        "element": "window",
                        "action": "Increase width",
                        "assigned_to": "Alice Johnson",
                        "priority": "HIGH",
                        "deadline": "2026-03-22"
                    }
                ],
                "summary": "Discussed design changes for studio units and corridor modifications",
                "action_items": [
                    {"task": "Update window dimensions", "assigned_to": "Alice", "due": "2026-03-22"}
                ],
                "risks": ["Tight deadline for implementation"],
                "next_steps": "Follow-up meeting on 2026-03-22 to review progress"
            }
        }


class MeetingIntelligenceResult(BaseModel):
    """Complete result from meeting intelligence processing"""

    meeting_id: str
    meeting_context: MeetingContext
    architectural_changes: list[ArchitecturalChange] = Field(default_factory=list)
    identified_elements: list[BIMElement] = Field(default_factory=list)
    task_assignments: list[TaskAssignment] = Field(default_factory=list)
    revision_markers: list[RevisionMarker] = Field(default_factory=list)
    meeting_minutes: Optional[MeetingMinutes] = None

    processing_time_seconds: float
    success: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=datetime.now)
