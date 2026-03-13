"""
Historical pattern retrieval via pgvector semantic search.
CTX-02
"""
import logging

from pydantic import BaseModel, ConfigDict

from src.shared.db.vector_store import search
from src.shared.models.events import NormalizedEvent

logger = logging.getLogger(__name__)


class HistoricalMatch(BaseModel):
    model_config = ConfigDict(extra="ignore")

    content: str
    source: str
    metadata: dict
    similarity: float
    outcome: str | None = None
    success_rate: float | None = None


def retrieve_historical(event: NormalizedEvent, top_k: int = 5) -> list[HistoricalMatch]:
    """
    Retrieve historical matches for the given event using pgvector semantic search.

    Constructs a query from event fields, calls search(), maps rows to HistoricalMatch,
    and returns results sorted by similarity descending.
    """
    query = (
        f"{event.event_type} {event.material_original or ''} "
        f"to {event.material_new or ''} {event.location or ''}"
    ).strip()

    logger.info(f"Historical search query='{query}' top_k={top_k}")
    rows = search(query_text=query, top_k=top_k)

    matches = []
    for row in rows:
        meta = row.get("metadata") or {}
        matches.append(
            HistoricalMatch(
                content=row["content"],
                source=row["source"],
                metadata=meta,
                similarity=float(row["similarity"]),
                outcome=meta.get("outcome"),
                success_rate=float(meta["success_rate"]) if "success_rate" in meta else None,
            )
        )

    return sorted(matches, key=lambda m: m.similarity, reverse=True)
