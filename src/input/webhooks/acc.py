"""
ACC (Autodesk Construction Cloud) webhook endpoint.
Receives POST /webhooks/acc, validates payload, publishes RawEvent to Pub/Sub.
INPUT-02
"""
import logging
import uuid

from fastapi import APIRouter, HTTPException, Request

from src.input.pubsub import publish_event
from src.shared.models.events import RawEvent

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/webhooks/acc")
async def receive_acc(request: Request) -> dict:
    """
    Receive an ACC platform webhook event.
    ACC payload schema is opaque in Phase 1 — validation is permissive.
    Full ACC schema validation deferred to Phase 7.
    Returns 200 + message_id on success, 400 on validation failure.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    if not body or not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Empty or non-JSON payload")

    raw_event = RawEvent(
        event_id=str(uuid.uuid4()),
        source="acc",
        raw_payload=body,
    )
    message_id = publish_event(raw_event)
    logger.info({"event": "acc_webhook_received", "message_id": message_id})
    return {"status": "ok", "message_id": message_id}
