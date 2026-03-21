"""
Pydantic v2 models for the unified inbox.

InboxItem represents any project communication — email, meeting transcript,
ACC notification, or internal message — normalized into a common structure
with AI-extracted metadata.
"""
import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


CommType = Literal["decision", "action-item", "FYI", "question", "escalation"]
SourceType = Literal["gmail", "fireflies", "acc", "internal"]


class ActionItem(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    assignee: str
    deadline: Optional[datetime] = None
    priority: Literal["low", "medium", "high"] = "medium"
    description: str


class InboxItem(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    item_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: SourceType
    comm_type: CommType
    urgency: int = Field(ge=1, le=5, default=3)
    summary: str
    raw_text: str
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    sender: str
    sender_email: Optional[str] = None
    subject: Optional[str] = None
    source_url: Optional[str] = None
    action_items: list[ActionItem] = Field(default_factory=list)
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    classified_at: Optional[datetime] = None
    is_read: bool = False

    @field_validator("summary")
    @classmethod
    def summary_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("summary must not be empty")
        return v
