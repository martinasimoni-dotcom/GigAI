from __future__ import annotations

from typing import Any

from gigai.action_gateway import apply_authority, execute_action
from gigai.agents import run_forecasting_agents, run_understanding_agents
from gigai.context import retrieve_context
from gigai.decision import build_decision
from gigai.event_bus import emit
from gigai.feedback import record_feedback
from gigai.ingestion import normalize_bim360_event
from gigai.models import (
    ActionResult,
    ApprovalState,
    DecisionPackage,
    NormalizedEvent,
    PipelineResponse,
)
from gigai.notifications import build_notification_outputs
from gigai.policy import apply_policy
from gigai.storage import (
    append_audit_log,
    find_event_by_idempotency,
    get_action,
    get_action_by_decision,
    get_approval,
    get_approval_by_decision,
    get_decision,
    get_decision_by_event,
    get_event,
    resolve_approval,
    save_action,
    save_approval,
    save_decision,
    update_action,
    update_event_status,
    upsert_event,
)


def ingest_payload(payload: dict[str, Any]) -> tuple[NormalizedEvent, bool]:
    event = normalize_bim360_event(payload)
    idempotency_key = _build_idempotency_key(payload, event)
    existing = find_event_by_idempotency(idempotency_key)
    if existing is not None:
        return NormalizedEvent(**existing["normalized_json"]), True

    upsert_event(
        event_id=event.event_id,
        source=event.source,
        event_type=event.type,
        project_id=event.project_id,
        payload=payload,
        normalized=event.model_dump(mode="json"),
        status="normalized",
        idempotency_key=idempotency_key,
    )
    return event, False


def process_webhook(payload: dict[str, Any]) -> PipelineResponse:
    event, _ = ingest_payload(payload)
    return process_event(event.event_id)


def process_event(event_id: str) -> PipelineResponse:
    event = _load_event(event_id)

    policy = apply_policy(event)
    emit(
        "event.normalized",
        {
            "entity_type": "event",
            "event_id": event.event_id,
            "type": event.type,
            "project_id": event.project_id,
            "priority": policy.priority_score,
            "payload": event.payload,
        },
    )

    update_event_status(event.event_id, "policy_validated")
    emit(
        "policy.validated",
        {
            "entity_type": "event",
            "event_id": event.event_id,
            "classification": policy.classification,
            "priority": policy.priority_score,
            "blockers": policy.blockers,
        },
    )

    context = retrieve_context(event)
    emit(
        "context.retrieved",
        {
            "entity_type": "event",
            "event_id": event.event_id,
            "context_refs": [item.ref for item in context],
        },
    )

    understanding = run_understanding_agents(event, context)
    forecasting = run_forecasting_agents(event, context)
    all_agents = understanding + forecasting
    emit(
        "agents.completed",
        {
            "entity_type": "event",
            "event_id": event.event_id,
            "agents": [agent.agent for agent in all_agents],
        },
    )

    decision = build_decision(event, policy, all_agents)
    save_decision(
        decision_id=decision.decision_id,
        event_id=decision.event_id,
        proposal=decision.model_dump(mode="json"),
        confidence=decision.confidence,
        risk_level=decision.risk_level,
        evidence=decision.evidence,
    )
    emit(
        "decision.generated",
        {
            "entity_type": "decision",
            "decision_id": decision.decision_id,
            "event_id": decision.event_id,
            "proposal": decision.proposal,
            "confidence": decision.confidence,
            "risk_level": decision.risk_level,
            "blockers": decision.constraints,
        },
    )

    action = apply_authority(event, decision, policy)
    emit(
        "authority.checked",
        {
            "entity_type": "decision",
            "decision_id": decision.decision_id,
            "event_id": event.event_id,
            "action_id": action.action_id,
            "mode": action.mode,
            "status": action.status,
            "approval_id": action.approval_id,
        },
    )

    if action.status == "approval_required":
        save_action(
            action_id=action.action_id,
            decision_id=decision.decision_id,
            mode=action.mode,
            status=action.status,
            result=action.model_dump(mode="json"),
        )
        if action.approval_id:
            save_approval(
                approval_id=action.approval_id,
                decision_id=decision.decision_id,
                requested_from="pm_user_1",
                status="pending",
            )
            emit(
                "approval.requested",
                {
                    "entity_type": "approval",
                    "approval_id": action.approval_id,
                    "decision_id": decision.decision_id,
                    "reason": action.reason,
                    "requested_from": "pm_user_1",
                },
            )
        outputs = build_notification_outputs(event, decision, action)
        action.outputs = outputs
        update_action(action.action_id, action.status, action.model_dump(mode="json"))
        update_event_status(event.event_id, "approval_requested")
    else:
        action.outputs = build_notification_outputs(event, decision, action)
        save_action(
            action_id=action.action_id,
            decision_id=decision.decision_id,
            mode=action.mode,
            status=action.status,
            result=action.model_dump(mode="json"),
        )
        emit(
            "action.executed",
            {
                "entity_type": "action",
                "action_id": action.action_id,
                "decision_id": decision.decision_id,
                "event_id": event.event_id,
                "mode": action.mode,
            },
        )
        update_event_status(event.event_id, "completed")

    return PipelineResponse(
        event=event,
        policy=policy,
        context=context,
        agents=all_agents,
        decision=decision,
        action=action,
    )


