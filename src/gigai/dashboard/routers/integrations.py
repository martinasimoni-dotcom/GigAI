from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException, WebSocket

from gigai.dashboard.mock_data import (
    build_dashboard_update,
    build_export_response,
    build_webhook_response,
)
from gigai.storage import append_audit_log

logger = logging.getLogger(__name__)
router = APIRouter(tags=["integrations", "realtime"])


@router.get("/api/export/meeting/{meeting_id}/pdf")
async def export_meeting_pdf(meeting_id: str):
    try:
        return build_export_response(meeting_id)
    except Exception as ex:
        logger.error("Error exporting meeting %s: %s", meeting_id, ex)
        raise HTTPException(status_code=500, detail=str(ex)) from ex


@router.post("/api/webhooks/meeting-ended")
async def webhook_meeting_ended(payload: dict):
    try:
        meeting_id = payload.get("meeting_id")
        logger.info("Webhook: Meeting ended - %s", meeting_id)
        append_audit_log(
            "meeting",
            str(meeting_id or "unknown"),
            "webhook_meeting_ended",
            "dashboard_api",
            {"meeting_id": meeting_id},
        )
        return build_webhook_response()
    except Exception as ex:
        logger.error("Error processing meeting-ended webhook: %s", ex)
        raise HTTPException(status_code=500, detail=str(ex)) from ex


@router.websocket("/ws/dashboard/{session_id}")
async def websocket_dashboard(websocket: WebSocket, session_id: str):
    await websocket.accept()
    logger.info("WebSocket connected: %s", session_id)
    try:
        while True:
            await asyncio.sleep(5)
            await websocket.send_json(build_dashboard_update())
    except Exception as ex:
        logger.error("WebSocket error for %s: %s", session_id, ex)
    finally:
        logger.info("WebSocket disconnected: %s", session_id)
