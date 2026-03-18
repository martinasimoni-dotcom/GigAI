from __future__ import annotations

from typing import Any

from gigai.event_bus import emit
from gigai.storage import add_feedback


def record_feedback(
    decision_id: str,
    outcome: str,
    *,
    approval_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    payload = {
        "decision_id": decision_id,
        "approval_id": approval_id,
        "outcome": outcome,
        "metadata": metadata or {},
    }
    add_feedback(decision_id, outcome, payload, approval_id=approval_id)
    emit(
        "feedback.recorded",
        {
            "entity_type": "decision",
            "decision_id": decision_id,
            "approval_id": approval_id,
            "outcome": outcome,
            "metadata": metadata or {},
        },
    )
