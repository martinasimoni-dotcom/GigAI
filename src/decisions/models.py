"""
Pydantic v2 models for the decision tracker.

A Decision represents a choice or agreement captured from any
communication channel — meetings, emails, proposals, ACC issues.
"""
import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


DecisionSource = Literal["meeting", "email", "proposal", "acc", "internal"]


class Decision(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    decision_id: str = Field(default_factory=lambda: f"DEC-{uuid.uuid4().hex[:8].upper()}")
    inbox_item_id: Optional[str] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    title: str
    description: str
    decided_by: str
    decided_by_email: Optional[str] = None
    source: DecisionSource
    source_url: Optional[str] = None
    context: str = ""
    linked_documents: list[str] = Field(default_factory=list)
    linked_rfis: list[str] = Field(default_factory=list)
    linked_proposals: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    superseded_by: Optional[str] = None

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("title must not be empty")
        return v
