from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException

from gigai.fireflies_stt import FirefliesIntegrationError, resolve_fireflies_transcript
from gigai.orchestrator import process_webhook
from gigai.voice import build_voice_focus_payload

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health", "voice"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "gigai_dashboard_api",
        "version": "0.3.0",
        "timestamp": datetime.now().isoformat(),
    }


@router.post("/voice/command")
async def voice_command(payload: dict):
    normalized_input = dict(payload)
    transcript = str(
        normalized_input.get("transcript")
        or normalized_input.get("voice_text")
        or ""
    ).strip()

    if not transcript:
        try:
            fireflies_transcript, fireflies_metadata = resolve_fireflies_transcript(
                normalized_input
            )
        except FirefliesIntegrationError as ex:
            raise HTTPException(status_code=400, detail=str(ex)) from ex

        if fireflies_transcript:
            transcript = fireflies_transcript
            normalized_input["transcript"] = transcript
            normalized_input.update(fireflies_metadata)

    if not transcript:
        raise HTTPException(
            status_code=400,
            detail=(
                "transcript is required. "
                "Or send fireflies_latest=true / fireflies_transcript_id with Fireflies enabled."
            ),
        )

    normalized_payload = build_voice_focus_payload(normalized_input)
    logger.info("Received voice command for project %s", normalized_payload.get("projectId"))
    return process_webhook(normalized_payload)
