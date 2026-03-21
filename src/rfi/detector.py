"""
RFI detector — identifies RFI-type questions from inbox communications.

Scans inbox items classified as 'question' or containing spec/compliance
language and creates RFI records in the RFI store.
"""
import logging
from typing import Optional

from src.rfi.models import RFI
from src.rfi.store import rfi_store

logger = logging.getLogger(__name__)

# Keywords that indicate an RFI-type question
_RFI_KEYWORDS = [
    "rfi", "request for information", "clarify", "clarification",
    "specification", "spec ", "comply", "compliance", "code requirement",
    "confirm", "confirmation", "which option", "what grade", "what rating",
    "fire rating", "fire resistance", "load bearing", "structural",
    "submittal", "shop drawing", "product data", "material",
    "astm", "ansi", "iso class", "leed", "osha",
]

# Categories based on content
_CATEGORY_KEYWORDS = {
    "structural": ["structural", "load", "bearing", "foundation", "concrete", "steel", "seismic"],
    "fire-protection": ["fire", "rating", "sprinkler", "smoke", "egress", "fire resistance"],
    "architectural": ["finish", "cladding", "facade", "window", "door", "flooring", "ceiling"],
    "MEP": ["hvac", "plumbing", "electrical", "mechanical", "ductwork", "piping", "transformer"],
    "environmental": ["asbestos", "lead", "environmental", "contamination", "remediation"],
    "code-compliance": ["code", "osha", "ada", "building code", "ibc", "nfpa", "astm"],
    "materials": ["material", "submittal", "product", "supplier", "grade", "specification"],
}


def detect_rfi_from_inbox_item(item: dict) -> Optional[RFI]:
    """
    Check if an inbox item contains an RFI-type question.
    Returns an RFI if detected, None otherwise.
    """
    # Only process questions, action-items, and escalations
    if item.get("comm_type") not in ("question", "action-item", "escalation"):
        return None

    text = (item.get("raw_text", "") + " " + item.get("summary", "")).lower()

    # Check for RFI indicators
    is_rfi = False
    for keyword in _RFI_KEYWORDS:
        if keyword in text:
            is_rfi = True
            break

    # Also detect questions with "?" that relate to specs/materials
    if not is_rfi and "?" in item.get("raw_text", ""):
        for keyword in ["which", "what", "should we", "can we", "is it"]:
            if keyword in text:
                is_rfi = True
                break

    if not is_rfi:
        return None

    # Determine category
    category = _detect_category(text)

    # Extract assignee from action items if available
    assignee = None
    assignee_email = None
    for ai in item.get("action_items", []):
        if any(w in ai.get("description", "").lower() for w in ["review", "confirm", "respond", "clarify"]):
            assignee = ai.get("assignee")
            break

    rfi = RFI(
        inbox_item_id=item.get("item_id"),
        project_id=item.get("project_id"),
        project_name=item.get("project_name"),
        title=_extract_title(item),
        question=item.get("raw_text", item.get("summary", "")),
        category=category,
        priority=_urgency_to_priority(item.get("urgency", 3)),
        assignee=assignee,
        requester=item.get("sender", "Unknown"),
        requester_email=item.get("sender_email"),
        source="auto-detected",
    )

    rfi_store.add(rfi)
    logger.info("RFI detected: %s — %s", rfi.rfi_id, rfi.title)
    return rfi


def scan_inbox_for_rfis() -> int:
    """Scan all inbox items and create RFIs for detected questions. Returns count."""
    from src.inbox.store import inbox_store
    items, _ = inbox_store.list_items(limit=10000)
    count = 0
    existing_inbox_ids = {r.inbox_item_id for r in rfi_store._items if r.inbox_item_id}

    for item in items:
        item_dict = {
            "item_id": item.item_id,
            "comm_type": item.comm_type,
            "raw_text": item.raw_text,
            "summary": item.summary,
            "project_id": item.project_id,
            "project_name": item.project_name,
            "sender": item.sender,
            "sender_email": item.sender_email,
            "urgency": item.urgency,
            "action_items": [
                {"assignee": ai.assignee, "description": ai.description}
                for ai in item.action_items
            ],
        }
        if item.item_id not in existing_inbox_ids:
            rfi = detect_rfi_from_inbox_item(item_dict)
            if rfi:
                count += 1

    return count


def _detect_category(text: str) -> str:
    """Detect RFI category based on content keywords."""
    for category, keywords in _CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return category
    return "general"


def _extract_title(item: dict) -> str:
    """Generate a concise RFI title from the inbox item."""
    subject = item.get("subject", "")
    if subject and len(subject) > 10:
        return subject[:100]
    summary = item.get("summary", "")
    if summary:
        return summary[:100]
    return "Untitled RFI"


def _urgency_to_priority(urgency: int) -> str:
    if urgency >= 5:
        return "critical"
    elif urgency >= 4:
        return "high"
    elif urgency >= 3:
        return "medium"
    return "low"
