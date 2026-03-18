from __future__ import annotations

from typing import Any

from gigai.models import NormalizedEvent, RetrievedContext
from gigai.storage import list_project_history


def retrieve_context(event: NormalizedEvent, limit: int = 6) -> list[RetrievedContext]:
    context_items: list[RetrievedContext] = []

    if event.focus_space:
        context_items.append(
            RetrievedContext(
                ref=f"space:{event.focus_space}",
                source="focus_space",
                summary=f"Current decision scope is limited to '{event.focus_space}'.",
                metadata={"focus_reason": event.focus_reason or "unknown"},
            )
        )

    if event.artifact_id:
        context_items.append(
            RetrievedContext(
                ref=f"artifact:{event.artifact_id}",
                source="artifact",
                summary=f"Working against artifact '{event.artifact_id}'.",
                metadata={"artifact_id": event.artifact_id},
            )
        )

    for history in list_project_history(event.project_id, artifact_id=event.artifact_id, limit=limit):
        normalized = history["normalized"]
        summary_bits = [history["type"], history["status"]]
        if normalized.get("focus_space"):
            summary_bits.append(f"focus={normalized['focus_space']}")
        context_items.append(
            RetrievedContext(
                ref=f"history:{history['event_id']}",
                source="historical_event",
                summary=" | ".join(summary_bits),
                metadata={
                    "event_id": history["event_id"],
                    "updated_at": history["updated_at"],
                },
            )
        )

    payload_hints = _payload_context_hints(event.payload)
    context_items.extend(payload_hints)
    return context_items[:limit]


def _payload_context_hints(payload: dict[str, Any]) -> list[RetrievedContext]:
    hints: list[RetrievedContext] = []
    for field in ("building_element", "discipline", "issue", "status"):
        value = payload.get(field)
        if not value:
            continue
        hints.append(
            RetrievedContext(
                ref=f"payload:{field}",
                source="payload",
                summary=f"{field}={value}",
                metadata={field: value},
            )
        )
    return hints
