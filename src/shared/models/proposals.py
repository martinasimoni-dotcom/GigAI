"""
Pydantic v2 models for signals, actions, and proposals.
FOUND-07
"""
from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class Signal(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    signal_type: str
    priority: int = 1
    payload: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Action(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    action_id: str = Field(default_factory=lambda: str(uuid4()))
    action_type: Literal["email", "task", "calendar", "drawing"]
    action_data: dict
    status: Literal["pending", "executed", "failed"] = "pending"
    executed_at: Optional[datetime] = None


class Proposal(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    proposal_id: str = Field(default_factory=lambda: str(uuid4()))
    event_id: str
    alert: dict
    actions: list[Action] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0)
    recommendation: Literal["accept", "review", "reject"]
    status: Literal["pending", "accepted", "rejected"] = "pending"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
