"""Calendar Executor (OUT-05): creates Google Calendar events via Calendar API v3."""
import logging
import os

import google.auth.transport.requests
import google.oauth2.credentials
import googleapiclient.discovery

from src.output.action_gateway import ActionResult
from src.shared.models.proposals import Action

logger = logging.getLogger(__name__)


async def execute_calendar_action(action: Action) -> ActionResult:
    client_id = os.getenv("GMAIL_CLIENT_ID")
    client_secret = os.getenv("GMAIL_CLIENT_SECRET")
    refresh_token = os.getenv("GMAIL_REFRESH_TOKEN")
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
    if not client_id or not client_secret or not refresh_token:
        raise RuntimeError(
            "GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, and GMAIL_REFRESH_TOKEN must be set in .env"
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
    creds.refresh(google.auth.transport.requests.Request())
    service = googleapiclient.discovery.build("calendar", "v3", credentials=creds)

    event_body = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_datetime, "timeZone": "UTC"},
        "end": {"dateTime": end_datetime, "timeZone": "UTC"},
    }
    result = service.events().insert(calendarId=calendar_id, body=event_body).execute()
    event_id = result.get("id", "unknown")
    logger.info("Calendar event created: %s", event_id)
    return ActionResult(
        action_type=action.action_type,
        status="success",
        message=f"Calendar event created: {event_id}",
    )
