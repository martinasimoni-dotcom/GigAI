from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from gigai.dashboard.mock_data import (
    build_dashboard_summary,
    build_revisions,
    build_team_workload,
    build_timeline,
)
from gigai.dashboard.models import DashboardSummary

logger = logging.getLogger(__name__)
router = APIRouter(tags=["dashboard", "revisions"])


@router.get("/api/dashboard/summary", response_model=DashboardSummary)
async def get_dashboard_summary(project_id: Optional[str] = None):
    try:
        summary = build_dashboard_summary()
        if project_id:
            logger.info("Returning dashboard summary for project %s", project_id)
        return summary
    except Exception as ex:
        logger.error("Error getting dashboard summary: %s", ex)
        raise HTTPException(status_code=500, detail=str(ex)) from ex


@router.get("/api/dashboard/timeline")
async def get_timeline(project_id: Optional[str] = None):
    try:
        timeline = build_timeline()
        if project_id:
            logger.info("Returning dashboard timeline for project %s", project_id)
        return timeline
    except Exception as ex:
        logger.error("Error getting timeline: %s", ex)
        raise HTTPException(status_code=500, detail=str(ex)) from ex


@router.get("/api/revisions")
async def list_revisions(
    meeting_id: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    try:
        revisions = build_revisions()
        if meeting_id:
            revisions["revisions"] = [
                revision
                for revision in revisions["revisions"]
                if revision["meeting_id"] == meeting_id
            ]
        revisions["revisions"] = revisions["revisions"][skip : skip + limit]
        revisions["total"] = len(revisions["revisions"])
        logger.info("Retrieved %s revisions", revisions["total"])
        return revisions
    except Exception as ex:
        logger.error("Error listing revisions: %s", ex)
        raise HTTPException(status_code=500, detail=str(ex)) from ex


@router.get("/api/dashboard/architects")
async def get_team_workload():
    try:
        team_data = build_team_workload()
        logger.info("Retrieved team workload for %s members", len(team_data["architects"]))
        return team_data
    except Exception as ex:
        logger.error("Error getting team workload: %s", ex)
        raise HTTPException(status_code=500, detail=str(ex)) from ex
