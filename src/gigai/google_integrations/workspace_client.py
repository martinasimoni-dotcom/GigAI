from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from typing import Any

from gigai.google_integrations.config import GoogleIntegrationConfig

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
except ModuleNotFoundError:
    Request = None
    Credentials = None
    build = None


@dataclass(frozen=True)
class GoogleActionResult:
    status: str
    payload: dict[str, Any]


class GoogleWorkspaceClient:
    def __init__(self, config: GoogleIntegrationConfig):
        self._config = config
        self._gmail_service = None
        self._calendar_service = None

    def send_email(self, to_emails: list[str], subject: str, body: str) -> GoogleActionResult:
        if not self._config.enabled:
            return GoogleActionResult("disabled", {})

        if not to_emails:
            return GoogleActionResult("skipped", {"reason": "no_recipients"})

        if not self._config.has_credentials:
            return GoogleActionResult("skipped", {"reason": "missing_credentials"})

        service = self._get_gmail_service()

        message = MIMEText(body, "plain")
        message["To"] = ", ".join(to_emails)
        message["Subject"] = subject

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        sent = service.users().messages().send(
            userId=self._config.sender_user_id,
            body={"raw": raw},
        ).execute()

        return GoogleActionResult(
            "sent",
            {
                "message_id": str(sent.get("id") or ""),
                "thread_id": str(sent.get("threadId") or ""),
                "to": to_emails,
            },
        )

    def create_calendar_event(
        self,
        summary: str,
        description: str,
        start_datetime: datetime | None = None,
        end_datetime: datetime | None = None,
        attendees: list[str] | None = None,
    ) -> GoogleActionResult:
        if not self._config.enabled:
            return GoogleActionResult("disabled", {})

        if not self._config.has_credentials:
            return GoogleActionResult("skipped", {"reason": "missing_credentials"})

        service = self._get_calendar_service()
        start = start_datetime or datetime.now(timezone.utc)
        end = end_datetime or (start + timedelta(hours=1))

        event_body: dict[str, Any] = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end.isoformat(), "timeZone": "UTC"},
        }

        if attendees:
            event_body["attendees"] = [{"email": email} for email in attendees]

        created = service.events().insert(
            calendarId=self._config.calendar_id,
            body=event_body,
        ).execute()

        return GoogleActionResult(
            "event_created",
            {
                "event_id": str(created.get("id") or ""),
                "html_link": str(created.get("htmlLink") or ""),
            },
        )

    def _get_gmail_service(self):
        if self._gmail_service is None:
            self._gmail_service = build("gmail", "v1", credentials=self._build_credentials())
        return self._gmail_service

    def _get_calendar_service(self):
        if self._calendar_service is None:
            self._calendar_service = build("calendar", "v3", credentials=self._build_credentials())
        return self._calendar_service

    def _build_credentials(self):
        if not all([Request, Credentials, build]):
            raise ModuleNotFoundError(
                "Google API dependencies missing. Install: google-auth google-api-python-client google-auth-httplib2"
            )

        credentials = Credentials(
            token=None,
            refresh_token=self._config.gmail_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self._config.gmail_client_id,
            client_secret=self._config.gmail_client_secret,
        )
        credentials.refresh(Request())
        return credentials
