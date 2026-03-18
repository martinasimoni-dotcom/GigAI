"""
Fireflies webhook endpoint.
Receives POST /webhooks/fireflies, validates payload, then either:
  - DEMO_MODE=true  → runs the full pipeline synchronously (no GCP needed)
  - DEMO_MODE=false → publishes RawEvent to Pub/Sub (production path)
INPUT-01
"""
import logging
import uuid

from fastapi import APIRouter, HTTPException, Request

from src.shared.models.events import RawEvent

router = APIRouter()
logger = logging.getLogger(__name__)

# Keys that indicate a valid Fireflies webhook payload.
_REQUIRED_KEYS = {"transcript", "meeting", "meetingId", "id"}


@router.post("/webhooks/fireflies")
async def receive_fireflies(request: Request) -> dict:
    """
    Receive a Fireflies meeting transcript webhook.
    In DEMO_MODE runs the pipeline synchronously and returns the proposal.
    In production publishes to Pub/Sub and returns the message_id.
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

    from config.settings import settings
    if settings.demo_mode:
        import asyncio
        from src.demo.pipeline import run_pipeline
        loop = asyncio.get_event_loop()
        proposal_response = await loop.run_in_executor(None, run_pipeline, raw_event)
        logger.info("DEMO fireflies webhook processed — proposal_id=%s", proposal_response.get("id"))
        return {"status": "ok", "mode": "demo", "proposal": proposal_response}

    from src.input.pubsub import publish_event
    message_id = publish_event(raw_event)
    logger.info({"event": "fireflies_webhook_received", "message_id": message_id})
    return {"status": "ok", "message_id": message_id}
