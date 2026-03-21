"""
Change Impact Simulator API routes.

  POST /api/impact/simulate    — run full impact analysis
  GET  /api/impact/eva/{id}    — earned value analysis for a project
"""
import logging

from fastapi import APIRouter
from pydantic import BaseModel

from src.impact.simulator import simulate_change_impact

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/impact", tags=["impact"])


class SimulateRequest(BaseModel):
    project_id: str
    change_description: str
    cost_delta: float = 0.0
    schedule_delay_days: int = 0


@router.post("/simulate")
async def simulate(request: SimulateRequest):
    """Run full change impact simulation with EVA + Monte Carlo."""
    result = simulate_change_impact(
        project_id=request.project_id,
        change_description=request.change_description,
        cost_delta=request.cost_delta,
        schedule_delay_days=request.schedule_delay_days,
    )
    return result


@router.get("/eva/{project_id}")
async def get_eva(project_id: str):
    """Get earned value analysis for a project (no change scenario)."""
    result = simulate_change_impact(
        project_id=project_id,
        change_description="Baseline analysis (no change)",
        cost_delta=0,
        schedule_delay_days=0,
    )
    return {
        "project_id": project_id,
        "earned_value": result.get("earned_value"),
        "monte_carlo": result.get("monte_carlo"),
        "overall_risk": result.get("overall_risk"),
    }
