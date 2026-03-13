"""
Gmail polling connector.
Polls Gmail API for unread material-related emails and publishes to Pub/Sub.
INPUT-03
"""
import logging
import uuid
from typing import Callable

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from config.settings import settings
from src.input.pubsub import publish_event
from src.shared.models.events import RawEvent

logger = logging.getLogger(__name__)

# Keywords defining "material-related" emails. Used in Gmail q= filter.
GMAIL_KEYWORDS = ["material", "substitution", "change", "approval", "RFI"]
GMAIL_QUERY = "is:unread (" + " OR ".join(GMAIL_KEYWORDS) + ")"


def _build_gmail_service():
    """
    Build and return an authenticated Gmail API service client.
    Uses stored refresh token — no browser OAuth flow at runtime.
    WARNING: Do not call at module level — builds service on each call.
    Call lazily inside poll_gmail() to avoid import-time credential errors.
    """
    creds = Credentials(
        token=None,
        refresh_token=settings.gmail_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.gmail_client_id,
        client_secret=settings.gmail_client_secret,
    )
    creds.refresh(Request())
    return build("gmail", "v1", credentials=creds)


def poll_gmail(publish_fn: Callable = publish_event) -> list[str]:
    """
    Poll Gmail for unread material-related emails and publish each to Pub/Sub.

    Args:
        publish_fn: Callable accepting a RawEvent and returning message_id.
                    Default is publish_event. Injectable for test isolation.

    Returns:
        List of Pub/Sub message_ids for each published email.
    """
    service = _build_gmail_service()
    results = service.users().messages().list(
        userId="me",
        q=GMAIL_QUERY,
        maxResults=50,
    ).execute()

    messages = results.get("messages", [])
    published_ids: list[str] = []

    for msg in messages:
        full_msg = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="full",
        ).execute()

        raw_event = RawEvent(
            event_id=str(uuid.uuid4()),
            source="gmail",
            raw_payload={"gmail_message_id": msg["id"], "message": full_msg},
        )
        message_id = publish_fn(raw_event)
        published_ids.append(message_id)
        logger.info({"event": "gmail_email_published", "gmail_message_id": msg["id"], "message_id": message_id})

    return published_ids
