"""
Auto-generated reports API routes.

  GET  /api/reports/daily        — generate daily digest
  GET  /api/reports/weekly       — generate weekly status report
"""
import logging
from typing import Optional

from fastapi import APIRouter, Query

from src.reports.generator import generate_daily_digest, generate_weekly_report

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/daily")
async def daily_digest(project_id: Optional[str] = Query(None)):
    return generate_daily_digest(project_id)


@router.get("/weekly")
async def weekly_report(project_id: Optional[str] = Query(None)):
    return generate_weekly_report(project_id)
