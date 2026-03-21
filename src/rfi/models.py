"""
Pydantic v2 models for RFI/Submittal automation.

An RFI (Request for Information) represents a question detected from
project communications that needs a formal response, often involving
spec clarification, material substitution, or code compliance.
"""
import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


RFIStatus = Literal["open", "drafted", "reviewed", "sent", "responded", "closed"]
RFIPriority = Literal["low", "medium", "high", "critical"]


class RFIResponse(BaseModel):
    """AI-drafted or PM-edited response to an RFI."""
    model_config = ConfigDict(str_strip_whitespace=True)

    draft_text: str
    knowledge_sources: list[str] = Field(default_factory=list)
    past_rfi_references: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    drafted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    edited_by_pm: bool = False
    pm_edits: Optional[str] = None


class RFI(BaseModel):
    """A Request for Information detected from project communications."""
    model_config = ConfigDict(str_strip_whitespace=True)

    rfi_id: str = Field(default_factory=lambda: f"RFI-{uuid.uuid4().hex[:8].upper()}")
    inbox_item_id: Optional[str] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    title: str
    question: str
    category: str = "general"
    status: RFIStatus = "open"
    priority: RFIPriority = "medium"
    assignee: Optional[str] = None
    assignee_email: Optional[str] = None
    requester: str
    requester_email: Optional[str] = None
    source: str = "detected"
    response: Optional[RFIResponse] = None
    sent_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("title must not be empty")
        return v

    @property
    def age_hours(self) -> int:
        return int((datetime.now(timezone.utc) - self.created_at).total_seconds() / 3600)
