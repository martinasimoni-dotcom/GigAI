from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class NormalizedEvent(BaseModel):
    event_id: str
    source: Literal["bim360"] = "bim360"
    type: str
    project_id: str
    artifact_id: str | None = None
    actor_id: str | None = None
    focus_space: str | None = None
    focus_reason: str | None = None
    occurred_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)


class PolicyResult(BaseModel):
    classification: str
    priority_score: int
    security_passed: bool
    blockers: list[str] = Field(default_factory=list)


class RetrievedContext(BaseModel):
    ref: str
    source: str
    summary: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentOutput(BaseModel):
    agent: str
    summary: str
    proposals: list[str] = Field(default_factory=list)
    risk_signals: list[str] = Field(default_factory=list)
    confidence: float
    citations: list[str] = Field(default_factory=list)


class DecisionPackage(BaseModel):
    decision_id: str
    event_id: str
    proposal: str
    alternatives: list[str] = Field(default_factory=list)
    confidence: float
    risk_level: Literal["low", "medium", "high"]
    constraints: list[str] = Field(default_factory=list)
    evidence: list[dict[str, str]] = Field(default_factory=list)


class ActionResult(BaseModel):
    action_id: str
    mode: Literal["auto", "manual"]
    status: str
    reason: str
    approval_id: str | None = None
    outputs: dict[str, Any] = Field(default_factory=dict)


class PipelineResponse(BaseModel):
    event: NormalizedEvent
    policy: PolicyResult
    context: list[RetrievedContext] = Field(default_factory=list)
    agents: list[AgentOutput]
    decision: DecisionPackage
    action: ActionResult


class WebhookAccepted(BaseModel):
    event_id: str
    status: Literal["accepted"]
    idempotent: bool = False


class ApprovalState(BaseModel):
    approval_id: str
    decision_id: str
    status: str
    note: str | None = None
    action_status: str | None = None
