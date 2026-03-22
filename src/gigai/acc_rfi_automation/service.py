from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from pathlib import Path

from gigai.acc_readonly_sync.auth import AccessTokenProvider
from gigai.google_integrations.config import GoogleIntegrationConfig
from gigai.google_integrations.workspace_client import GoogleWorkspaceClient

from .client import AccRfiClient
from .config import AccRfiAutomationConfig
from .models import NormalizedRfi
from .normalize import normalize_rfis
from .state import RfiAutomationStateStore


@dataclass(slots=True)
class RfiAutomationSummary:
    fetched: int = 0
    open_items: int = 0
    email_sent: int = 0
    calendar_created: int = 0
    skipped: int = 0


class RfiAutomationService:
    def __init__(
        self,
        config: AccRfiAutomationConfig,
        *,
        google_client: GoogleWorkspaceClient | None = None,
        state_store: RfiAutomationStateStore | None = None,
    ) -> None:
        self._config = config
        google_config = GoogleIntegrationConfig.from_env()
        self._google_client = google_client or GoogleWorkspaceClient(google_config)
        self._state_store = state_store or RfiAutomationStateStore(config.db_path)

    def run_once(self) -> RfiAutomationSummary:
        access_token = ""
        if self._config.rfis_input_path is None:
            access_token = AccessTokenProvider(self._config).get()
        client = AccRfiClient(self._config, access_token)
        rfis = normalize_rfis(client.fetch_rfis())

        summary = RfiAutomationSummary(fetched=len(rfis))
        for rfi in rfis:
            if rfi.normalized_status != "open":
                self._log(f"{rfi.id} -> Skipped (Status={rfi.status})")
                summary.skipped += 1
                continue

            summary.open_items += 1
            payload_hash = _compute_payload_hash(rfi)
            state = self._state_store.get(rfi.id)
            if state and state.email_sent and state.calendar_created:
                self._state_store.upsert(
                    rfi_id=rfi.id,
                    payload_hash=payload_hash,
                    email_sent=True,
                    calendar_created=True,
                    email_message_id=state.email_message_id,
                    calendar_event_id=state.calendar_event_id,
                    last_status=rfi.status,
                )
                self._log(f"{rfi.id} -> Skipped (Already Processed)")
                summary.skipped += 1
                continue

            email_result = None
            if state is None or not state.email_sent:
                email_result = self._google_client.send_email(
                    to_emails=rfi.assigned_to,
                    cc_emails=[rfi.created_by] if rfi.created_by else [],
                    subject=f"New RFI Raised - {rfi.id} - {rfi.subject}",
                    body=_build_email_body(rfi),
                )
                if email_result.status == "sent":
                    summary.email_sent += 1
                    self._log(f"{rfi.id} -> Email Sent")
                else:
                    self._log(f"{rfi.id} -> Email {email_result.status}")

            calendar_result = None
            if state is None or not state.calendar_created:
                start_dt, end_dt = _due_window(rfi.due_date)
                calendar_result = self._google_client.create_calendar_event(
                    summary=f"RFI Deadline - {rfi.id}",
                    description=_build_calendar_description(rfi),
                    start_datetime=start_dt,
                    end_datetime=end_dt,
                    attendees=rfi.assigned_to,
                )
                if calendar_result.status == "event_created":
                    summary.calendar_created += 1
                    self._log(f"{rfi.id} -> Calendar Created")
                else:
                    self._log(f"{rfi.id} -> Calendar {calendar_result.status}")

            self._state_store.upsert(
                rfi_id=rfi.id,
                payload_hash=payload_hash,
                email_sent=(state.email_sent if state else False) or (email_result is not None and email_result.status == "sent"),
                calendar_created=(state.calendar_created if state else False) or (calendar_result is not None and calendar_result.status == "event_created"),
                email_message_id=_coerce_message_id(state.email_message_id if state else "", email_result),
                calendar_event_id=_coerce_event_id(state.calendar_event_id if state else "", calendar_result),
                last_status=rfi.status,
            )

        return summary

    def _log(self, message: str) -> None:
        timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        self._config.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self._config.log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"[{timestamp}] {message}\n")


def _build_email_body(rfi: NormalizedRfi) -> str:
    assigned = ", ".join(rfi.assigned_to) if rfi.assigned_to else "Unassigned"
    return (
        f"RFI ID: {rfi.id}\n"
        f"Subject: {rfi.subject}\n"
        f"Question: {rfi.question}\n"
        f"Status: {rfi.status}\n"
        f"Due date: {rfi.due_date or 'N/A'}\n"
        f"Assigned person: {assigned}\n"
    )


def _build_calendar_description(rfi: NormalizedRfi) -> str:
    return f"Subject: {rfi.subject}\n\nQuestion:\n{rfi.question}"


def _due_window(due_date: str | None) -> tuple[datetime, datetime]:
    if due_date:
        try:
            due = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
            if due.tzinfo is None:
                due = due.replace(tzinfo=UTC)
            return due, due + timedelta(hours=1)
        except ValueError:
            try:
                day = datetime.combine(datetime.strptime(due_date, "%Y-%m-%d").date(), time(9, 0), tzinfo=UTC)
                return day, day + timedelta(hours=1)
            except ValueError:
                pass
    start = datetime.now(UTC).replace(hour=9, minute=0, second=0, microsecond=0)
    return start, start + timedelta(hours=1)


def _compute_payload_hash(rfi: NormalizedRfi) -> str:
    payload = {
        "id": rfi.id,
        "subject": rfi.subject,
        "question": rfi.question,
        "status": rfi.status,
        "due_date": rfi.due_date,
        "assigned_to": rfi.assigned_to,
        "created_by": rfi.created_by,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _coerce_message_id(existing: str, result) -> str:
    if result and result.status == "sent":
        return str(result.payload.get("message_id") or "")
    return existing


def _coerce_event_id(existing: str, result) -> str:
    if result and result.status == "event_created":
        return str(result.payload.get("event_id") or "")
    return existing
