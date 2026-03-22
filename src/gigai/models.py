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


class ReviewQueueItem(BaseModel):
    id: str
    structured_intelligence_id: str
    project_id: str
    confidence_score: float
    reason_for_review: str
    entities: list[dict[str, Any]] = Field(default_factory=list)
    actions: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: Literal["pending", "in-review", "approved", "rejected"]
    assigned_to: str | None = None
    reviewer_note: str | None = None
    created_at: str
    updated_at: str
    resolved_at: str | None = None


class ReviewQueueResponse(BaseModel):
    items: list[ReviewQueueItem]
    total: int
    status: str = "ok"


class STTMetric(BaseModel):
    id: int
    transcript_id: str
    provider: str
    model: str
    latency_ms: float
    audio_duration_ms: float | None = None
    transcript_length: int | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class STTHealthStatus(BaseModel):
    status: str
    provider: str
    model: str
    device: str
    compute_type: str
    available: bool
    last_latency_ms: float | None = None
    total_transcribed: int = 0
    error_count: int = 0
    error_rate: float = 0.0
