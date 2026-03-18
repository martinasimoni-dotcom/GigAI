from __future__ import annotations

from typing import Any

from gigai.models import ActionResult, DecisionPackage, NormalizedEvent
from gigai.storage import append_audit_log


def build_notification_outputs(
    event: NormalizedEvent,
    decision: DecisionPackage,
    action: ActionResult,
) -> dict[str, Any]:
    outputs = dict(action.outputs)
    outputs.setdefault("dashboard", "logged")
    outputs.setdefault("email", "team_notified")
    outputs.setdefault(
        "dashboard_entry",
        {
            "event_id": event.event_id,
            "decision_id": decision.decision_id,
            "proposal": decision.proposal,
            "confidence": decision.confidence,
            "risk_level": decision.risk_level,
        },
    )
    outputs.setdefault(
        "email_payload",
        {
            "project_id": event.project_id,
            "subject": f"GigAI decision for {event.type}",
            "summary": decision.proposal,
        },
    )
    append_audit_log(
        "notification",
        action.action_id,
        "notifications.sent",
        "system",
        {
            "event_id": event.event_id,
            "decision_id": decision.decision_id,
            "outputs": outputs,
        },
    )
    return outputs
