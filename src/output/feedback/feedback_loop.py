"""Feedback Loop (OUT-10): records PM decisions to PostgreSQL + pgvector."""
import logging

from src.shared.db import postgres
from src.shared.db.vector_store import embed_and_store
from src.shared.models.proposals import Proposal

logger = logging.getLogger(__name__)

_DDL = """
CREATE TABLE IF NOT EXISTS decisions (
    id          SERIAL PRIMARY KEY,
    proposal_id TEXT NOT NULL,
    event_id    TEXT NOT NULL,
    decision    TEXT NOT NULL,
    reason      TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
)
"""

_INSERT = """
INSERT INTO decisions (proposal_id, event_id, decision, reason)
VALUES (%s, %s, %s, %s)
"""


def record_decision(
    proposal_id: str,
    decision: str,
    reason: str | None,
    proposal: Proposal,
) -> None:
    conn = postgres.get_connection()
    try:
        postgres.execute(conn, _DDL)
        postgres.execute(conn, _INSERT, (proposal_id, proposal.event_id, decision, reason))
    finally:
        postgres.release_connection(conn)

    decision_text = (
        f"Decision: {decision} for proposal {proposal_id} "
        f"(event {proposal.event_id}). Reason: {reason or 'none'}. "
        f"Recommendation was: {proposal.recommendation}."
    )
    embed_and_store(
        [decision_text],
        source="decisions",
        metadata={"proposal_id": proposal_id, "event_id": proposal.event_id},
    )
    logger.info("Decision recorded: proposal_id=%s decision=%s", proposal_id, decision)
