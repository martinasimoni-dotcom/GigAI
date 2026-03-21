"""
Smart notifications API routes.

  GET  /api/notifications           — list notifications
  GET  /api/notifications/stats     — notification statistics
  GET  /api/notifications/config    — get notification config
  POST /api/notifications/config    — update notification config
  POST /api/notifications/{id}/read — mark as read
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.notifications.smart import notification_center

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class ConfigUpdate(BaseModel):
    immediate_threshold: Optional[int] = None
    digest_frequency: Optional[str] = None


@router.get("")
async def list_notifications(
    tier: Optional[str] = Query(None, description="immediate, important, digest"),
    unread_only: bool = Query(False),
    project_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    items, total = notification_center.list_notifications(
        tier=tier,
        unread_only=unread_only,
        project_id=project_id,
        limit=limit,
        offset=offset,
    )
    return {
        "notifications": [n.to_dict() for n in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/stats")
async def notification_stats():
    return notification_center.get_stats()


@router.get("/config")
async def get_config():
    return notification_center.get_config()


@router.post("/config")
async def update_config(config: ConfigUpdate):
    updates = {}
    if config.immediate_threshold is not None:
        updates["immediate_threshold"] = config.immediate_threshold
    if config.digest_frequency is not None:
        updates["digest_frequency"] = config.digest_frequency
    return notification_center.update_config(**updates)


@router.post("/{notif_id}/read")
async def mark_read(notif_id: str):
    if not notification_center.mark_read(notif_id):
        raise HTTPException(status_code=404, detail=f"Notification {notif_id} not found")
    return {"status": "ok", "notif_id": notif_id, "read": True}
