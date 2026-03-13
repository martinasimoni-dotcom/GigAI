"""
Context enrichment: ACC floor plan data + pgvector knowledge retrieval.
CTX-01
"""
import logging
import os

from pydantic import BaseModel, ConfigDict, Field

from src.shared.clients.acc import get_floor_plan
from src.shared.db.vector_store import search
from src.shared.models.events import NormalizedEvent
from src.system.context.historical import HistoricalMatch, retrieve_historical

logger = logging.getLogger(__name__)


class EnrichedEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    event: NormalizedEvent
    knowledge_chunks: list[dict] = Field(default_factory=list)
    acc_floor_plan: dict = Field(default_factory=dict)
    supplier_info: dict | None = None
    relevant_rules: list[str] = Field(default_factory=list)
    historical_matches: list[HistoricalMatch] = Field(default_factory=list)


def _get_acc_floor_plan(project_id: str, location: str | None) -> dict:
    """
    Fetch real floor plan / location data from ACC Locations API.

    Requires ACC_CLIENT_ID and ACC_CLIENT_SECRET in environment.
    Raises RuntimeError if credentials are not set.
    """
    floor_plan = get_floor_plan(project_id, location_query=location)
    logger.info(
        "ACC floor plan fetched: project=%s nodes=%d",
        project_id,
        len(floor_plan.get("nodes", [])),
    )
    return floor_plan


def enrich_event(event: NormalizedEvent, project_id: str | None = None) -> "EnrichedEvent":
    """
    Enrich a NormalizedEvent with ACC floor plan data and knowledge folder context.

    Args:
        event:      The normalized event to enrich.
        project_id: ACC project ID. Falls back to ACC_PROJECT_ID env var.

    Raises:
        RuntimeError if ACC_PROJECT_ID, ACC_CLIENT_ID, or ACC_CLIENT_SECRET
        are not configured in .env.
    """
    if project_id is None:
        project_id = os.getenv("ACC_PROJECT_ID")
        if not project_id:
            raise RuntimeError(
                "ACC_PROJECT_ID must be set in .env (or pass project_id explicitly)"
            )

    material_new = event.material_new or ""
    location = event.location or ""

    supplier_query = f"{material_new} supplier pricing lead time"
    rules_query = f"material change approval threshold {material_new}"
    location_query = f"{location} floor plan units"

    logger.info(
        "Enriching event=%s material_new='%s' location='%s'",
        event.event_id, material_new, location,
    )

    supplier_results = search(supplier_query, top_k=5)
    rules_results = search(rules_query, top_k=5)
    location_results = search(location_query, top_k=5)

    # Deduplicate by id
    seen_ids: set = set()
    all_chunks: list[dict] = []
    for row in supplier_results + rules_results + location_results:
        row_id = row.get("id")
        if row_id not in seen_ids:
            seen_ids.add(row_id)
            all_chunks.append(row)

    # Extract supplier_info from first supplier result
    supplier_info: dict | None = None
    if supplier_results:
        first = supplier_results[0]
        supplier_info = {
            "name": first.get("source", "unknown"),
            "content": first.get("content", ""),
            "source": first.get("source", ""),
            "similarity": first.get("similarity", 0.0),
        }

    # Extract relevant rule texts (top 3 from rules query)
    relevant_rules = [r["content"] for r in rules_results[:3]]

    # ACC floor plan — real API call (raises RuntimeError if credentials not set)
    acc_floor_plan = _get_acc_floor_plan(project_id, location)

    # Historical matches
    historical_matches = retrieve_historical(event, top_k=5)

    return EnrichedEvent(
        event=event,
        knowledge_chunks=all_chunks,
        acc_floor_plan=acc_floor_plan,
        supplier_info=supplier_info,
        relevant_rules=relevant_rules,
        historical_matches=historical_matches,
    )
