"""
Decision detector — captures decisions from inbox communications.

Scans inbox items classified as 'decision' and creates decision records
in the decision store.
"""
import logging
from typing import Optional

from src.decisions.models import Decision
from src.decisions.store import decision_store

logger = logging.getLogger(__name__)


def detect_decision_from_inbox_item(item: dict) -> Optional[Decision]:
    """Check if an inbox item contains a decision. Returns a Decision if detected."""
    if item.get("comm_type") != "decision":
        return None

    # Map inbox source to decision source
    source_map = {"gmail": "email", "fireflies": "meeting", "acc": "acc", "internal": "internal"}
    source = source_map.get(item.get("source", ""), "internal")

    decision = Decision(
        inbox_item_id=item.get("item_id"),
        project_id=item.get("project_id"),
        project_name=item.get("project_name"),
        title=item.get("summary", "")[:150],
        description=item.get("raw_text", ""),
        decided_by=item.get("sender", "Unknown"),
        decided_by_email=item.get("sender_email"),
        source=source,
        source_url=item.get("source_url"),
        context=item.get("subject", ""),
        tags=_extract_tags(item.get("raw_text", "")),
    )

    # Check for contradictions before adding
    contradictions = decision_store.find_contradictions(decision)
    if contradictions:
        logger.warning(
            "Decision '%s' may contradict %d existing decision(s): %s",
            decision.title[:50],
            len(contradictions),
            [c["existing_title"][:40] for c in contradictions],
        )

    decision_store.add(decision)
    logger.info("Decision captured: %s — %s", decision.decision_id, decision.title[:60])
    return decision


def scan_inbox_for_decisions() -> int:
    """Scan all inbox items and create decisions for items classified as 'decision'. Returns count."""
    from src.inbox.store import inbox_store
    items, _ = inbox_store.list_items(comm_type="decision", limit=10000)
    count = 0
    existing_inbox_ids = {d.inbox_item_id for d in decision_store._items if d.inbox_item_id}

    for item in items:
        if item.item_id not in existing_inbox_ids:
            item_dict = {
                "item_id": item.item_id,
                "comm_type": item.comm_type,
                "raw_text": item.raw_text,
                "summary": item.summary,
                "project_id": item.project_id,
                "project_name": item.project_name,
                "sender": item.sender,
                "sender_email": item.sender_email,
                "source": item.source,
                "source_url": item.source_url,
                "subject": item.subject,
            }
            decision = detect_decision_from_inbox_item(item_dict)
            if decision:
                count += 1

    return count


def _extract_tags(text: str) -> list[str]:
    """Extract topic tags from decision text."""
    tags = []
    text_lower = text.lower()
    tag_keywords = {
        "material": ["material", "window", "concrete", "steel", "wood", "aluminum"],
        "design": ["design", "layout", "architectural", "facade", "lobby"],
        "MEP": ["hvac", "plumbing", "electrical", "mechanical", "ductwork"],
        "schedule": ["schedule", "timeline", "deadline", "delay"],
        "budget": ["budget", "cost", "pricing", "quote", "expense"],
        "safety": ["safety", "harness", "guardrail", "osha", "fall protection"],
        "vendor": ["vendor", "supplier", "contractor", "subcontractor"],
        "permit": ["permit", "code", "compliance", "inspection"],
    }
    for tag, keywords in tag_keywords.items():
        if any(kw in text_lower for kw in keywords):
            tags.append(tag)
    return tags
