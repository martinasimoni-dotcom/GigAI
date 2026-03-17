"""
Fireflies webhook endpoint.
Receives POST /webhooks/fireflies, validates payload, publishes RawEvent to Pub/Sub.
INPUT-01
"""
import logging
import uuid

from fastapi import APIRouter, HTTPException, Request

from src.input.pubsub import publish_event
from src.shared.models.events import RawEvent

router = APIRouter()
logger = logging.getLogger(__name__)

# Keys that indicate a valid Fireflies webhook payload.
# Validation is permissive in Phase 1 — full HMAC signature check added in Phase 7.
_REQUIRED_KEYS = {"transcript", "meeting", "meetingId", "id"}


@router.post("/webhooks/fireflies")
async def receive_fireflies(request: Request) -> dict:
    """
    Receive a Fireflies meeting transcript webhook.
    Validates the payload has transcript or meeting data, then publishes to Pub/Sub.
    Returns 200 + message_id on success, 400 on validation failure.
    """
    try:
        body = await request.json()
    except Exception as exc:
        logger.warning("Failed to parse Fireflies webhook JSON: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    if not body or not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Empty or non-JSON payload")

    if not _REQUIRED_KEYS.intersection(body.keys()):
        raise HTTPException(
            status_code=400,
            detail=f"Missing required keys: payload must contain one of {sorted(_REQUIRED_KEYS)}",
        )

    raw_event = RawEvent(
        event_id=str(uuid.uuid4()),
        source="fireflies",
        raw_payload=body,
    )
    message_id = publish_event(raw_event)
    logger.info({"event": "fireflies_webhook_received", "message_id": message_id})
    return {"status": "ok", "message_id": message_id}
