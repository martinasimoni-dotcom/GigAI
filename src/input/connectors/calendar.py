"""
Google Calendar polling connector.
Polls Calendar API for delivery/installation events in the next 7 days and publishes to Pub/Sub.
INPUT-04
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Callable

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from config.settings import settings
from src.input.pubsub import publish_event
from src.shared.models.events import RawEvent

logger = logging.getLogger(__name__)

# Keywords that identify construction-relevant calendar events.
CALENDAR_KEYWORDS = {"delivery", "installation", "material", "inspection"}

# Look-ahead window in days.
CALENDAR_LOOKAHEAD_DAYS = 7


def _build_calendar_service():
    """
    Build and return an authenticated Calendar API service client.
    Reuses Gmail OAuth credentials (same Google account).
    WARNING: Do not call at module level — build inside poll_calendar() to avoid import-time errors.
    """
    creds = Credentials(
        token=None,
        refresh_token=settings.gmail_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.gmail_client_id,
        client_secret=settings.gmail_client_secret,
    )
    creds.refresh(Request())
    return build("calendar", "v3", credentials=creds)


def poll_calendar(publish_fn: Callable = publish_event) -> list[str]:
    """
    Poll Google Calendar for delivery/installation events in the next 7 days.

    Uses datetime.now(timezone.utc) — NOT datetime.utcnow() — to produce
    RFC3339-compliant ISO strings with timezone offset (required by Calendar API).

    singleEvents=True is required when orderBy="startTime" (Calendar API constraint).

    Args:
        publish_fn: Callable accepting a RawEvent and returning message_id.
                    Default is publish_event. Injectable for test isolation.

    Returns:
        List of Pub/Sub message_ids for each published event.
    """
    service = _build_calendar_service()
    now = datetime.now(timezone.utc)
    time_max = now + timedelta(days=CALENDAR_LOOKAHEAD_DAYS)

    events_result = service.events().list(
        calendarId="primary",
        timeMin=now.isoformat(),
        timeMax=time_max.isoformat(),
        singleEvents=True,       # Required for orderBy="startTime"
        orderBy="startTime",
        maxResults=50,
    ).execute()

    items = events_result.get("items", [])
    published_ids: list[str] = []

    for event in items:
        summary = event.get("summary", "").lower()
        description = event.get("description", "").lower()
        text = summary + " " + description

        if any(kw in text for kw in CALENDAR_KEYWORDS):
            raw_event = RawEvent(
                event_id=str(uuid.uuid4()),
                source="calendar",
                raw_payload=event,
            )
            message_id = publish_fn(raw_event)
            published_ids.append(message_id)
            logger.info({"event": "calendar_event_published", "calendar_event_id": event.get("id"), "message_id": message_id})

    return published_ids
