"""
Stakeholder communication graph.

Models the relationships between people, projects, roles, and
communication preferences. When a change occurs, identifies the
full notification chain and drafts personalized messages.
"""
import logging
from typing import Optional

from src.data.employees import EMPLOYEES
from src.data.projects import PROJECTS

logger = logging.getLogger(__name__)


class StakeholderGraph:
    """In-memory stakeholder relationship graph."""

    def __init__(self) -> None:
        self._nodes: list[dict] = []
        self._edges: list[dict] = []
        self._build_from_data()

    def _build_from_data(self) -> None:
        """Build graph from existing employee and project data."""
        # Add employee nodes
        for emp in EMPLOYEES:
            self._nodes.append({
                "id": emp["employee_id"],
                "name": emp["name"],
                "role": emp["profession"],
                "title": emp["title"],
                "email": emp["email"],
                "company": emp["company"],
                "department": emp["department"],
                "projects": emp["current_projects"],
                "type": "person",
            })

        # Add project nodes
        for proj in PROJECTS:
            self._nodes.append({
                "id": proj["project_id"],
                "name": proj["name"],
                "type": "project",
                "category": proj["category"],
                "status": proj["status"],
            })

        # Build edges (person -> project assignments)
        for emp in EMPLOYEES:
            for proj_id in emp["current_projects"]:
                self._edges.append({
                    "from": emp["employee_id"],
                    "to": proj_id,
                    "relationship": "assigned_to",
                    "role": emp["profession"],
                })

    def get_stakeholders_for_project(self, project_id: str) -> list[dict]:
        """Get all stakeholders assigned to a project."""
        assigned_ids = {e["from"] for e in self._edges if e["to"] == project_id}
        return [n for n in self._nodes if n["id"] in assigned_ids]

    def get_notification_chain(self, project_id: str, change_type: str = "material") -> list[dict]:
        """
        Determine who needs to be notified about a change, in priority order.

        Returns stakeholders with their notification priority and reason.
        """
        stakeholders = self.get_stakeholders_for_project(project_id)
        if not stakeholders:
            # Fallback: return employees from project's PM/Super
            project = next((p for p in PROJECTS if p["project_id"] == project_id), None)
            if project:
                pm_name = project.get("project_manager", "")
                super_name = project.get("superintendent", "")
                for emp in EMPLOYEES:
                    if emp["name"] in (pm_name, super_name):
                        stakeholders.append({
                            "id": emp["employee_id"],
                            "name": emp["name"],
                            "role": emp["profession"],
                            "title": emp["title"],
                            "email": emp["email"],
                            "type": "person",
                        })

        # Define notification priority based on role and change type
        priority_rules = _get_priority_rules(change_type)

        chain = []
        for s in stakeholders:
            role = s.get("role", "").lower()
            priority = 3  # default medium
            reason = "General project stakeholder"

            for rule in priority_rules:
                if rule["role_match"] in role:
                    priority = rule["priority"]
                    reason = rule["reason"]
                    break

            chain.append({
                **s,
                "notification_priority": priority,
                "notification_reason": reason,
                "info_needs": _get_info_needs(s.get("role", ""), change_type),
            })

        chain.sort(key=lambda x: x["notification_priority"])
        return chain

    def get_graph_data(self) -> dict:
        """Return the full graph for visualization."""
        return {
            "nodes": self._nodes,
            "edges": self._edges,
            "person_count": sum(1 for n in self._nodes if n["type"] == "person"),
            "project_count": sum(1 for n in self._nodes if n["type"] == "project"),
            "edge_count": len(self._edges),
        }

    def get_recent_interactions(self, person_id: str, limit: int = 10) -> list[dict]:
        """Get recent communications involving a person (from inbox)."""
        try:
            from src.inbox.store import inbox_store
            items, _ = inbox_store.list_items(limit=10000)
            person_node = next((n for n in self._nodes if n["id"] == person_id), None)
            if not person_node:
                return []
            name = person_node["name"].lower()
            relevant = [
                {
                    "item_id": i.item_id,
                    "summary": i.summary,
                    "source": i.source,
                    "comm_type": i.comm_type,
                    "received_at": i.received_at.isoformat(),
                }
                for i in items
                if name in i.sender.lower() or name in i.raw_text.lower()
            ]
            return relevant[:limit]
        except Exception:
            return []


