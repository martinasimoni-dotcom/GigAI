"""
AI communication classifier using Claude Haiku 4.5.

Processes raw communications into structured InboxItems by:
1. Classifying communication type (decision, action-item, FYI, question, escalation)
2. Scoring urgency (1-5)
3. Extracting action items with assignees, deadlines, priorities
4. Routing to the correct project based on content analysis
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from src.inbox.models import ActionItem, InboxItem

logger = logging.getLogger(__name__)

_CLASSIFICATION_PROMPT = """You are an AI assistant for construction project management. Analyze this communication and extract structured data.

Communication source: {source}
Subject: {subject}
Sender: {sender}

--- COMMUNICATION ---
{text}
--- END ---

Known projects (match by content — use project_id and project_name if the communication relates to one):
{projects_context}

Respond with ONLY valid JSON matching this schema:
{{
  "comm_type": "decision" | "action-item" | "FYI" | "question" | "escalation",
  "urgency": 1-5 (1=informational, 2=low, 3=normal, 4=high, 5=critical),
  "summary": "One-sentence summary of the communication",
  "project_id": "PRJ-XXX or null if no project match",
  "project_name": "Project name or null",
  "action_items": [
    {{
      "assignee": "Person name",
      "deadline": "YYYY-MM-DD or null",
      "priority": "low" | "medium" | "high",
      "description": "What needs to be done"
    }}
  ]
}}

Classification rules:
- "decision": A decision has been made or announced
- "action-item": Someone needs to do something specific
- "question": A question that needs answering (including RFIs)
- "escalation": Urgent issue requiring immediate attention
- "FYI": Informational update, no action required

Urgency rules:
- 5 (critical): Safety issue, work stoppage, deadline today, budget overrun
- 4 (high): Deadline this week, blocking other work, client escalation
- 3 (normal): Standard coordination, routine updates with action needed
- 2 (low): Non-urgent updates, planning for future work
- 1 (informational): FYI, meeting notes, general updates"""


def classify_communication(
    text: str,
    source: str,
    sender: str,
    sender_email: Optional[str] = None,
    subject: Optional[str] = None,
    source_url: Optional[str] = None,
) -> InboxItem:
    """
    Classify a raw communication using Haiku and return a populated InboxItem.

    Uses Claude Haiku 4.5 for fast classification. Falls back to a basic
    heuristic classification if the LLM call fails.
    """
    # Build project context for routing
    projects_context = _get_projects_context()

    prompt = _CLASSIFICATION_PROMPT.format(
        source=source,
        subject=subject or "(no subject)",
        sender=sender,
        text=text[:3000],  # Truncate for token efficiency
        projects_context=projects_context,
    )

    try:
        from src.shared.llm.claude import call_haiku
        response = call_haiku(
            prompt=prompt,
            system="You are a construction project communication classifier. Respond with valid JSON only.",
        )

        # Parse the JSON response
        if isinstance(response, str):
            parsed = json.loads(response)
        elif isinstance(response, dict):
            parsed = response
        else:
            parsed = json.loads(str(response))

        # Build action items
        action_items = []
        for ai_data in parsed.get("action_items", []):
            deadline = None
            if ai_data.get("deadline"):
                try:
                    deadline = datetime.fromisoformat(ai_data["deadline"])
                except (ValueError, TypeError):
                    pass
            action_items.append(ActionItem(
                assignee=ai_data.get("assignee", "Unassigned"),
                deadline=deadline,
                priority=ai_data.get("priority", "medium"),
                description=ai_data.get("description", ""),
            ))

        return InboxItem(
            source=source,
            comm_type=parsed.get("comm_type", "FYI"),
            urgency=max(1, min(5, parsed.get("urgency", 3))),
            summary=parsed.get("summary", text[:100]),
            raw_text=text,
            project_id=parsed.get("project_id"),
            project_name=parsed.get("project_name"),
            sender=sender,
            sender_email=sender_email,
            subject=subject,
            source_url=source_url,
            action_items=action_items,
            classified_at=datetime.now(timezone.utc),
        )

    except Exception as exc:
        logger.warning("Haiku classification failed (%s), using fallback", exc)
        return _fallback_classify(text, source, sender, sender_email, subject, source_url)


def _fallback_classify(
    text: str,
    source: str,
    sender: str,
    sender_email: Optional[str],
    subject: Optional[str],
    source_url: Optional[str],
) -> InboxItem:
    """Basic heuristic classification when LLM is unavailable."""
    text_lower = text.lower()

    # Simple heuristic classification
    if any(w in text_lower for w in ["urgent", "immediately", "asap", "critical", "safety"]):
        comm_type = "escalation"
        urgency = 5
    elif "?" in text or any(w in text_lower for w in ["question", "rfi", "clarify", "confirm"]):
        comm_type = "question"
        urgency = 3
    elif any(w in text_lower for w in ["decided", "approved", "confirmed", "agreed"]):
        comm_type = "decision"
        urgency = 3
    elif any(w in text_lower for w in ["action", "please", "need to", "must", "deadline"]):
        comm_type = "action-item"
        urgency = 3
    else:
        comm_type = "FYI"
        urgency = 2

    return InboxItem(
        source=source,
        comm_type=comm_type,
        urgency=urgency,
        summary=text[:120].replace("\n", " ").strip(),
        raw_text=text,
        sender=sender,
        sender_email=sender_email,
        subject=subject,
        source_url=source_url,
        classified_at=datetime.now(timezone.utc),
    )


def _get_projects_context() -> str:
    """Build a compact project list for LLM routing."""
    try:
        from src.data.projects import PROJECTS
        lines = []
        for p in PROJECTS[:15]:  # Top 15 for token efficiency
            lines.append(f"- {p['project_id']}: {p['name']} ({p['city']}, {p['category']})")
        return "\n".join(lines)
    except Exception:
        return "(project list unavailable)"