def replay_event(event_id: str) -> PipelineResponse:
    return process_event(event_id)


def resolve_approval_action(
    approval_id: str,
    *,
    decision: str,
    actor: str,
    note: str | None = None,
) -> ApprovalState:
    approval = get_approval(approval_id)
    if approval is None:
        raise ValueError(f"Approval '{approval_id}' was not found.")
    if approval["status"] != "pending":
        raise ValueError(f"Approval '{approval_id}' is already resolved.")

    stored_decision = get_decision(approval["decision_id"])
    if stored_decision is None:
        raise ValueError(f"Decision '{approval['decision_id']}' was not found.")

    event = _load_event(stored_decision["event_id"])
    decision_package = DecisionPackage(**stored_decision["proposal_json"])
    action_row = get_action_by_decision(decision_package.decision_id)
    if action_row is None:
        raise ValueError(f"No pending action found for decision '{decision_package.decision_id}'.")

    if decision == "approve":
        executed = execute_action(
            event,
            decision_package,
            mode="manual",
            reason="approved_by_user",
            approval_id=approval_id,
        )
        executed.outputs = build_notification_outputs(event, decision_package, executed)
        update_action(action_row["id"], executed.status, executed.model_dump(mode="json"))
        resolve_approval(approval_id, "approved", note)
        record_feedback(
            decision_package.decision_id,
            "accepted",
            approval_id=approval_id,
            metadata={"actor": actor, "note": note or ""},
        )
        emit(
            "action.executed",
            {
                "entity_type": "action",
                "action_id": action_row["id"],
                "decision_id": decision_package.decision_id,
                "event_id": event.event_id,
                "approval_id": approval_id,
                "actor": actor,
            },
            actor=actor,
        )
        update_event_status(event.event_id, "completed")
        return ApprovalState(
            approval_id=approval_id,
            decision_id=decision_package.decision_id,
            status="approved",
            note=note,
            action_status="executed",
        )

    rejected_result = {
        "status": "rejected",
        "reason": "rejected_by_user",
        "approval_id": approval_id,
        "actor": actor,
        "note": note or "",
    }
    update_action(action_row["id"], "rejected", rejected_result)
    resolve_approval(approval_id, "rejected", note)
    record_feedback(
        decision_package.decision_id,
        "rejected",
        approval_id=approval_id,
        metadata={"actor": actor, "note": note or ""},
    )
    emit(
        "approval.rejected",
        {
            "entity_type": "approval",
            "approval_id": approval_id,
            "decision_id": decision_package.decision_id,
            "actor": actor,
            "note": note or "",
        },
        actor=actor,
    )
    update_event_status(event.event_id, "rejected")
    return ApprovalState(
        approval_id=approval_id,
        decision_id=decision_package.decision_id,
        status="rejected",
        note=note,
        action_status="rejected",
    )


def get_cached_pipeline(event_id: str) -> PipelineResponse | None:
    event_row = get_event(event_id)
    if event_row is None:
        return None

    decision_row = get_decision_by_event(event_id)
    action_row = get_action_by_decision(decision_row["id"]) if decision_row else None
    if decision_row is None or action_row is None:
        return None

    event = NormalizedEvent(**event_row["normalized_json"])
    policy = apply_policy(event)
    context = retrieve_context(event)
    decision = DecisionPackage(**decision_row["proposal_json"])
    action_payload = action_row["result_json"]
    action = ActionResult(
        action_id=action_row["id"],
        mode=action_row["mode"],
        status=action_row["status"],
        reason=action_payload.get("reason", ""),
        approval_id=action_payload.get("approval_id"),
        outputs=action_payload.get("outputs", {}),
    )

    return PipelineResponse(
        event=event,
        policy=policy,
        context=context,
        agents=[],
        decision=decision,
        action=action,
    )


def _load_event(event_id: str) -> NormalizedEvent:
    stored = get_event(event_id)
    if stored is None:
        raise ValueError(f"Event '{event_id}' was not found.")
    return NormalizedEvent(**stored["normalized_json"])


def _build_idempotency_key(payload: dict[str, Any], event: NormalizedEvent) -> str:
    external_event_id = (
        str(payload.get("external_event_id") or "").strip()
        or str(payload.get("id") or payload.get("event_id") or event.event_id).strip()
    )
    return f"{event.source}:{external_event_id}"
