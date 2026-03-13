"""Action Gateway (OUT-02): parallel executor dispatch with exception isolation."""
import asyncio
import logging

from pydantic import BaseModel

from src.output.action_gateway import ActionResult
import src.output.action_gateway.acc_executor as _acc_mod
import src.output.action_gateway.calendar_executor as _cal_mod
import src.output.action_gateway.document_executor as _doc_mod
import src.output.action_gateway.gmail_executor as _gmail_mod
from src.shared.models.proposals import Proposal

logger = logging.getLogger(__name__)

# Module references — allows tests to patch individual executor functions
EXECUTOR_MAP = {
    "email": lambda a: _gmail_mod.execute_gmail_action(a),
    "task": lambda a: _acc_mod.execute_acc_action(a),
    "calendar": lambda a: _cal_mod.execute_calendar_action(a),
    "drawing": lambda a: _doc_mod.execute_document_action(a),
}


class ExecutionResult(BaseModel):
    proposal_id: str
    results: list[ActionResult]
    success_count: int
    failure_count: int


async def execute_actions(proposal: Proposal) -> ExecutionResult:
    """Run all proposal actions in parallel; isolate individual failures."""
    action_executor_pairs = []
    for action in proposal.actions:
        executor = EXECUTOR_MAP.get(action.action_type)
        action_executor_pairs.append((action, executor))

    coros = []
    for action, executor in action_executor_pairs:
        if executor:
            coros.append(executor(action))
        else:
            async def _unknown(a=action):
                return ActionResult(
                    action_type=a.action_type,
                    status="failed",
                    message="Execution failed",
                    error=f"Unknown action_type: {a.action_type}",
                )
            coros.append(_unknown())

    raw_results = await asyncio.gather(*coros, return_exceptions=True)

    results = []
    for (action, _), outcome in zip(action_executor_pairs, raw_results):
        if isinstance(outcome, Exception):
            results.append(ActionResult(
                action_type=action.action_type,
                status="failed",
                message="Execution failed",
                error=str(outcome),
            ))
        else:
            results.append(outcome)

    success_count = sum(1 for r in results if r.status == "success")
    failure_count = len(results) - success_count
    logger.info(
        "execute_actions: proposal_id=%s success=%d failed=%d",
        proposal.proposal_id, success_count, failure_count,
    )
    return ExecutionResult(
        proposal_id=proposal.proposal_id,
        results=results,
        success_count=success_count,
        failure_count=failure_count,
    )
