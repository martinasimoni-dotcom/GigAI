"""Action Gateway package — ActionResult and ExecutionResult models."""
from pydantic import BaseModel
from typing import Literal


class ActionResult(BaseModel):
    action_type: str
    status: Literal["success", "failed", "skipped"]
    message: str
    error: str | None = None


class ExecutionResult(BaseModel):
    proposal_id: str
    results: list[ActionResult]
    success_count: int
    failure_count: int
