"""
Context enrichment: ACC floor plan data + pgvector knowledge retrieval.
CTX-01
"""
import logging
import os
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.shared.db.vector_store import search
from src.shared.models.events import NormalizedEvent
from src.system.context.historical import HistoricalMatch, retrieve_historical

logger = logging.getLogger(__name__)

_MOCK_UNIT_IDS = [f"W-{300 + i}" for i in range(1, 13)]  # W-301..W-312


class EnrichedEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    event: NormalizedEvent
    knowledge_chunks: list[dict] = Field(default_factory=list)
    acc_floor_plan: dict = Field(default_factory=dict)
    supplier_info: dict | None = None
    relevant_rules: list[str] = Field(default_factory=list)
    historical_matches: list[HistoricalMatch] = Field(default_factory=list)


def _get_acc_floor_plan(project_id: str, location: str | None) -> dict:
    token = os.getenv("ACC_TOKEN")
    if not token:
        logger.info("ACC_TOKEN not set — returning mock floor plan for demo scenario")
        return {
            "project_id": project_id,
            "floor": location or "3rd",
            "units": _MOCK_UNIT_IDS,
            "source": "stub",
        }
    # Real ACC API call would go here (future implementation)
    # For now fall through to stub even if token present until real endpoint added
    return {
        "project_id": project_id,
        "floor": location or "unknown",
        "units": _MOCK_UNIT_IDS,
        "source": "acc_api",
    }


def enrich_event(event: NormalizedEvent, project_id: str = "demo-project") -> "EnrichedEvent":
    """
    Enrich a NormalizedEvent with ACC floor plan data and knowledge folder context.
    """
    material_new = event.material_new or ""
    location = event.location or ""

    supplier_query = f"{material_new} supplier pricing lead time"
    rules_query = f"material change approval threshold {material_new}"
    location_query = f"{location} floor plan units"

    logger.info(f"Enriching event={event.event_id} material_new='{material_new}' location='{location}'")

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

    # ACC floor plan (stub when ACC_TOKEN not set)
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
