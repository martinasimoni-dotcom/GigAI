"""
Mock ACC client — returns realistic data matching real ACC API response shapes.

Used as automatic fallback when real ACC credentials are missing or API calls fail.
Mirrors every public function in acc.py with identical signatures and return shapes.
"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Demo project constants
# ---------------------------------------------------------------------------
DEMO_PROJECT_ID = "b.demo-harbor-view-tower"
DEMO_ACCOUNT_ID = "demo-account-001"
DEMO_CONTAINER_ID = "demo-issues-container-001"

DEMO_TEAM = [
    {"userId": "user-001", "name": "Sarah Chen", "email": "s.chen@apexconstruction.com", "role": "Project Manager", "company": "Apex Construction"},
    {"userId": "user-002", "name": "Mike Torres", "email": "m.torres@apexconstruction.com", "role": "Procurement Officer", "company": "Apex Construction"},
    {"userId": "user-003", "name": "James Park", "email": "j.park@parkstudioarch.com", "role": "Lead Architect", "company": "Park Studio Architecture"},
    {"userId": "user-004", "name": "Lisa Wong", "email": "l.wong@structuralfocus.com", "role": "Structural Engineer", "company": "Structural Focus Inc."},
    {"userId": "user-005", "name": "Carlos Rivera", "email": "c.rivera@apexconstruction.com", "role": "Site Superintendent", "company": "Apex Construction"},
    {"userId": "user-006", "name": "Jane Miller", "email": "j.miller@premiumwoodco.com", "role": "Supplier Contact", "company": "Premium Wood Co."},
    {"userId": "user-007", "name": "Robert Hayes", "email": "r.hayes@harbordevelopment.com", "role": "Owner Representative", "company": "Harbor Development LLC"},
]


def _today() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")

def _future(days: int) -> str:
    return (datetime.utcnow() + timedelta(days=days)).strftime("%Y-%m-%d")


# ═══ Account Admin ══════════════════════════════════════════════════════════

def get_projects() -> list[dict]:
    return [{"id": DEMO_PROJECT_ID, "name": "Harbor View Tower", "status": "active", "type": "residential", "startDate": "2025-06-15", "endDate": "2027-03-01", "value": 42500000}]

def get_project_details(project_id: str | None = None) -> dict:
    return {"id": DEMO_PROJECT_ID, "name": "Harbor View Tower", "status": "active", "type": "residential", "startDate": "2025-06-15", "endDate": "2027-03-01", "value": 42500000, "addressLine1": "Waterfront District, Barcelona", "currency": "USD"}

def get_project_users(project_id: str | None = None) -> list[dict]:
    return list(DEMO_TEAM)

def get_companies() -> list[dict]:
    return [
        {"id": "co-001", "name": "Apex Construction", "trade": "General Contractor"},
        {"id": "co-002", "name": "Park Studio Architecture", "trade": "Architect"},
        {"id": "co-003", "name": "Structural Focus Inc.", "trade": "Structural Engineer"},
        {"id": "co-004", "name": "Premium Wood Co.", "trade": "Material Supplier"},
        {"id": "co-005", "name": "Harbor Development LLC", "trade": "Owner"},
    ]

def get_account_users() -> list[dict]:
    return list(DEMO_TEAM)


# ═══ Cost Management ════════════════════════════════════════════════════════

def get_budgets(project_id: str | None = None) -> list[dict]:
    return [
        {"id": "bgt-001", "code": "03000", "name": "Concrete", "originalAmount": 4200000, "revisedAmount": 4350000, "committedAmount": 3800000, "actualAmount": 3200000, "status": "active"},
        {"id": "bgt-002", "code": "05000", "name": "Structural Steel", "originalAmount": 6800000, "revisedAmount": 6800000, "committedAmount": 5900000, "actualAmount": 4100000, "status": "active"},
        {"id": "bgt-003", "code": "08000", "name": "Openings (Windows/Doors)", "originalAmount": 3200000, "revisedAmount": 3210200, "committedAmount": 2800000, "actualAmount": 1900000, "status": "active"},
        {"id": "bgt-004", "code": "09000", "name": "Finishes", "originalAmount": 5100000, "revisedAmount": 5100000, "committedAmount": 2400000, "actualAmount": 800000, "status": "active"},
        {"id": "bgt-005", "code": "15000", "name": "Mechanical (HVAC/Plumbing)", "originalAmount": 7200000, "revisedAmount": 7200000, "committedAmount": 4100000, "actualAmount": 2200000, "status": "active"},
        {"id": "bgt-006", "code": "16000", "name": "Electrical", "originalAmount": 4800000, "revisedAmount": 4800000, "committedAmount": 3200000, "actualAmount": 1500000, "status": "active"},
        {"id": "bgt-007", "code": "14000", "name": "Elevators", "originalAmount": 2800000, "revisedAmount": 2800000, "committedAmount": 2800000, "actualAmount": 560000, "status": "active"},
        {"id": "bgt-008", "code": "02000", "name": "Site Work", "originalAmount": 1900000, "revisedAmount": 1900000, "committedAmount": 1900000, "actualAmount": 1800000, "status": "active"},
        {"id": "bgt-009", "code": "01000", "name": "General Conditions", "originalAmount": 3500000, "revisedAmount": 3500000, "committedAmount": 3500000, "actualAmount": 2100000, "status": "active"},
        {"id": "bgt-010", "code": "99000", "name": "Contingency", "originalAmount": 3000000, "revisedAmount": 2850000, "committedAmount": 0, "actualAmount": 150000, "status": "active"},
    ]

def get_contracts(project_id: str | None = None) -> list[dict]:
    return [
        {"id": "ctr-001", "name": "Concrete Subcontract — Bay Concrete", "type": "subcontract", "originalAmount": 3800000, "revisedAmount": 3950000, "status": "executed"},
        {"id": "ctr-002", "name": "Steel Erection — Pacific Steel", "type": "subcontract", "originalAmount": 5900000, "revisedAmount": 5900000, "status": "executed"},
        {"id": "ctr-003", "name": "Window Supply — Premium Wood Co.", "type": "purchase_order", "originalAmount": 10200, "revisedAmount": 10200, "status": "pending"},
        {"id": "ctr-004", "name": "HVAC — ClimaTech Systems", "type": "subcontract", "originalAmount": 4100000, "revisedAmount": 4100000, "status": "executed"},
        {"id": "ctr-005", "name": "Electrical — Volt Contractors", "type": "subcontract", "originalAmount": 3200000, "revisedAmount": 3200000, "status": "executed"},
    ]

def get_change_orders(project_id: str | None = None) -> list[dict]:
    return [
        {"id": "co-001", "number": "CO-001", "title": "3rd Floor Window Material Substitution (Aluminum → Wood)", "amount": 2400, "status": "pending", "createdDate": _today(), "description": "12 units × $200 premium for wood over aluminum"},
        {"id": "co-002", "number": "CO-002", "title": "Additional Concrete Testing — Tower B Level 3", "amount": 8500, "status": "approved", "createdDate": _future(-14), "description": "Core extraction and lab testing per ACI 318"},
        {"id": "co-003", "number": "CO-003", "title": "Lobby Marble Upgrade — Italian Import", "amount": 180000, "status": "approved", "createdDate": _future(-7), "description": "Client-approved upgrade from domestic to Italian marble"},
    ]

def get_cost_items(project_id: str | None = None) -> list[dict]:
    return [
        {"id": "ci-001", "description": "Concrete pour — Foundation", "amount": 850000, "category": "03000", "date": _future(-90)},
        {"id": "ci-002", "description": "Steel delivery — Floors 1-5", "amount": 2100000, "category": "05000", "date": _future(-60)},
        {"id": "ci-003", "description": "Window rough openings — 3rd Floor", "amount": 45000, "category": "08000", "date": _future(-10)},
    ]


# ═══ Issues ══════════════════════════════════════════════════════════════════

_created_issues: list[dict] = []

def get_issues(project_id: str | None = None, container_id: str | None = None) -> list[dict]:
    base = [
        {"id": "iss-001", "title": "Window frame spec update needed — A-301", "status": "open", "assignedTo": "user-003", "priority": "high", "createdDate": _today()},
        {"id": "iss-002", "title": "Structural weight assessment — wood frames", "status": "open", "assignedTo": "user-004", "priority": "high", "createdDate": _today()},
        {"id": "iss-003", "title": "Missing guardrails — 5th floor east", "status": "closed", "assignedTo": "user-005", "priority": "critical", "createdDate": _future(-2)},
    ]
    return base + list(_created_issues)

def create_issue(project_id, container_id, title, description, assignee_id=None, issue_type="task", due_date=None):
    issue_id = f"mock-issue-{uuid.uuid4().hex[:8]}"
    issue = {"id": issue_id, "containerId": container_id, "title": title, "description": description, "status": "open", "issueType": issue_type, "assignedTo": assignee_id, "dueDate": due_date or _future(14), "createdAt": datetime.utcnow().isoformat() + "Z", "projectId": project_id}
    _created_issues.append(issue)
    logger.info("[MOCK ACC] Issue created: id=%s title=%s", issue_id, title)
    return issue


# ═══ RFIs ════════════════════════════════════════════════════════════════════

def get_rfis(project_id: str | None = None, container_id: str | None = None) -> list[dict]:
    return [
        {"id": "rfi-001", "number": "RFI-0034", "title": "Fire rating — corridor partition walls floors 2-5", "status": "closed", "assignedTo": "user-003", "dueDate": _future(-5), "answeredDate": _future(-3)},
        {"id": "rfi-002", "number": "RFI-0035", "title": "Cladding finish grade — Grade A vs B", "status": "open", "assignedTo": "user-003", "dueDate": _future(7)},
    ]


# ═══ Submittals ══════════════════════════════════════════════════════════════

def get_submittals(project_id: str | None = None) -> list[dict]:
    return [
        {"id": "sub-001", "number": "SUB-0089", "title": "Exterior cladding panels — finish grade", "status": "pending", "specSection": "074600"},
        {"id": "sub-002", "number": "SUB-0090", "title": "Wood window frames — FSC certification", "status": "submitted", "specSection": "061000"},
        {"id": "sub-003", "number": "SUB-0091", "title": "HVAC VRF system — Daikin equipment data", "status": "approved", "specSection": "238100"},
    ]


# ═══ Documents ═══════════════════════════════════════════════════════════════

def get_top_folders(project_id: str | None = None) -> list[dict]:
    return [
        {"id": "fld-001", "name": "Project Files", "type": "folder"},
        {"id": "fld-002", "name": "Drawings", "type": "folder"},
        {"id": "fld-003", "name": "Specifications", "type": "folder"},
        {"id": "fld-004", "name": "Photos", "type": "folder"},
        {"id": "fld-005", "name": "Submittals", "type": "folder"},
    ]

def get_folder_contents(project_id: str, folder_id: str) -> list[dict]:
    return [{"id": "doc-001", "name": "Drawing A-301 Rev C.pdf", "type": "file", "lastModified": _today()}]


# ═══ Locations ═══════════════════════════════════════════════════════════════

_LOCATION_TREE = {
    "treeId": "tree-001",
    "nodes": [
        {"id": "loc-001", "name": "1st Floor", "type": "Floor", "parentId": None, "description": "Ground floor — lobby, retail spaces, mechanical room"},
        {"id": "loc-002", "name": "2nd Floor", "type": "Floor", "parentId": None, "description": "Residential units 201-224"},
        {"id": "loc-003", "name": "3rd Floor", "type": "Floor", "parentId": None, "description": "Residential units 301-324"},
        {"id": "loc-003a", "name": "3rd Floor — Zone A (North)", "type": "Zone", "parentId": "loc-003", "description": "Units 301-306, 6 window openings (W-301 to W-306)"},
        {"id": "loc-003b", "name": "3rd Floor — Zone B (South)", "type": "Zone", "parentId": "loc-003", "description": "Units 307-312, 6 window openings (W-307 to W-312)"},
        {"id": "loc-004", "name": "4th Floor", "type": "Floor", "parentId": None, "description": "Residential units 401-424"},
        {"id": "loc-005", "name": "5th Floor", "type": "Floor", "parentId": None, "description": "Penthouse units 501-508"},
        {"id": "loc-006", "name": "Roof", "type": "Floor", "parentId": None, "description": "Mechanical penthouse, terrace, solar array"},
    ],
}

def get_floor_plan(project_id: str, location_query: str | None = None) -> dict:
    nodes = list(_LOCATION_TREE["nodes"])
    if location_query:
        q = location_query.lower()
        nodes = [n for n in nodes if q in n["name"].lower() or q in n.get("description", "").lower()]
    return {"project_id": project_id, "tree_id": _LOCATION_TREE["treeId"], "nodes": nodes, "source": "mock_acc"}


# ═══ Schedule ════════════════════════════════════════════════════════════════

_SCHEDULE_ACTIVITIES = [
    {"activity": "Window rough openings — 3rd Floor", "date": _future(5), "end_date": _future(12), "location": "3rd Floor", "status": "in_progress", "discipline": "Structural"},
    {"activity": "Window frame installation — 3rd Floor", "date": _future(14), "end_date": _future(21), "location": "3rd Floor", "status": "not_started", "discipline": "Glazing"},
    {"activity": "Window glazing — 3rd Floor", "date": _future(22), "end_date": _future(28), "location": "3rd Floor", "status": "not_started", "discipline": "Glazing"},
    {"activity": "Interior drywall — 3rd Floor", "date": _future(30), "end_date": _future(40), "location": "3rd Floor", "status": "not_started", "discipline": "Interior"},
    {"activity": "Exterior cladding — 3rd Floor", "date": _future(25), "end_date": _future(35), "location": "3rd Floor", "status": "not_started", "discipline": "Exterior"},
    {"activity": "MEP rough-in — 3rd Floor", "date": _future(8), "end_date": _future(20), "location": "3rd Floor", "status": "in_progress", "discipline": "MEP"},
]

def get_schedule_activities(project_id: str) -> list[dict]:
    return list(_SCHEDULE_ACTIVITIES)


# ═══ Forms / Checklists ══════════════════════════════════════════════════════

def get_checklists(project_id: str | None = None) -> list[dict]:
    return [
        {"id": "chk-001", "title": "Daily Safety Inspection", "status": "complete", "completedDate": _today(), "inspector": "Carlos Rivera"},
        {"id": "chk-002", "title": "Concrete Pre-Pour Checklist", "status": "complete", "completedDate": _future(-3), "inspector": "Carlos Rivera"},
        {"id": "chk-003", "title": "Window Opening Inspection — 3rd Floor", "status": "pending", "inspector": "Carlos Rivera"},
    ]


# ═══ Photos ══════════════════════════════════════════════════════════════════

def get_photos(project_id: str | None = None) -> list[dict]:
    return [
        {"id": "pht-001", "title": "3rd Floor Window Openings", "date": _today(), "location": "3rd Floor Zone A", "photographer": "Carlos Rivera"},
        {"id": "pht-002", "title": "Steel Erection Progress — Floor 8", "date": _future(-1), "location": "8th Floor", "photographer": "Carlos Rivera"},
        {"id": "pht-003", "title": "Curtain Wall Installation — Floor 2", "date": _future(-3), "location": "2nd Floor", "photographer": "Carlos Rivera"},
    ]


# ═══ Daily Logs ══════════════════════════════════════════════════════════════

def get_daily_logs(project_id: str | None = None, log_date: str | None = None) -> list[dict]:
    return [
        {"id": "dl-001", "date": _today(), "weather": {"condition": "Partly Cloudy", "tempHigh": 72, "tempLow": 58, "windSpeed": 12}, "manpower": {"total": 85, "trades": {"concrete": 12, "steel": 18, "glazing": 8, "MEP": 15, "electrical": 10, "interior": 8, "laborers": 14}}, "equipment": ["Tower Crane #1", "Concrete Pump", "Material Hoist"], "notes": "Window rough openings progressing on 3rd floor. Steel erection on floors 6-8. No safety incidents."},
        {"id": "dl-002", "date": _future(-1), "weather": {"condition": "Sunny", "tempHigh": 75, "tempLow": 60, "windSpeed": 8}, "manpower": {"total": 82, "trades": {"concrete": 10, "steel": 20, "glazing": 6, "MEP": 14, "electrical": 10, "interior": 8, "laborers": 14}}, "equipment": ["Tower Crane #1", "Concrete Pump"], "notes": "Steel erection completed floor 7. Concrete cure test passed on floor 3."},
    ]


# ═══ Drawing Markup ══════════════════════════════════════════════════════════

_created_markups: list[dict] = []

def create_drawing_markup(project_id, version_urn, drawing_number, annotation_text, x=0.0, y=0.0):
    markup_id = f"mock-markup-{uuid.uuid4().hex[:8]}"
    markup = {"id": markup_id, "projectId": project_id, "drawingNumber": drawing_number, "text": annotation_text, "position": {"x": x, "y": y}, "createdAt": datetime.utcnow().isoformat() + "Z", "status": "active"}
    _created_markups.append(markup)
    logger.info("[MOCK ACC] Markup created on drawing %s", drawing_number)
    return markup


# ═══ Notifications ═══════════════════════════════════════════════════════════

_sent_notifications: list[dict] = []

def send_acc_notification(account_id, project_id, subject, body, recipient_ids):
    notif_id = f"mock-notif-{uuid.uuid4().hex[:8]}"
    notif = {"id": notif_id, "subject": subject, "body": body, "recipients": [{"userId": uid} for uid in recipient_ids], "sentAt": datetime.utcnow().isoformat() + "Z", "status": "delivered"}
    _sent_notifications.append(notif)
    return notif


# ═══ Comprehensive Pull ═════════════════════════════════════════════════════

def pull_all_project_data(project_id: str | None = None) -> dict:
    pid = project_id or DEMO_PROJECT_ID
    data = {
        "project_id": pid,
        "project_details": get_project_details(pid),
        "users": get_project_users(pid),
        "companies": get_companies(),
        "budgets": get_budgets(pid),
        "contracts": get_contracts(pid),
        "change_orders": get_change_orders(pid),
        "cost_items": get_cost_items(pid),
        "issues": get_issues(pid),
        "rfis": get_rfis(pid),
        "submittals": get_submittals(pid),
        "locations": get_floor_plan(pid),
        "schedule": get_schedule_activities(pid),
        "checklists": get_checklists(pid),
        "photos": get_photos(pid),
        "daily_logs": get_daily_logs(pid),
        "documents": get_top_folders(pid),
    }
    data["_summary"] = {k: len(v) if isinstance(v, list) else (1 if v else 0) for k, v in data.items() if k != "project_id"}
    return data


# ═══ Query helpers ═══════════════════════════════════════════════════════════

def get_created_issues() -> list[dict]:
    return list(_created_issues)

def get_created_markups() -> list[dict]:
    return list(_created_markups)

def get_sent_notifications() -> list[dict]:
    return list(_sent_notifications)

def get_team_directory() -> list[dict]:
    return list(DEMO_TEAM)
