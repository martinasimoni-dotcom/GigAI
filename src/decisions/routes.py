"""
Decision tracker API routes.

  GET  /api/decisions            — list/filter/search decisions
  GET  /api/decisions/stats      — decision statistics
  GET  /api/decisions/timeline   — chronological timeline for a project
  GET  /api/decisions/{id}       — single decision detail
  POST /api/decisions/{id}/check — check for contradictions
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.decisions.store import decision_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/decisions", tags=["decisions"])


@router.get("")
async def list_decisions(
    project_id: Optional[str] = Query(None),
    decided_by: Optional[str] = Query(None),
    source: Optional[str] = Query(None, description="meeting, email, proposal, acc, internal"),
    search: Optional[str] = Query(None, description="Search title, description, person, tags"),
    date_from: Optional[str] = Query(None, description="ISO date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="ISO date (YYYY-MM-DD)"),
    tag: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    items, total = decision_store.list_decisions(
        project_id=project_id,
        decided_by=decided_by,
        source=source,
        search=search,
        date_from=date_from,
        date_to=date_to,
        tag=tag,
        limit=limit,
        offset=offset,
    )
    return {
        "decisions": [_serialize(d) for d in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/stats")
async def decision_stats():
    all_decisions, total = decision_store.list_decisions(limit=10000)
    by_source = {}
    by_project = {}
    by_person = {}
    all_tags = {}
    for d in all_decisions:
        by_source[d.source] = by_source.get(d.source, 0) + 1
        if d.project_name:
            by_project[d.project_name] = by_project.get(d.project_name, 0) + 1
        by_person[d.decided_by] = by_person.get(d.decided_by, 0) + 1
        for t in d.tags:
            all_tags[t] = all_tags.get(t, 0) + 1
    return {
        "total": total,
        "by_source": by_source,
        "by_project": dict(sorted(by_project.items(), key=lambda x: -x[1])[:10]),
        "by_person": dict(sorted(by_person.items(), key=lambda x: -x[1])[:10]),
        "tags": dict(sorted(all_tags.items(), key=lambda x: -x[1])),
    }


@router.get("/timeline")
async def decision_timeline(
    project_id: Optional[str] = Query(None, description="Filter timeline by project"),
    limit: int = Query(100, ge=1, le=500),
):
    items, _ = decision_store.list_decisions(project_id=project_id, limit=limit)
    return {
        "timeline": [
            {
                "decision_id": d.decision_id,
                "title": d.title,
                "decided_by": d.decided_by,
                "source": d.source,
                "decided_at": d.decided_at.isoformat(),
                "project_name": d.project_name,
                "tags": d.tags,
            }
            for d in items
        ],
        "total": len(items),
    }


@router.get("/{decision_id}")
async def get_decision(decision_id: str):
    d = decision_store.get(decision_id)
    if not d:
        raise HTTPException(status_code=404, detail=f"Decision {decision_id} not found")
    return _serialize(d)


@router.post("/{decision_id}/check")
async def check_contradictions(decision_id: str):
    """Check if this decision contradicts any existing decisions."""
    d = decision_store.get(decision_id)
    if not d:
        raise HTTPException(status_code=404, detail=f"Decision {decision_id} not found")
    contradictions = decision_store.find_contradictions(d)
    return {
        "decision_id": decision_id,
        "contradictions_found": len(contradictions),
        "contradictions": contradictions,
    }


def _serialize(d) -> dict:
    return {
        "decision_id": d.decision_id,
        "inbox_item_id": d.inbox_item_id,
        "project_id": d.project_id,
        "project_name": d.project_name,
        "title": d.title,
        "description": d.description,
        "decided_by": d.decided_by,
        "decided_by_email": d.decided_by_email,
        "source": d.source,
        "source_url": d.source_url,
        "context": d.context,
        "linked_documents": d.linked_documents,
        "linked_rfis": d.linked_rfis,
        "linked_proposals": d.linked_proposals,
        "tags": d.tags,
        "decided_at": d.decided_at.isoformat(),
        "recorded_at": d.recorded_at.isoformat(),
        "superseded_by": d.superseded_by,
    }
