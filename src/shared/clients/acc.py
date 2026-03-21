"""
Autodesk Construction Cloud (ACC) API client — comprehensive data extraction.

Pulls ALL available data from ACC to feed into GigAI's intelligence:
  - Account Admin: projects, users, companies
  - Project: details, members, roles
  - Issues: tasks, quality issues
  - RFIs: formal RFIs with responses
  - Cost Management: budgets, contracts, cost items, change orders
  - Documents: folders, files, versions
  - Locations: floor plans, zones
  - Schedule: activities, milestones
  - Forms/Checklists: inspection data
  - Photos: site photos
  - Daily Logs: weather, manpower, equipment, notes

All methods raise RuntimeError if required env vars are absent.
Token is cached in-process until expiry.
"""
import json
import logging
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-process token cache (thread-safe)
# ---------------------------------------------------------------------------
_token_cache: dict[str, Any] = {}
_token_lock = threading.Lock()


def _get_acc_token() -> str:
    """Acquire (or return cached) 2-legged OAuth token for ACC."""
    now = time.time()
    if _token_cache.get("access_token") and _token_cache.get("expires_at", 0) > now + 60:
        return _token_cache["access_token"]

    with _token_lock:
        now = time.time()
        if _token_cache.get("access_token") and _token_cache.get("expires_at", 0) > now + 60:
            return _token_cache["access_token"]

        client_id = os.getenv("ACC_CLIENT_ID")
        client_secret = os.getenv("ACC_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise RuntimeError("ACC_CLIENT_ID and ACC_CLIENT_SECRET must be set")

        import base64
        creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        body = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "scope": "data:read data:write account:read account:write",
        }).encode()
        req = urllib.request.Request(
            "https://developer.api.autodesk.com/authentication/v2/token",
            data=body,
            headers={
                "Authorization": f"Basic {creds}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())

        _token_cache["access_token"] = data["access_token"]
        _token_cache["expires_at"] = now + data.get("expires_in", 3600)
        logger.info("ACC OAuth token acquired, expires in %ds", data.get("expires_in", 3600))
        return _token_cache["access_token"]


def _acc_get(path: str, base: str = "https://developer.api.autodesk.com") -> Any:
    """GET request to ACC API, returns parsed JSON."""
    token = _get_acc_token()
    req = urllib.request.Request(
        f"{base}{path}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def _acc_post(path: str, payload: dict, base: str = "https://developer.api.autodesk.com") -> Any:
    """POST request to ACC API with JSON body."""
    token = _get_acc_token()
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{base}{path}",
        data=body,
        method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def _acc_patch(path: str, payload: dict, base: str = "https://developer.api.autodesk.com") -> Any:
    """PATCH request to ACC API."""
    token = _get_acc_token()
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{base}{path}",
        data=body,
        method="PATCH",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def _extract(resp: Any, *keys: str) -> list:
    """Extract results from ACC response — handles various response shapes."""
    for key in keys:
        if isinstance(resp, dict) and key in resp:
            val = resp[key]
            if isinstance(val, list):
                return val
    if isinstance(resp, list):
        return resp
    return []


def _account_id() -> str:
    aid = os.getenv("ACC_ACCOUNT_ID", "")
    if not aid:
        raise RuntimeError("ACC_ACCOUNT_ID must be set")
    return aid


def _project_id() -> str:
    pid = os.getenv("ACC_PROJECT_ID", "")
    if not pid:
        raise RuntimeError("ACC_PROJECT_ID must be set")
    return pid


# ═══════════════════════════════════════════════════════════════════════════
# ACCOUNT ADMIN — Projects, Users, Companies
# ═══════════════════════════════════════════════════════════════════════════

def get_projects() -> list[dict]:
    """Fetch all projects in the ACC account."""
    account_id = _account_id()
    resp = _acc_get(f"/construction/admin/v1/accounts/{account_id}/projects?limit=100")
    projects = _extract(resp, "results", "data")
    logger.info("ACC: fetched %d projects", len(projects))
    return projects


def get_project_details(project_id: str | None = None) -> dict:
    """Fetch full details for a specific project."""
    pid = project_id or _project_id()
    account_id = _account_id()
    return _acc_get(f"/construction/admin/v1/accounts/{account_id}/projects/{pid}")


def get_project_users(project_id: str | None = None) -> list[dict]:
    """Fetch all users assigned to a project — names, roles, companies, emails."""
    pid = project_id or _project_id()
    account_id = _account_id()
    resp = _acc_get(f"/construction/admin/v1/projects/{pid}/users?limit=100")
    users = _extract(resp, "results", "data")
    logger.info("ACC: fetched %d project users for %s", len(users), pid)
    return users


def get_companies() -> list[dict]:
    """Fetch all companies in the ACC account."""
    account_id = _account_id()
    resp = _acc_get(f"/construction/admin/v1/accounts/{account_id}/companies?limit=100")
    return _extract(resp, "results", "data")


def get_account_users() -> list[dict]:
    """Fetch all users across the ACC account."""
    account_id = _account_id()
    resp = _acc_get(f"/construction/admin/v1/accounts/{account_id}/users?limit=100")
    return _extract(resp, "results", "data")


# ═══════════════════════════════════════════════════════════════════════════
# COST MANAGEMENT — Budgets, Contracts, Change Orders, Cost Items
# ═══════════════════════════════════════════════════════════════════════════

def get_budgets(project_id: str | None = None) -> list[dict]:
    """Fetch budget line items for a project."""
    pid = project_id or _project_id()
    try:
        resp = _acc_get(f"/cost/v1/containers/{pid}/budgets?limit=100")
        budgets = _extract(resp, "results", "data")
        logger.info("ACC Cost: fetched %d budget items for %s", len(budgets), pid)
        return budgets
    except Exception as exc:
        logger.warning("ACC Cost API budgets failed: %s", exc)
        return []


def get_contracts(project_id: str | None = None) -> list[dict]:
    """Fetch contracts (commitments) for a project."""
    pid = project_id or _project_id()
    try:
        resp = _acc_get(f"/cost/v1/containers/{pid}/contracts?limit=100")
        return _extract(resp, "results", "data")
    except Exception as exc:
        logger.warning("ACC Cost API contracts failed: %s", exc)
        return []


def get_change_orders(project_id: str | None = None) -> list[dict]:
    """Fetch change orders for a project."""
    pid = project_id or _project_id()
    try:
        resp = _acc_get(f"/cost/v1/containers/{pid}/change-orders?limit=100")
        return _extract(resp, "results", "data")
    except Exception as exc:
        logger.warning("ACC Cost API change orders failed: %s", exc)
        return []


def get_cost_items(project_id: str | None = None) -> list[dict]:
    """Fetch cost items/expenses for a project."""
    pid = project_id or _project_id()
    try:
        resp = _acc_get(f"/cost/v1/containers/{pid}/cost-items?limit=100")
        return _extract(resp, "results", "data")
    except Exception as exc:
        logger.warning("ACC Cost API cost items failed: %s", exc)
        return []


# ═══════════════════════════════════════════════════════════════════════════
# ISSUES — Tasks, Quality Issues, all issue types
# ═══════════════════════════════════════════════════════════════════════════

def get_issues(project_id: str | None = None, container_id: str | None = None) -> list[dict]:
    """Fetch all issues for a project."""
    cid = container_id or os.getenv("ACC_ISSUES_CONTAINER_ID", "")
    if not cid:
        pid = project_id or _project_id()
        logger.warning("ACC_ISSUES_CONTAINER_ID not set — cannot fetch issues for %s", pid)
        return []
    try:
        resp = _acc_get(f"/issues/v1/containers/{cid}/quality-issues?limit=100")
        issues = _extract(resp, "results", "data")
        logger.info("ACC Issues: fetched %d issues", len(issues))
        return issues
    except Exception as exc:
        logger.warning("ACC Issues API failed: %s", exc)
        return []


def create_issue(
    project_id: str,
    container_id: str,
    title: str,
    description: str,
    assignee_id: str | None = None,
    issue_type: str = "task",
    due_date: str | None = None,
) -> dict:
    """Create an ACC issue (task / RFI / quality issue)."""
    payload: dict[str, Any] = {
        "title": title,
        "description": description,
        "status": "open",
    }
    if assignee_id:
        payload["assignedTo"] = assignee_id
    if due_date:
        payload["dueDate"] = due_date

    resp = _acc_post(f"/issues/v1/containers/{container_id}/quality-issues", payload)
    issue_id = (resp.get("data") or resp).get("id", "unknown")
    logger.info("ACC issue created: id=%s title=%s", issue_id, title)
    return resp.get("data") or resp


# ═══════════════════════════════════════════════════════════════════════════
# RFIs (formal ACC RFIs — separate from Issues)
# ═══════════════════════════════════════════════════════════════════════════

def get_rfis(project_id: str | None = None, container_id: str | None = None) -> list[dict]:
    """Fetch all RFIs for a project."""
    cid = container_id or os.getenv("ACC_ISSUES_CONTAINER_ID", "")
    if not cid:
        return []
    try:
        resp = _acc_get(f"/bim360/rfis/v2/containers/{cid}/rfis?limit=100")
        rfis = _extract(resp, "results", "data")
        logger.info("ACC RFIs: fetched %d RFIs", len(rfis))
        return rfis
    except Exception as exc:
        logger.warning("ACC RFIs API failed: %s", exc)
        return []


# ═══════════════════════════════════════════════════════════════════════════
# SUBMITTALS
# ═══════════════════════════════════════════════════════════════════════════

def get_submittals(project_id: str | None = None) -> list[dict]:
    """Fetch all submittals for a project."""
    pid = project_id or _project_id()
    try:
        resp = _acc_get(f"/construction/submittals/v2/projects/{pid}/items?limit=100")
        return _extract(resp, "results", "data")
    except Exception as exc:
        logger.warning("ACC Submittals API failed: %s", exc)
        return []


# ═══════════════════════════════════════════════════════════════════════════
# DOCUMENTS — Folders, Files, Versions
# ═══════════════════════════════════════════════════════════════════════════

def get_top_folders(project_id: str | None = None) -> list[dict]:
    """Fetch top-level document folders for a project."""
    pid = project_id or _project_id()
    try:
        # Data Management API — get hub then project then top folders
        resp = _acc_get(f"/project/v1/hubs/b.{_account_id()}/projects/b.{pid}/topFolders")
        return _extract(resp, "data")
    except Exception as exc:
        logger.warning("ACC Documents top folders failed: %s", exc)
        return []


def get_folder_contents(project_id: str, folder_id: str) -> list[dict]:
    """Fetch contents of a specific folder."""
    try:
        resp = _acc_get(f"/data/v1/projects/b.{project_id}/folders/{folder_id}/contents")
        return _extract(resp, "data")
    except Exception as exc:
        logger.warning("ACC Documents folder contents failed: %s", exc)
        return []


# ═══════════════════════════════════════════════════════════════════════════
# LOCATIONS — Floor Plans, Zones
# ═══════════════════════════════════════════════════════════════════════════

def get_floor_plan(project_id: str, location_query: str | None = None) -> dict:
    """Fetch location tree nodes for the project."""
    trees_resp = _acc_get(f"/bim360/locations/v2/containers/{project_id}/trees")
    trees = _extract(trees_resp, "results", "data")

    if not trees:
        logger.warning("ACC Locations API returned no trees for project %s", project_id)
        return {"project_id": project_id, "nodes": [], "source": "acc_api"}

    tree_id = trees[0].get("id") or trees[0].get("treeId")
    nodes_resp = _acc_get(f"/bim360/locations/v2/containers/{project_id}/trees/{tree_id}/nodes")
    nodes = _extract(nodes_resp, "results", "data")

    if location_query:
        q = location_query.lower()
        nodes = [n for n in nodes if q in (n.get("name") or "").lower()]

    return {"project_id": project_id, "tree_id": tree_id, "nodes": nodes, "source": "acc_api"}


# ═══════════════════════════════════════════════════════════════════════════
# SCHEDULE — Activities, Milestones
# ═══════════════════════════════════════════════════════════════════════════

def get_schedule_activities(project_id: str) -> list[dict]:
    """Fetch schedule activities from ACC."""
    try:
        resp = _acc_get(f"/construction/schedule/v1/projects/{project_id}/activities")
        activities = _extract(resp, "results", "data")
        return [
            {
                "activity": a.get("name") or a.get("title", ""),
                "date": a.get("startDate") or a.get("start_date", ""),
                "end_date": a.get("endDate") or a.get("end_date", ""),
                "location": a.get("location", ""),
                "status": a.get("status", ""),
                "discipline": a.get("discipline", ""),
            }
            for a in activities
        ]
    except Exception as exc:
        logger.warning("ACC Schedule API failed: %s", exc)
        return []


# ═══════════════════════════════════════════════════════════════════════════
# FORMS / CHECKLISTS — Inspections, Quality
# ═══════════════════════════════════════════════════════════════════════════

def get_checklists(project_id: str | None = None) -> list[dict]:
    """Fetch checklists/forms for a project."""
    pid = project_id or _project_id()
    try:
        resp = _acc_get(f"/bim360/checklists/v1/containers/{pid}/instances?limit=100")
        return _extract(resp, "results", "data")
    except Exception as exc:
        logger.warning("ACC Checklists API failed: %s", exc)
        return []


# ═══════════════════════════════════════════════════════════════════════════
# PHOTOS — Site documentation
# ═══════════════════════════════════════════════════════════════════════════

def get_photos(project_id: str | None = None) -> list[dict]:
    """Fetch site photos for a project."""
    pid = project_id or _project_id()
    try:
        resp = _acc_get(f"/construction/photos/v2/projects/{pid}/photos?limit=50")
        return _extract(resp, "results", "data")
    except Exception as exc:
        logger.warning("ACC Photos API failed: %s", exc)
        return []


# ═══════════════════════════════════════════════════════════════════════════
# DAILY LOG — Weather, Manpower, Equipment, Notes
# ═══════════════════════════════════════════════════════════════════════════

def get_daily_logs(project_id: str | None = None, log_date: str | None = None) -> list[dict]:
    """Fetch daily log entries for a project."""
    pid = project_id or _project_id()
    try:
        path = f"/construction/dailylogs/v2/projects/{pid}/logs?limit=50"
        if log_date:
            path += f"&filter[date]={log_date}"
        resp = _acc_get(path)
        return _extract(resp, "results", "data")
    except Exception as exc:
        logger.warning("ACC Daily Logs API failed: %s", exc)
        return []


# ═══════════════════════════════════════════════════════════════════════════
# DRAWING MARKUP — Annotations
# ═══════════════════════════════════════════════════════════════════════════

def create_drawing_markup(
    project_id: str,
    version_urn: str,
    drawing_number: str,
    annotation_text: str,
    x: float = 0.0,
    y: float = 0.0,
) -> dict:
    """Add a markup annotation to an ACC drawing."""
    payload = {
        "type": "markup",
        "attributes": {
            "text": annotation_text,
            "urnVersion": version_urn,
            "position": {"x": x, "y": y},
            "drawingNumber": drawing_number,
        },
    }
    resp = _acc_post(f"/bim360/docs/v1/projects/{project_id}/markups", payload)
    logger.info("ACC markup created on drawing %s", drawing_number)
    return resp.get("data") or resp


# ═══════════════════════════════════════════════════════════════════════════
# NOTIFICATIONS — In-app ACC notifications
# ═══════════════════════════════════════════════════════════════════════════

def send_acc_notification(
    account_id: str,
    project_id: str,
    subject: str,
    body: str,
    recipient_ids: list[str],
) -> dict:
    """Send an ACC in-app notification."""
    payload = {
        "subject": subject,
        "body": body,
        "projectId": project_id,
        "recipients": [{"userId": uid} for uid in recipient_ids],
    }
    resp = _acc_post(
        f"/construction/notifications/v1/accounts/{account_id}/notifications",
        payload,
    )
    logger.info("ACC notification sent: subject=%s recipients=%d", subject, len(recipient_ids))
    return resp


# ═══════════════════════════════════════════════════════════════════════════
# COMPREHENSIVE DATA PULL — Get everything for a project
# ═══════════════════════════════════════════════════════════════════════════

def pull_all_project_data(project_id: str | None = None) -> dict:
    """
    Pull ALL available data from ACC for a project.

    This is the master data extraction function — called on startup or
    on-demand to populate GigAI's project intelligence with real ACC data.

    Returns a dict with all data categories, each gracefully falling back
    to empty lists if the API isn't available for that module.
    """
    pid = project_id or _project_id()
    container_id = os.getenv("ACC_ISSUES_CONTAINER_ID", "")

    logger.info("ACC: pulling all data for project %s", pid)

    data = {
        "project_id": pid,
        "project_details": {},
        "users": [],
        "companies": [],
        "budgets": [],
        "contracts": [],
        "change_orders": [],
        "cost_items": [],
        "issues": [],
        "rfis": [],
        "submittals": [],
        "locations": {},
        "schedule": [],
        "checklists": [],
        "photos": [],
        "daily_logs": [],
        "documents": [],
    }

    # Pull each data type independently — failures don't block others
    try:
        data["project_details"] = get_project_details(pid)
    except Exception as exc:
        logger.warning("ACC pull: project details failed: %s", exc)

    try:
        data["users"] = get_project_users(pid)
    except Exception as exc:
        logger.warning("ACC pull: users failed: %s", exc)

    try:
        data["companies"] = get_companies()
    except Exception as exc:
        logger.warning("ACC pull: companies failed: %s", exc)

    try:
        data["budgets"] = get_budgets(pid)
    except Exception as exc:
        logger.warning("ACC pull: budgets failed: %s", exc)

    try:
        data["contracts"] = get_contracts(pid)
    except Exception as exc:
        logger.warning("ACC pull: contracts failed: %s", exc)

    try:
        data["change_orders"] = get_change_orders(pid)
    except Exception as exc:
        logger.warning("ACC pull: change orders failed: %s", exc)

    try:
        data["cost_items"] = get_cost_items(pid)
    except Exception as exc:
        logger.warning("ACC pull: cost items failed: %s", exc)

    try:
        data["issues"] = get_issues(pid, container_id)
    except Exception as exc:
        logger.warning("ACC pull: issues failed: %s", exc)

    try:
        data["rfis"] = get_rfis(pid, container_id)
    except Exception as exc:
        logger.warning("ACC pull: RFIs failed: %s", exc)

    try:
        data["submittals"] = get_submittals(pid)
    except Exception as exc:
        logger.warning("ACC pull: submittals failed: %s", exc)

    try:
        data["locations"] = get_floor_plan(pid)
    except Exception as exc:
        logger.warning("ACC pull: locations failed: %s", exc)

    try:
        data["schedule"] = get_schedule_activities(pid)
    except Exception as exc:
        logger.warning("ACC pull: schedule failed: %s", exc)

    try:
        data["checklists"] = get_checklists(pid)
    except Exception as exc:
        logger.warning("ACC pull: checklists failed: %s", exc)

    try:
        data["photos"] = get_photos(pid)
    except Exception as exc:
        logger.warning("ACC pull: photos failed: %s", exc)

    try:
        data["daily_logs"] = get_daily_logs(pid)
    except Exception as exc:
        logger.warning("ACC pull: daily logs failed: %s", exc)

    try:
        data["documents"] = get_top_folders(pid)
    except Exception as exc:
        logger.warning("ACC pull: documents failed: %s", exc)

    # Summary
    counts = {k: len(v) if isinstance(v, list) else (1 if v else 0) for k, v in data.items() if k != "project_id"}
    logger.info("ACC pull complete for %s: %s", pid, counts)
    data["_summary"] = counts

    return data
