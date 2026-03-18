from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from gigai.dashboard.mock_data import (
    build_meeting_decisions,
    build_meeting_detail,
    build_meeting_revisions,
    build_meeting_transcript,
    build_meetings,
)
from gigai.dashboard.models import MeetingList

logger = logging.getLogger(__name__)
router = APIRouter(tags=["meetings"])


@router.get("/api/meetings", response_model=MeetingList)
async def list_meetings(
    project_id: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    try:
        meetings = build_meetings()
        if project_id:
            meetings = [meeting for meeting in meetings if meeting.project == project_id]
        logger.info("Retrieved %s meetings", len(meetings))
        return meetings[skip : skip + limit]
    except Exception as ex:
        logger.error("Error listing meetings: %s", ex)
        raise HTTPException(status_code=500, detail=str(ex)) from ex


@router.get("/api/meetings/{meeting_id}")
async def get_meeting(meeting_id: str):
    try:
        meeting = build_meeting_detail(meeting_id)
        logger.info("Retrieved meeting %s", meeting_id)
        return meeting
    except Exception as ex:
        logger.error("Error getting meeting %s: %s", meeting_id, ex)
        raise HTTPException(status_code=500, detail=str(ex)) from ex


@router.get("/api/meetings/{meeting_id}/transcript")
async def get_meeting_transcript(meeting_id: str):
    try:
        return build_meeting_transcript(meeting_id).model_dump()
    except Exception as ex:
        logger.error("Error getting transcript for %s: %s", meeting_id, ex)
        raise HTTPException(status_code=500, detail=str(ex)) from ex


@router.get("/api/meetings/{meeting_id}/decisions")
async def get_meeting_decisions(meeting_id: str):
    try:
        decisions = build_meeting_decisions(meeting_id)
        logger.info("Retrieved decisions for meeting %s", meeting_id)
        return decisions
    except Exception as ex:
        logger.error("Error getting decisions for %s: %s", meeting_id, ex)
        raise HTTPException(status_code=500, detail=str(ex)) from ex


@router.get("/api/meetings/{meeting_id}/revisions")
async def get_meeting_revisions(meeting_id: str):
    try:
        return build_meeting_revisions(meeting_id)
    except Exception as ex:
        logger.error("Error getting revisions for %s: %s", meeting_id, ex)
        raise HTTPException(status_code=500, detail=str(ex)) from ex
