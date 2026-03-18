from __future__ import annotations

from typing import Any

from gigai.storage import append_audit_log, publish_bus_event


def emit(topic: str, payload: dict[str, Any], *, actor: str = "system") -> None:
    publish_bus_event(topic, payload)

    entity_type = payload.get("entity_type") or "pipeline"
    entity_id = str(
        payload.get("event_id")
        or payload.get("decision_id")
        or payload.get("approval_id")
        or payload.get("action_id")
        or topic
    )
    append_audit_log(entity_type, entity_id, topic, actor, payload)