def _get_priority_rules(change_type: str) -> list[dict]:
    """Priority rules based on change type."""
    rules = {
        "material": [
            {"role_match": "project manager", "priority": 1, "reason": "PM must approve all material changes"},
            {"role_match": "architect", "priority": 1, "reason": "Architect reviews design impact"},
            {"role_match": "structural engineer", "priority": 2, "reason": "Engineer assesses load implications"},
            {"role_match": "procurement", "priority": 2, "reason": "Procurement handles supplier coordination"},
            {"role_match": "superintendent", "priority": 3, "reason": "Super coordinates field installation"},
            {"role_match": "estimator", "priority": 3, "reason": "Estimator reviews cost impact"},
        ],
        "schedule": [
            {"role_match": "project manager", "priority": 1, "reason": "PM owns the master schedule"},
            {"role_match": "superintendent", "priority": 1, "reason": "Super coordinates field work"},
            {"role_match": "procurement", "priority": 2, "reason": "Procurement adjusts delivery dates"},
        ],
        "safety": [
            {"role_match": "superintendent", "priority": 1, "reason": "Super is responsible for site safety"},
            {"role_match": "project manager", "priority": 1, "reason": "PM must be informed of all safety issues"},
        ],
        "budget": [
            {"role_match": "project manager", "priority": 1, "reason": "PM controls project budget"},
            {"role_match": "estimator", "priority": 1, "reason": "Estimator validates cost projections"},
            {"role_match": "procurement", "priority": 2, "reason": "Procurement negotiates pricing"},
        ],
    }
    return rules.get(change_type, rules["material"])


def _get_info_needs(role: str, change_type: str) -> str:
    """What information each role needs about a change."""
    role_lower = role.lower()
    needs = {
        "project manager": "Full change summary: scope, cost impact, schedule impact, required approvals",
        "architect": "Design implications: specification changes, drawing updates, aesthetic impact",
        "structural engineer": "Structural analysis: load calculations, material properties, code compliance",
        "procurement officer": "Procurement impact: supplier quotes, lead times, PO modifications",
        "site superintendent": "Field coordination: crew scheduling, material staging, installation sequence",
        "estimator": "Cost analysis: material costs, labor impact, contingency adjustment",
    }
    for key, value in needs.items():
        if key in role_lower:
            return value
    return "Change notification: summary and any required actions"


def draft_stakeholder_messages(
    project_id: str,
    change_summary: str,
    change_type: str = "material",
) -> list[dict]:
    """
    Draft personalized notification messages for each stakeholder.

    Returns list of {stakeholder, message, priority} dicts ready for PM review.
    """
    graph = stakeholder_graph
    chain = graph.get_notification_chain(project_id, change_type)

    messages = []
    for stakeholder in chain:
        info_needs = stakeholder.get("info_needs", "")
        name = stakeholder.get("name", "Stakeholder")
        role = stakeholder.get("role", "Team Member")

        message = (
            f"Hi {name},\n\n"
            f"This is to inform you of a {change_type} change on the project.\n\n"
            f"Summary: {change_summary}\n\n"
            f"As {role}, here's what you need to know:\n"
            f"{info_needs}\n\n"
            f"Please review and confirm any required actions on your end.\n\n"
            f"Best regards,\nGigAI Coordination System"
        )

        messages.append({
            "stakeholder_id": stakeholder["id"],
            "stakeholder_name": name,
            "stakeholder_role": role,
            "stakeholder_email": stakeholder.get("email"),
            "notification_priority": stakeholder["notification_priority"],
            "notification_reason": stakeholder["notification_reason"],
            "message": message,
            "status": "draft",
        })

    return messages


# Module-level singleton
stakeholder_graph = StakeholderGraph()
