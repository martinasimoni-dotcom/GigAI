"""
Unified inbox API routes.

  GET   /api/inbox              — list/filter inbox items
  GET   /api/inbox/stats        — inbox statistics
  GET   /api/inbox/{item_id}    — single item detail
  POST  /api/inbox/{item_id}/read — mark item as read
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.inbox.store import inbox_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/inbox", tags=["inbox"])


@router.get("")
async def list_inbox(
    project_id: Optional[str] = Query(None, description="Filter by project"),
    comm_type: Optional[str] = Query(None, description="Filter: decision, action-item, FYI, question, escalation"),
    min_urgency: int = Query(1, ge=1, le=5),
    max_urgency: int = Query(5, ge=1, le=5),
    unread_only: bool = Query(False),
    search: Optional[str] = Query(None, description="Search summary, sender, subject"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    items, total = inbox_store.list_items(
        project_id=project_id,
        comm_type=comm_type,
        min_urgency=min_urgency,
        max_urgency=max_urgency,
        unread_only=unread_only,
        search=search,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [_serialize(i) for i in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/stats")
async def inbox_stats():
    all_items, total = inbox_store.list_items(limit=10000)
    unread = sum(1 for i in all_items if not i.is_read)
    by_type = {}
    by_urgency = {}
    by_source = {}
    for item in all_items:
        by_type[item.comm_type] = by_type.get(item.comm_type, 0) + 1
        by_urgency[item.urgency] = by_urgency.get(item.urgency, 0) + 1
        by_source[item.source] = by_source.get(item.source, 0) + 1
    return {
        "total": total,
        "unread": unread,
        "by_type": by_type,
        "by_urgency": by_urgency,
        "by_source": by_source,
    }


@router.get("/{item_id}")
async def get_inbox_item(item_id: str):
    item = inbox_store.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Inbox item {item_id} not found")
    return _serialize(item)


@router.post("/{item_id}/read")
async def mark_read(item_id: str):
    success = inbox_store.mark_read(item_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Inbox item {item_id} not found")
    return {"status": "ok", "item_id": item_id, "is_read": True}


@router.post("/{item_id}/archive")
async def archive_item(item_id: str):
    """Hide item from active feed. Data preserved — queryable via /api/inbox/archived."""
    success = inbox_store.archive(item_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Inbox item {item_id} not found")
    return {"status": "ok", "item_id": item_id, "archived": True}


@router.post("/{item_id}/unarchive")
async def unarchive_item(item_id: str):
    """Restore archived item back to active feed."""
    success = inbox_store.unarchive(item_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Archived item {item_id} not found")
    return {"status": "ok", "item_id": item_id, "archived": False}


@router.get("/archived")
async def list_archived(
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Query archived items — data is always stored, just hidden from active feed."""
    items, total = inbox_store.list_archived(search=search, limit=limit, offset=offset)
    return {"items": [_serialize(i) for i in items], "total": total, "limit": limit, "offset": offset}


def _serialize(item) -> dict:
    """Convert InboxItem to API response dict."""
    return {
        "item_id": item.item_id,
        "source": item.source,
        "comm_type": item.comm_type,
        "urgency": item.urgency,
        "summary": item.summary,
        "raw_text": item.raw_text,
        "project_id": item.project_id,
        "project_name": item.project_name,
        "sender": item.sender,
        "sender_email": item.sender_email,
        "subject": item.subject,
        "source_url": item.source_url,
        "action_items": [
            {
                "assignee": ai.assignee,
                "deadline": ai.deadline.isoformat() if ai.deadline else None,
                "priority": ai.priority,
                "description": ai.description,
            }
            for ai in item.action_items
        ],
        "received_at": item.received_at.isoformat(),
        "classified_at": item.classified_at.isoformat() if item.classified_at else None,
        "is_read": item.is_read,
    }
