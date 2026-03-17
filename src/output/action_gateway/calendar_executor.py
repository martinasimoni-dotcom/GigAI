"""Calendar Executor (OUT-05): creates Google Calendar events via Calendar API v3."""
import asyncio
import logging
import os

import google.auth.transport.requests
import google.oauth2.credentials
import googleapiclient.discovery

from config.settings import settings
from src.output.action_gateway import ActionResult
from src.shared.models.proposals import Action

logger = logging.getLogger(__name__)


async def execute_calendar_action(action: Action) -> ActionResult:
    client_id = os.getenv("GMAIL_CLIENT_ID")
    client_secret = os.getenv("GMAIL_CLIENT_SECRET")
    refresh_token = os.getenv("GMAIL_REFRESH_TOKEN")
    calendar_id = settings.google_calendar_id
    if not client_id or not client_secret or not refresh_token:
        logger.info("Google credentials not configured — skipping calendar action")
        return ActionResult(
            action_type=action.action_type,
            status="skipped",
            message="Calendar event skipped: GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, and GMAIL_REFRESH_TOKEN not set in .env",
        )
    data = action.action_data or {}
    summary = data.get("summary", "GigAI Event")
    description = data.get("description", "")
    start_datetime = data.get("start_datetime", "")
    end_datetime = data.get("end_datetime", "")

    creds = google.oauth2.credentials.Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
    )

    def _create_event() -> str:
        """Blocking Calendar API call — runs in thread pool to avoid blocking the event loop."""
        creds.refresh(google.auth.transport.requests.Request())
        service = googleapiclient.discovery.build("calendar", "v3", credentials=creds)
        event_body = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start_datetime, "timeZone": "UTC"},
            "end": {"dateTime": end_datetime, "timeZone": "UTC"},
        }
        result = service.events().insert(calendarId=calendar_id, body=event_body).execute()
        return result.get("id", "unknown")

    event_id = await asyncio.to_thread(_create_event)
    logger.info("Calendar event created: %s", event_id)
    return ActionResult(
        action_type=action.action_type,
        status="success",
        message=f"Calendar event created: {event_id}",
    )
