"""Seed data for decision tracker."""
import logging
from src.decisions.detector import scan_inbox_for_decisions
from src.decisions.store import decision_store

logger = logging.getLogger(__name__)


def seed_decisions() -> int:
    """Seed decision store from inbox decisions. Returns count."""
    decision_store.clear()
    count = scan_inbox_for_decisions()
    logger.info("Decision store seeded with %d decisions", count)
    return count
