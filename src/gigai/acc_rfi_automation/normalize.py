from __future__ import annotations

from typing import Any, Iterable

from .models import NormalizedRfi


def normalize_rfis(records: Iterable[dict[str, Any]]) -> list[NormalizedRfi]:
    normalized: list[NormalizedRfi] = []
    for record in records:
        item = _normalize_one(record)
        if item is not None:
            normalized.append(item)
    return normalized


def _normalize_one(record: dict[str, Any]) -> NormalizedRfi | None:
    identifier = _text(_pick(record, "id", "rfiId", "identifier"))
    if not identifier:
        return None

    assigned = _coerce_people(record.get("assignedTo"))
    created_by = _coerce_person(
        _pick(record, "createdBy", "creator", "submitter", "owner")
    )

    return NormalizedRfi(
        id=identifier,
        subject=_text(_pick(record, "subject", "title")) or f"RFI-{identifier}",
        question=_text(_pick(record, "question", "description", "text")) or "",
        status=_text(_pick(record, "status", "workflowStatus", "currentStatus")) or "unknown",
        due_date=_text(_pick(record, "dueDate", "responseDueDate", "due_date")),
        assigned_to=assigned,
        created_by=created_by,
        raw_payload=record,
    )


def _pick(payload: dict[str, Any], *paths: str) -> Any:
    for path in paths:
        value = _pick_path(payload, path)
        if value is not None:
            return value
    return None


def _pick_path(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for segment in path.split("."):
        if not isinstance(current, dict) or segment not in current:
            return None
        current = current[segment]
    return current


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_person(value: Any) -> str | None:
    if isinstance(value, dict):
        return _text(value.get("name") or value.get("displayName") or value.get("email"))
    return _text(value)


def _coerce_people(value: Any) -> list[str]:
    if isinstance(value, list):
        names = [_coerce_person(item) for item in value]
        return [name for name in names if name]
    one = _coerce_person(value)
    return [one] if one else []

