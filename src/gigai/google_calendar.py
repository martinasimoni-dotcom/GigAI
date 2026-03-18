from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

from gigai.google_integrations import GoogleIntegrationConfig, GoogleWorkspaceClient
from gigai.models import DecisionPackage, NormalizedEvent


class GoogleCalendarConfig:
    def __init__(self):
        self._inner = GoogleIntegrationConfig.from_env()
        self.enabled = self._inner.enabled
        self.calendar_id = self._inner.calendar_id

    @classmethod
    def from_env(cls) -> "GoogleCalendarConfig":
        return cls()


class GoogleCalendarClient:
    def __init__(self, config: GoogleCalendarConfig):
        self._client = GoogleWorkspaceClient(config._inner)

    def sync_event(self, event: NormalizedEvent, decision: DecisionPackage) -> dict[str, Any]:
        start = datetime.now(timezone.utc)
        result = self._client.create_calendar_event(
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
        )

        if result.status == "event_created":
            return {
                "status": "event_created",
                "calendar_event_id": result.payload.get("event_id"),
                "html_link": result.payload.get("html_link"),
            }

        if result.status in {"disabled", "skipped"}:
            return {
                "status": result.status,
                "reason": result.payload.get("reason"),
            }

        return {
            "status": "error",
            "message": str(result.payload),
        }


async def sync_event(event_data: dict[str, Any]) -> str | None:
    """Backward-compatible async helper used by meeting intelligence task assignment."""
    config = GoogleIntegrationConfig.from_env()
    client = GoogleWorkspaceClient(config)

    def _execute() -> str | None:
        start_raw = (event_data.get("start") or {}).get("dateTime")
        end_raw = (event_data.get("end") or {}).get("dateTime")

        start_dt = _parse_iso(start_raw) if isinstance(start_raw, str) else datetime.now(timezone.utc)
        end_dt = _parse_iso(end_raw) if isinstance(end_raw, str) else (start_dt + timedelta(hours=1))

        attendees = []
        for attendee in event_data.get("attendees", []):
            if isinstance(attendee, dict) and attendee.get("email"):
                attendees.append(str(attendee["email"]))

        result = client.create_calendar_event(
            summary=str(event_data.get("summary") or "GigAI Event"),
            description=str(event_data.get("description") or ""),
            start_datetime=start_dt,
            end_datetime=end_dt,
            attendees=attendees,
        )

        if result.status == "event_created":
            return str(result.payload.get("event_id") or "")
        return None

    return await asyncio.to_thread(_execute)


def _parse_iso(value: str) -> datetime:
    candidate = value.strip()
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    parsed = datetime.fromisoformat(candidate)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
