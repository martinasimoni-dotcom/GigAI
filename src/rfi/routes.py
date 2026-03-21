"""
RFI/Submittal API routes.

  GET   /api/rfis                — list/filter RFIs
  GET   /api/rfis/stats          — RFI statistics
  GET   /api/rfis/{rfi_id}       — single RFI detail
  POST  /api/rfis/{rfi_id}/draft — generate AI draft response
  POST  /api/rfis/{rfi_id}/edit  — apply PM edits to draft
  POST  /api/rfis/{rfi_id}/send  — mark RFI as sent
  POST  /api/rfis/{rfi_id}/close — mark RFI as closed
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.rfi.store import rfi_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rfis", tags=["rfis"])


class EditRequest(BaseModel):
    edited_text: str


# ---------------------------------------------------------------------------
# List & Stats
# ---------------------------------------------------------------------------

@router.get("")
async def list_rfis(
    project_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None, description="open, drafted, reviewed, sent, responded, closed"),
    priority: Optional[str] = Query(None, description="low, medium, high, critical"),
    assignee: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    items, total = rfi_store.list_rfis(
        project_id=project_id,
        status=status,
        priority=priority,
        assignee=assignee,
        search=search,
        limit=limit,
        offset=offset,
    )
    return {
        "rfis": [_serialize(r) for r in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/stats")
async def rfi_stats():
    all_rfis, total = rfi_store.list_rfis(limit=10000)
    by_status = {}
    by_priority = {}
    by_category = {}
    for rfi in all_rfis:
        by_status[rfi.status] = by_status.get(rfi.status, 0) + 1
        by_priority[rfi.priority] = by_priority.get(rfi.priority, 0) + 1
        by_category[rfi.category] = by_category.get(rfi.category, 0) + 1

    needs_attention = sum(1 for r in all_rfis if r.status in ("open", "drafted"))
    avg_age = sum(r.age_hours for r in all_rfis) / max(total, 1)

    return {
        "total": total,
        "needs_attention": needs_attention,
        "avg_age_hours": round(avg_age, 1),
        "by_status": by_status,
        "by_priority": by_priority,
        "by_category": by_category,
    }


# ---------------------------------------------------------------------------
# Single RFI
# ---------------------------------------------------------------------------

@router.get("/{rfi_id}")
async def get_rfi(rfi_id: str):
    rfi = rfi_store.get(rfi_id)
    if not rfi:
        raise HTTPException(status_code=404, detail=f"RFI {rfi_id} not found")
    return _serialize(rfi)


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

@router.post("/{rfi_id}/draft")
async def draft_response(rfi_id: str):
    """Generate an AI-drafted response for this RFI."""
    from src.rfi.drafter import draft_rfi_response
    rfi = draft_rfi_response(rfi_id)
    if not rfi:
        raise HTTPException(status_code=404, detail=f"RFI {rfi_id} not found")
    return _serialize(rfi)


@router.post("/{rfi_id}/edit")
async def edit_response(rfi_id: str, request: EditRequest):
    """Apply PM edits to the RFI draft."""
    from src.rfi.drafter import apply_pm_edit
    rfi = apply_pm_edit(rfi_id, request.edited_text)
    if not rfi:
        raise HTTPException(status_code=404, detail=f"RFI {rfi_id} not found or no draft exists")
    return _serialize(rfi)


@router.post("/{rfi_id}/send")
async def send_rfi(rfi_id: str):
    """Mark RFI response as sent."""
    from src.rfi.drafter import send_rfi as do_send
    rfi = do_send(rfi_id)
    if not rfi:
        raise HTTPException(status_code=404, detail=f"RFI {rfi_id} not found")
    return _serialize(rfi)


@router.post("/{rfi_id}/close")
async def close_rfi(rfi_id: str):
    """Close the RFI."""
    from src.rfi.drafter import close_rfi as do_close
    rfi = do_close(rfi_id)
    if not rfi:
        raise HTTPException(status_code=404, detail=f"RFI {rfi_id} not found")
    return _serialize(rfi)


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def _serialize(rfi) -> dict:
    result = {
        "rfi_id": rfi.rfi_id,
        "inbox_item_id": rfi.inbox_item_id,
        "project_id": rfi.project_id,
        "project_name": rfi.project_name,
        "title": rfi.title,
        "question": rfi.question,
        "category": rfi.category,
        "status": rfi.status,
        "priority": rfi.priority,
        "assignee": rfi.assignee,
        "assignee_email": rfi.assignee_email,
        "requester": rfi.requester,
        "requester_email": rfi.requester_email,
        "source": rfi.source,
        "age_hours": rfi.age_hours,
        "created_at": rfi.created_at.isoformat(),
        "sent_at": rfi.sent_at.isoformat() if rfi.sent_at else None,
        "responded_at": rfi.responded_at.isoformat() if rfi.responded_at else None,
        "closed_at": rfi.closed_at.isoformat() if rfi.closed_at else None,
    }
    if rfi.response:
        result["response"] = {
            "draft_text": rfi.response.draft_text,
            "knowledge_sources": rfi.response.knowledge_sources,
            "past_rfi_references": rfi.response.past_rfi_references,
            "confidence": rfi.response.confidence,
            "drafted_at": rfi.response.drafted_at.isoformat(),
            "edited_by_pm": rfi.response.edited_by_pm,
            "pm_edits": rfi.response.pm_edits,
        }
    else:
        result["response"] = None
    return result
