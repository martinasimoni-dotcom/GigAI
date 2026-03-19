"""
Gmail polling connector.

Polls Gmail every POLL_INTERVAL seconds for unread emails containing
material change keywords. Deduplicates via processed_events table.
Runs the full pipeline for each new matching email.
"""
import base64
import logging
import uuid

from src.shared.db.postgres import get_connection, release_connection
from src.shared.models.events import RawEvent

logger = logging.getLogger(__name__)

# Gmail search query — only fetch emails likely to be material change related
GMAIL_QUERY = 'is:unread (material OR substitution OR "change order" OR RFI OR "material change" OR "window" OR "frame")'


def _is_processed(message_id: str) -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM processed_events WHERE source = 'gmail' AND source_id = %s",
                (message_id,),
            )
            return cur.fetchone() is not None
    finally:
        release_connection(conn)


def _mark_processed(message_id: str) -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO processed_events (source, source_id) VALUES ('gmail', %s) ON CONFLICT DO NOTHING",
                (message_id,),
            )
        conn.commit()
    finally:
        release_connection(conn)


def _extract_body(payload: dict) -> str:
    """Recursively extract plain text body from Gmail message payload."""
    mime = payload.get("mimeType", "")
    if mime == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
    for part in payload.get("parts", []):
        text = _extract_body(part)
        if text:
            return text
    return ""


def _build_gmail_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from config.settings import settings

    creds = Credentials(
        token=None,
        refresh_token=settings.gmail_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.gmail_client_id,
        client_secret=settings.gmail_client_secret,
    )
    creds.refresh(Request())
    return build("gmail", "v1", credentials=creds)


def poll_once() -> int:
    """
    Poll Gmail once, run pipeline for any new matching emails.
    Returns the number of emails processed.
    """
    from config.settings import settings

    if not all([settings.gmail_refresh_token, settings.gmail_client_id, settings.gmail_client_secret]):
        logger.info("Gmail credentials not set — skipping Gmail poll")
        return 0

    try:
        service = _build_gmail_service()
    except Exception as exc:
        logger.warning("Gmail auth failed: %s", exc)
        return 0

    try:
        results = service.users().messages().list(
            userId="me", q=GMAIL_QUERY, maxResults=10
        ).execute()
        messages = results.get("messages", [])
    except Exception as exc:
        logger.warning("Gmail list failed: %s", exc)
        return 0

    if not messages:
        logger.debug("Gmail poll: no new matching emails")
        return 0

    processed = 0
    for msg_ref in messages:
        msg_id = msg_ref["id"]
        if _is_processed(msg_id):
            logger.debug("Gmail message %s already processed — skipping", msg_id)
            continue

        try:
            msg = service.users().messages().get(
                userId="me", id=msg_id, format="full"
            ).execute()
        except Exception as exc:
            logger.warning("Failed to fetch Gmail message %s: %s", msg_id, exc)
            continue

        headers = {
            h["name"]: h["value"]
            for h in msg.get("payload", {}).get("headers", [])
        }
        subject = headers.get("Subject", "No Subject")
        sender = headers.get("From", "Unknown")
        body = _extract_body(msg.get("payload", {}))

        if not body.strip():
            logger.debug("Gmail message %s has no text body — skipping", msg_id)
            _mark_processed(msg_id)  # mark so we don't retry empty emails
            continue

        full_text = f"Subject: {subject}\nFrom: {sender}\n\n{body}"

        payload = {
            "id": msg_id,
            "meetingId": msg_id,
            "meeting": {"title": subject},
            "transcript": full_text,
            "sentences": [{"text": body, "speaker": sender}],
            "summary": {"action_items": []},
        }

        raw_event = RawEvent(
            event_id=str(uuid.uuid4()),
            source="gmail",
            raw_payload=payload,
        )

        try:
            from src.demo.pipeline import run_pipeline
            run_pipeline(raw_event)
            _mark_processed(msg_id)
            processed += 1
            logger.info("Processed Gmail message id=%s subject=%s", msg_id, subject)
        except Exception as exc:
            logger.error("Pipeline failed for Gmail message %s: %s", msg_id, exc)

    return processed
