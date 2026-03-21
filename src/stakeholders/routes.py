"""
Stakeholder communication map API routes.

  GET  /api/stakeholders/graph              — full graph data
  GET  /api/stakeholders/project/{id}       — stakeholders for a project
  GET  /api/stakeholders/chain/{project_id} — notification chain for a change
  POST /api/stakeholders/draft-messages     — draft personalized notifications
  GET  /api/stakeholders/{person_id}/interactions — recent interactions
"""
import logging
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from src.stakeholders.graph import stakeholder_graph, draft_stakeholder_messages

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stakeholders", tags=["stakeholders"])


class DraftRequest(BaseModel):
    project_id: str
    change_summary: str
    change_type: str = "material"


@router.get("/graph")
async def get_graph():
    return stakeholder_graph.get_graph_data()


@router.get("/project/{project_id}")
async def get_project_stakeholders(project_id: str):
    stakeholders = stakeholder_graph.get_stakeholders_for_project(project_id)
    return {"project_id": project_id, "stakeholders": stakeholders, "count": len(stakeholders)}


@router.get("/chain/{project_id}")
async def get_notification_chain(
    project_id: str,
    change_type: str = Query("material", description="material, schedule, safety, budget"),
):
    chain = stakeholder_graph.get_notification_chain(project_id, change_type)
    return {"project_id": project_id, "change_type": change_type, "chain": chain, "count": len(chain)}


@router.post("/draft-messages")
async def draft_messages(request: DraftRequest):
    messages = draft_stakeholder_messages(
        project_id=request.project_id,
        change_summary=request.change_summary,
        change_type=request.change_type,
    )
    return {"messages": messages, "count": len(messages)}


@router.get("/{person_id}/interactions")
async def get_interactions(person_id: str, limit: int = Query(10, ge=1, le=50)):
    interactions = stakeholder_graph.get_recent_interactions(person_id, limit)
    return {"person_id": person_id, "interactions": interactions, "count": len(interactions)}
