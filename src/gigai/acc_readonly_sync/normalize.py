from __future__ import annotations

from typing import Any, Iterable

from .models import NormalizedAccRecord, NormalizedLocation


def normalize_issue_records(records: Iterable[dict[str, Any]]) -> tuple[list[NormalizedAccRecord], int]:
    return _normalize_records(records, record_type="issue")


def normalize_rfi_records(records: Iterable[dict[str, Any]]) -> tuple[list[NormalizedAccRecord], int]:
    return _normalize_records(records, record_type="rfi")


def _normalize_records(
    records: Iterable[dict[str, Any]],
    *,
    record_type: str,
) -> tuple[list[NormalizedAccRecord], int]:
    normalized: list[NormalizedAccRecord] = []
    ignored = 0
    for record in records:
        item = _normalize_one(record, record_type=record_type)
        if item is None:
            ignored += 1
            continue
        normalized.append(item)
    return normalized, ignored


def _normalize_one(record: dict[str, Any], *, record_type: str) -> NormalizedAccRecord | None:
    identifier = _text(_pick(record, "id", "issueId", "rfiId", "identifier"))
    if not identifier:
        return None

    location_payload = (
        _pick(record, "location")
        or _pick(record, "pushpin")
        or _pick(record, "locationDetails")
        or _pick(record, "linkedLocation")
        or {}
    )
    if not isinstance(location_payload, dict):
        location_payload = {}

    location = NormalizedLocation(
        x=_number(_pick(location_payload, "x", "position.x", "coordinates.x", "point.x")),
        y=_number(_pick(location_payload, "y", "position.y", "coordinates.y", "point.y")),
        z=_number(_pick(location_payload, "z", "position.z", "coordinates.z", "point.z")),
        elementId=_text(
            _pick(
                location_payload,
                "elementId",
                "element_id",
                "externalId",
                "external_id",
                "viewerNodeId",
                "targetId",
                "entityId",
            )
        ),
        viewId=_text(
            _pick(location_payload, "viewId", "view_id", "sheetId", "sheet_id", "documentId", "target_urn")
        ),
        modelUrn=_text(_pick(location_payload, "modelUrn", "model_urn", "urn")),
        sourceUrl=_text(_pick(record, "url", "webUrl", "web_url")),
    )

    if not location.has_mapping_data():
        nested_candidates = [
            _text(_pick(record, "locationDescription")),
            _text(_pick(record, "location_name")),
            _text(_pick(record, "locationNotes")),
        ]
        if not any(candidate for candidate in nested_candidates):
            return None

    title = _text(_pick(record, "title", "subject")) or f"{record_type.upper()}-{identifier}"
    description = _text(_pick(record, "description", "issueDescription", "question", "text")) or ""
    status = _text(_pick(record, "status", "workflowStatus", "currentStatus")) or "unknown"
    created_by = _coerce_creator(record)
    assigned_user = _coerce_assignee(record)
    due_date = _text(_pick(record, "dueDate", "due_date", "responseDueDate"))
    updated_at = _text(_pick(record, "updatedAt", "updated_at", "lastModifiedTime"))

    return NormalizedAccRecord(
        id=identifier,
        type=record_type,
        title=title,
        description=description,
        status=status,
        createdBy=created_by,
        assignedUser=assigned_user,
        dueDate=due_date,
        location=location,
        sourceUpdatedAt=updated_at,
        sourcePayload=record,
    )


def _coerce_assignee(record: dict[str, Any]) -> str | None:
    candidate = _pick(record, "assignedTo.name", "assignedTo.displayName", "assigned_user", "assignee")
    if candidate is not None:
        return _text(candidate)

    assigned_to = _pick(record, "assignedTo")
    if isinstance(assigned_to, list):
        names = [_text(item.get("name") or item.get("displayName")) for item in assigned_to if isinstance(item, dict)]
        names = [name for name in names if name]
        if names:
            return ", ".join(names)
    return None


def _coerce_creator(record: dict[str, Any]) -> str | None:
    candidate = _pick(
        record,
        "createdBy.name",
        "createdBy.displayName",
        "created_by",
        "creator",
        "owner.name",
        "owner.displayName",
        "submitter.name",
        "submitter.displayName",
    )
    if candidate is not None:
        return _text(candidate)
    return None


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


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
