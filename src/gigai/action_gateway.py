from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from gigai.bim360_client import Bim360Client, Bim360Config, Bim360Error
from gigai.google_integrations import GoogleIntegrationConfig, GoogleWorkspaceClient
from gigai.models import ActionResult, DecisionPackage, NormalizedEvent, PolicyResult


def apply_authority(
    event: NormalizedEvent,
    decision: DecisionPackage,
    policy: PolicyResult,
    confidence_threshold: float = 0.80,
) -> ActionResult:
    auto_allowed = (
        decision.confidence >= confidence_threshold
        and decision.risk_level in {"low", "medium"}
        and not policy.blockers
    )

    if decision.proposal in {"create_issue_note", "log_meeting_note"}:
        auto_allowed = auto_allowed and decision.confidence >= 0.85

    if auto_allowed:
        return execute_action(
            event,
            decision,
            mode="auto",
            reason="confidence_high_no_blockers",
        )

    return ActionResult(
        action_id=f"act_{uuid4().hex[:10]}",
        mode="manual",
        status="approval_required",
        reason="authority_boundary_triggered",
        approval_id=f"apr_{uuid4().hex[:10]}",
        outputs={
            "dashboard": "approval_requested",
            "bim360": "status_pending_approval",
            "email": "pm_approval_requested",
        },
    )


def execute_action(
    event: NormalizedEvent,
    decision: DecisionPackage,
    *,
    mode: str,
    reason: str,
    approval_id: str | None = None,
) -> ActionResult:
    outputs = {
        "dashboard": "logged",
        "bim360": "comment_written",
        "email": "team_notified",
    }
    if decision.proposal == "create_issue_note":
        outputs["bim360"] = "issue_created"
    elif decision.proposal == "log_meeting_note":
        outputs["dashboard"] = "note_logged"

    outputs = _apply_bim360_writeback(event, decision, outputs)
    outputs = _apply_google_email_notify(event, decision, outputs)
    outputs = _apply_google_calendar_sync(event, decision, outputs)
    return ActionResult(
        action_id=f"act_{uuid4().hex[:10]}",
        mode="auto" if mode == "auto" else "manual",
        status="executed",
        reason=reason,
        approval_id=approval_id,
        outputs=outputs,
    )


def _apply_bim360_writeback(
    event: NormalizedEvent,
    decision: DecisionPackage,
    outputs: dict[str, str],
) -> dict[str, str]:
    config = Bim360Config.from_env()
    client = Bim360Client(config)

    try:
        result = client.writeback(event, decision)
    except Bim360Error as ex:
        outputs["bim360"] = "writeback_failed"
        outputs["bim360_error"] = str(ex)
        return outputs

    status = str(result.get("status") or "").strip()
    if status in {"comment_written", "issue_created"}:
        outputs["bim360"] = status
    elif status:
        outputs["bim360_writeback"] = status

    for key, value in result.items():
        if key == "status":
            continue
        outputs[f"bim360_{key}"] = str(value)

    return outputs


def _apply_google_calendar_sync(
    event: NormalizedEvent,
    decision: DecisionPackage,
    outputs: dict[str, str],
) -> dict[str, str]:
    config = GoogleIntegrationConfig.from_env()
    if not config.enabled:
        return outputs

    client = GoogleWorkspaceClient(config)
    start = datetime.now(timezone.utc)
    try:
        result = client.create_calendar_event(
            summary=f"GigAI: {decision.proposal}",
            description=(
                f"Project: {event.project_id}\n"
                f"Decision ID: {decision.decision_id}\n"
                f"Confidence: {decision.confidence}\n"
                f"Risk: {decision.risk_level}\n"
                f"Event: {event.type}"
            ),
            start_datetime=start,
            end_datetime=start + timedelta(hours=1),
            attendees=_resolve_notification_recipients(event, config.default_recipients),
        )
    except ModuleNotFoundError:
        outputs["google_calendar"] = "skipped"
        outputs["google_calendar_reason"] = "missing_google_dependencies"
        return outputs
    except Exception as ex:
        outputs["google_calendar"] = "sync_failed"
        outputs["google_calendar_error"] = str(ex)
        return outputs

    status = result.status
    if status == "event_created":
        outputs["google_calendar"] = "event_created"
        outputs["google_calendar_link"] = str(result.payload.get("html_link") or "")
        outputs["google_calendar_event_id"] = str(result.payload.get("event_id") or "")
    elif status in {"skipped", "disabled"}:
        outputs["google_calendar"] = status
        reason = str(result.payload.get("reason") or "")
        if reason:
            outputs["google_calendar_reason"] = reason
    else:
        outputs["google_calendar"] = "sync_failed"
        outputs["google_calendar_error"] = str(result.payload or "Unknown error")

    return outputs


def _apply_google_email_notify(
    event: NormalizedEvent,
    decision: DecisionPackage,
    outputs: dict[str, str],
) -> dict[str, str]:
    config = GoogleIntegrationConfig.from_env()
    recipients = _resolve_notification_recipients(event, config.default_recipients)

    client = GoogleWorkspaceClient(config)
    try:
        result = client.send_email(
            to_emails=recipients,
            subject=f"GigAI decision for {event.type}",
            body=(
                f"Project: {event.project_id}\n"
                f"Decision: {decision.proposal}\n"
                f"Confidence: {decision.confidence}\n"
                f"Risk: {decision.risk_level}\n"
                f"Decision ID: {decision.decision_id}\n"
                f"Event ID: {event.event_id}"
            ),
        )
    except ModuleNotFoundError:
        outputs["google_email"] = "skipped"
        outputs["google_email_reason"] = "missing_google_dependencies"
        return outputs
    except Exception as ex:
        outputs["email"] = "failed"
        outputs["google_email"] = "failed"
        outputs["google_email_error"] = str(ex)
        return outputs

    if result.status == "sent":
        outputs["email"] = "sent_via_google"
        outputs["google_email"] = "sent"
        outputs["google_email_message_id"] = str(result.payload.get("message_id") or "")
    elif result.status in {"skipped", "disabled"}:
        outputs["google_email"] = result.status
        reason = str(result.payload.get("reason") or "")
        if reason:
            outputs["google_email_reason"] = reason
    else:
        outputs["email"] = "failed"
        outputs["google_email"] = "failed"
        outputs["google_email_error"] = str(result.payload or "Unknown error")

    return outputs


def _resolve_notification_recipients(
    event: NormalizedEvent,
    default_recipients: tuple[str, ...],
) -> list[str]:
    recipients: list[str] = []
    payload = event.payload if isinstance(event.payload, dict) else {}

    for key in ("notification_emails", "team_emails", "emails", "recipients"):
        value = payload.get(key)
        if isinstance(value, list):
            recipients.extend(str(item).strip() for item in value if str(item).strip())

    participants = payload.get("participants")
    if isinstance(participants, list):
        for participant in participants:
            if isinstance(participant, dict):
                email = str(participant.get("email") or "").strip()
                if email:
                    recipients.append(email)

    if not recipients:
        recipients.extend(default_recipients)

    unique: list[str] = []
    seen = set()
    for email in recipients:
        lowered = email.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        unique.append(email)
    return unique
