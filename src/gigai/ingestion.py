from datetime import UTC, datetime
import re
from uuid import uuid4

from gigai.models import NormalizedEvent


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _extract_room_roots(value: str) -> set[str]:
    roots: set[str] = set()
    for token in re.findall(r"\b[a-z]?[0-9]{2,4}[a-z]?\b", _normalize_text(value)):
        digits = "".join(ch for ch in token if ch.isdigit())
        if len(digits) >= 2:
            roots.add(digits)
    return roots


def detect_focus_space(payload: dict) -> tuple[str | None, str | None]:
    llm_space = payload.get("llm_space_name")
    llm_reason = payload.get("llm_reason")
    if isinstance(llm_space, str) and llm_space.strip():
        if isinstance(llm_reason, str) and llm_reason.strip():
            return llm_space.strip(), llm_reason.strip()
        return llm_space.strip(), "llm_space_match"

    explicit_space = payload.get("space_name") or payload.get("space")
    if isinstance(explicit_space, str) and explicit_space.strip():
        return explicit_space.strip(), "explicit_space_field"

    utterance = payload.get("meeting_utterance") or payload.get("transcript")
    spaces = payload.get("available_spaces") or payload.get("spaces")
    if not isinstance(utterance, str) or not utterance.strip() or not isinstance(spaces, list):
        return None, None

    normalized_utterance = f" {_normalize_text(utterance)} "
    for space in spaces:
        if not isinstance(space, str) or not space.strip():
            continue
        normalized_space = _normalize_text(space)
        if normalized_space and f" {normalized_space} " in normalized_utterance:
            return space.strip(), "meeting_utterance_match"

    # Fallback: if transcript is imperfect but still includes a room/unit number
    # (e.g., 404), map that number to a unique available space.
    utterance_roots = _extract_room_roots(utterance)
    if utterance_roots:
        best_space: str | None = None
        best_overlap = 0
        tie = False
        for space in spaces:
            if not isinstance(space, str) or not space.strip():
                continue
            overlap = len(_extract_room_roots(space) & utterance_roots)
            if overlap > best_overlap:
                best_overlap = overlap
                best_space = space.strip()
                tie = False
            elif overlap > 0 and overlap == best_overlap:
                tie = True

        if best_space and best_overlap > 0 and not tie:
            return best_space, "meeting_room_number_match"

    return None, None


def normalize_bim360_event(payload: dict) -> NormalizedEvent:
    event_type = payload.get("eventType") or payload.get("type") or "issue.updated"
    focus_space, focus_reason = detect_focus_space(payload)

    return NormalizedEvent(
        event_id=payload.get("event_id") or payload.get("id") or f"evt_{uuid4().hex[:10]}",
        type=event_type,
        project_id=payload.get("projectId") or payload.get("project_id") or "",
        artifact_id=payload.get("artifactId") or payload.get("artifact_id"),
        actor_id=(payload.get("actor") or {}).get("id") if isinstance(payload.get("actor"), dict) else None,
        focus_space=focus_space,
        focus_reason=focus_reason,
        occurred_at=datetime.now(UTC),
        payload=payload,
    )
