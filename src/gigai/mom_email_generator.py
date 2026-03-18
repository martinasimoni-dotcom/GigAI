"""
Revit Location Marked -> Minutes of Meeting (MOM) email generator.

Builds a formal MOM email from verified event payload data while avoiding
assumptions for missing fields.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


NOT_SPECIFIED = "Not specified"


def _to_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _text(value: Any) -> str:
    if value is None:
        return NOT_SPECIFIED
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed if trimmed else NOT_SPECIFIED
    rendered = str(value).strip()
    return rendered if rendered else NOT_SPECIFIED


def _join(values: list[Any]) -> str:
    cleaned = [_text(v) for v in values if _text(v) != NOT_SPECIFIED]
    return ", ".join(cleaned) if cleaned else NOT_SPECIFIED


def _pick(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = data.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def _extract_key_lines(transcript: str, prefixes: tuple[str, ...]) -> list[str]:
    if not transcript:
        return []
    items: list[str] = []
    for raw_line in transcript.splitlines():
        line = raw_line.strip()
        lowered = line.lower()
        if any(lowered.startswith(prefix) for prefix in prefixes):
            parts = line.split(":", 1)
            if len(parts) == 2:
                candidate = parts[1].strip()
                if candidate:
                    items.append(candidate)
            elif line:
                items.append(line)
    return items


def _normalize_action_items(action_items: list[dict[str, Any]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in action_items:
        normalized.append(
            {
                "task": _text(_pick(item, "task", "description", "action")),
                "responsible": _text(_pick(item, "responsible", "owner", "assigned_to", "person")),
                "deadline": _text(_pick(item, "deadline", "due_date", "due", "target_date")),
            }
        )
    return normalized


def generate_meeting_completed_mom(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Generate a formal MOM email payload for a verified "Revit Location Marked" event.
    """
    event_type = _text(_pick(payload, "event_type", "eventType", "type"))
    event_confirmed = event_type.lower() == "revit location marked"
    event_status = "Meeting Completed" if event_confirmed else f"Unrecognized event ({event_type})"

    project_data = payload.get("project") if isinstance(payload.get("project"), dict) else {}
    meeting_data = payload.get("meeting") if isinstance(payload.get("meeting"), dict) else {}
    bim_data = payload.get("bim") if isinstance(payload.get("bim"), dict) else {}
    detected_changes = payload.get("detected_changes") if isinstance(payload.get("detected_changes"), dict) else {}

    project_name = _text(_pick(project_data, "name", "project_name", "title") or _pick(payload, "project_name"))
    team_name = _text(
        _pick(project_data, "assigned_team", "team_name", "architect_team")
        or _pick(meeting_data, "team_name", "architect_team")
    )

    marked_location = _text(
        _pick(bim_data, "marked_location", "location", "room", "area", "zone")
        or _pick(payload, "marked_location", "location")
    )
    element_ids = _to_list(_pick(bim_data, "element_ids", "elements", "revit_element_ids"))
    element_categories = _to_list(_pick(bim_data, "element_categories", "categories"))
    sheet_numbers = _to_list(_pick(bim_data, "sheet_numbers", "sheets", "views"))
    model_revision = _text(
        _pick(bim_data, "model_version", "revision", "model_revision")
        or _pick(project_data, "revision", "model_version")
    )

    meeting_date_time = _text(
        _pick(meeting_data, "date_time", "timestamp", "date", "meeting_time")
        or _pick(payload, "timestamp", "date_time")
    )
    meeting_date_for_subject = (
        datetime.now().strftime("%d %b %Y") if meeting_date_time == NOT_SPECIFIED else meeting_date_time
    )
    duration = _text(_pick(meeting_data, "duration", "duration_minutes"))
    participants = _to_list(_pick(meeting_data, "participants", "attendees"))
    participant_text = _join(participants)

    transcript = _text(_pick(meeting_data, "transcript", "transcript_text"))
    transcript_value = "" if transcript == NOT_SPECIFIED else transcript

    key_discussions = _to_list(
        _pick(detected_changes, "key_discussions", "discussions", "topics")
    )
    if not key_discussions and transcript_value:
        key_discussions = _extract_key_lines(transcript_value, ("discussion:", "topic:", "discussed:"))
    if not key_discussions:
        descriptions = []
        for change in _to_list(_pick(detected_changes, "design_modifications", "changes")):
            if isinstance(change, dict):
                desc = _pick(change, "description", "change", "summary")
                if desc:
                    descriptions.append(desc)
        key_discussions = descriptions

    decisions = _to_list(_pick(detected_changes, "decisions", "decisions_taken"))
    if not decisions and transcript_value:
        decisions = _extract_key_lines(transcript_value, ("decision:", "decided:", "approved:"))

    issues = _to_list(_pick(detected_changes, "issues", "conflicts", "coordination_issues", "observations"))
    if not issues and transcript_value:
        issues = _extract_key_lines(transcript_value, ("issue:", "risk:", "clash:", "observation:"))

    raw_actions = _to_list(_pick(detected_changes, "action_items", "actions", "tasks"))
    action_items = _normalize_action_items(
        [item for item in raw_actions if isinstance(item, dict)]
    )

    task_refs = _to_list(_pick(project_data, "task_references", "tasks", "task_refs"))
    revision_refs = _to_list(_pick(project_data, "related_revisions", "issues", "related_issues"))
    attachments = _to_list(_pick(payload, "attachments", "files", "documents"))

    def bullet_section(values: list[Any]) -> list[str]:
        if not values:
            return [f"- {NOT_SPECIFIED}"]
        rendered = []
        for value in values:
            if isinstance(value, dict):
                rendered.append(f"- {_text(value.get('name') or value.get('title') or value.get('id'))}")
            else:
                rendered.append(f"- {_text(value)}")
        return rendered if rendered else [f"- {NOT_SPECIFIED}"]

    action_lines: list[str] = []
    if action_items:
        for item in action_items:
            action_lines.extend(
                [
                    f"- Task: {item['task']}",
                    f"  Responsible: {item['responsible']}",
                    f"  Deadline: {item['deadline']}",
                ]
            )
    else:
        action_lines = [
            f"- Task: {NOT_SPECIFIED}",
            f"  Responsible: {NOT_SPECIFIED}",
            f"  Deadline: {NOT_SPECIFIED}",
        ]

    subject = f"{project_name} – Minutes of Meeting (Location: {marked_location}) – {meeting_date_for_subject}"

    body_lines = [
        f"Dear {team_name},",
        "",
        f"This is to confirm that the meeting conducted on {meeting_date_time} at {marked_location} has been completed successfully.",
        "",
        "Please find below the Minutes of Meeting:",
        "",
        "----------------------------------------",
        "1. Meeting Details",
        "----------------------------------------",
        f"- Event Confirmation: {event_status}",
        f"- Project: {project_name}",
        f"- Location (Revit Mark): {marked_location}",
        f"- Date & Time: {meeting_date_time}",
        f"- Duration: {duration}",
        f"- Participants: {participant_text}",
        "",
        "----------------------------------------",
        "2. Key Discussions",
        "----------------------------------------",
    ]
    body_lines.extend(bullet_section(key_discussions))
    body_lines.extend(
        [
            "",
            "----------------------------------------",
            "3. Decisions Taken",
            "----------------------------------------",
        ]
    )
    body_lines.extend(bullet_section(decisions))
    body_lines.extend(
        [
            "",
            "----------------------------------------",
            "4. Issues / Observations",
            "----------------------------------------",
        ]
    )
    body_lines.extend(bullet_section(issues))
    body_lines.extend(
        [
            "",
            "----------------------------------------",
            "5. Action Items",
            "----------------------------------------",
        ]
    )
    body_lines.extend(action_lines)
    body_lines.extend(
        [
            "",
            "----------------------------------------",
            "6. BIM / Drawing References",
            "----------------------------------------",
            f"- Marked Location: {marked_location}",
            f"- Element IDs: {_join(element_ids)}",
            f"- Element Categories: {_join(element_categories)}",
            f"- Sheet Numbers / Views: {_join(sheet_numbers)}",
            f"- Model Version / Revision: {model_revision}",
            f"- Task References: {_join(task_refs)}",
            f"- Related Revisions / Issues: {_join(revision_refs)}",
            "",
            "----------------------------------------",
            "7. Attachments",
            "----------------------------------------",
        ]
    )
    body_lines.extend(bullet_section(attachments))
    body_lines.extend(
        [
            "",
            "Kindly review and proceed with the necessary actions.",
            "",
            "Please confirm once updates are implemented or if any clarification is required.",
            "",
            "Best regards,",
            "GigAI Coordination System",
            "(On behalf of Project Management Team)",
        ]
    )

    email_body = "\n".join(body_lines)

    structured = {
        "event_confirmation": event_status,
        "meeting_details": {
            "project": project_name,
            "location_revit_mark": marked_location,
            "date_time": meeting_date_time,
            "duration": duration,
            "participants": participants if participants else [NOT_SPECIFIED],
        },
        "key_discussions": [
            _text(item) for item in key_discussions
        ]
        or [NOT_SPECIFIED],
        "decisions_taken": [_text(item) for item in decisions] or [NOT_SPECIFIED],
        "issues_observations": [_text(item) for item in issues] or [NOT_SPECIFIED],
        "action_items": action_items
        or [{"task": NOT_SPECIFIED, "responsible": NOT_SPECIFIED, "deadline": NOT_SPECIFIED}],
        "bim_drawing_references": {
            "element_ids": [_text(item) for item in element_ids] or [NOT_SPECIFIED],
            "element_categories": [_text(item) for item in element_categories] or [NOT_SPECIFIED],
            "sheet_numbers": [_text(item) for item in sheet_numbers] or [NOT_SPECIFIED],
            "model_revision": model_revision,
        },
        "attachments": [_text(item) for item in attachments] or [NOT_SPECIFIED],
    }

    return {
        "event_confirmation": event_status,
        "subject": subject,
        "email_body": email_body,
        "mom": structured,
    }
