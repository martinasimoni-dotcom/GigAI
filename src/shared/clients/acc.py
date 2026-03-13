"""
Autodesk Construction Cloud (ACC) API client.

Handles 2-legged OAuth2 token acquisition and caching, plus all ACC API calls
used across the GigAI pipeline:
  - Locations API  — floor plan / zone data
  - Issues API     — create tasks, RFIs, issues
  - Documents API  — drawing markups
  - Notifications  — ACC in-app notifications
  - Schedule       — project schedule activities

All methods raise RuntimeError if required env vars are absent.
Token is cached in-process until expiry.
"""
import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-process token cache
# ---------------------------------------------------------------------------
_token_cache: dict[str, Any] = {}   # {"access_token": str, "expires_at": float}


def _get_acc_token() -> str:
    """
    Acquire (or return cached) 2-legged OAuth token for ACC.

    Requires:
        ACC_CLIENT_ID     — Autodesk app client ID
        ACC_CLIENT_SECRET — Autodesk app client secret

    Raises:
        RuntimeError if credentials are missing.
        urllib.error.HTTPError on auth failure.
    """
    now = time.time()
    if _token_cache.get("access_token") and _token_cache.get("expires_at", 0) > now + 60:
        return _token_cache["access_token"]

    client_id = os.getenv("ACC_CLIENT_ID")
    client_secret = os.getenv("ACC_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError(
            "ACC_CLIENT_ID and ACC_CLIENT_SECRET must be set in .env to use ACC API"
        )

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
    """POST request to ACC API with JSON body, returns parsed JSON."""
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


# ---------------------------------------------------------------------------
# Locations API — floor plan / zone / unit data
# ---------------------------------------------------------------------------

def get_floor_plan(project_id: str, location_query: str | None = None) -> dict:
    """
    Fetch location tree nodes for the project from ACC Locations API.

    Returns a dict with project_id, nodes (list of location dicts), source="acc_api".

    Args:
        project_id: ACC project ID (e.g. "b.xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
        location_query: Optional filter string (e.g. "3rd Floor") to narrow results.

    Raises:
        RuntimeError if ACC_CLIENT_ID or ACC_CLIENT_SECRET not set.
    """
    # Fetch the location trees for the project
    trees_resp = _acc_get(f"/bim360/locations/v2/containers/{project_id}/trees")
    trees = trees_resp.get("results") or trees_resp.get("data", [])

    # Use the first tree (projects typically have one location tree)
    if not trees:
        logger.warning("ACC Locations API returned no trees for project %s", project_id)
        return {"project_id": project_id, "nodes": [], "source": "acc_api"}

    tree_id = trees[0].get("id") or trees[0].get("treeId")
    nodes_resp = _acc_get(
        f"/bim360/locations/v2/containers/{project_id}/trees/{tree_id}/nodes"
    )
    nodes = nodes_resp.get("results") or nodes_resp.get("data", [])

    # Filter by location_query if provided
    if location_query:
        q = location_query.lower()
        nodes = [n for n in nodes if q in (n.get("name") or "").lower()]

    return {
        "project_id": project_id,
        "tree_id": tree_id,
        "nodes": nodes,
        "source": "acc_api",
    }


# ---------------------------------------------------------------------------
# Schedule API — project schedule activities
# ---------------------------------------------------------------------------

def get_schedule_activities(project_id: str) -> list[dict]:
    """
    Fetch schedule activities from ACC Schedule API.

    Returns a list of activity dicts with at minimum: name, startDate, endDate.

    Raises:
        RuntimeError if credentials not set.
    """
    account_id = os.getenv("ACC_ACCOUNT_ID")
    if not account_id:
        raise RuntimeError("ACC_ACCOUNT_ID must be set in .env to fetch ACC schedule")

    # ACC Schedule v1 API
    resp = _acc_get(
        f"/construction/schedule/v1/projects/{project_id}/activities",
    )
    activities = resp.get("results") or resp.get("data", [])
    return [
        {
            "activity": a.get("name") or a.get("title", ""),
            "date": a.get("startDate") or a.get("start_date", ""),
            "end_date": a.get("endDate") or a.get("end_date", ""),
            "location": a.get("location", ""),
        }
        for a in activities
    ]


# ---------------------------------------------------------------------------
# Issues API — create tasks / RFIs / issues
# ---------------------------------------------------------------------------

def create_issue(
    project_id: str,
    container_id: str,
    title: str,
    description: str,
    assignee_id: str | None = None,
    issue_type: str = "task",
    due_date: str | None = None,
) -> dict:
    """
    Create an ACC issue (task / RFI / quality issue).

    Args:
        project_id:    ACC project ID
        container_id:  Issues container ID for the project
        title:         Issue title
        description:   Issue description
        assignee_id:   ACC user ID of the assignee (optional)
        issue_type:    "task", "rfi", or "quality" (default "task")
        due_date:      ISO date string "YYYY-MM-DD" (optional)

    Returns:
        Created issue dict from ACC API.
    """
    payload: dict[str, Any] = {
        "title": title,
        "description": description,
        "status": "open",
    }
    if assignee_id:
        payload["assignedTo"] = assignee_id
    if due_date:
        payload["dueDate"] = due_date

    resp = _acc_post(
        f"/issues/v1/containers/{container_id}/quality-issues",
        payload,
    )
    issue_id = (resp.get("data") or resp).get("id", "unknown")
    logger.info("ACC issue created: id=%s title=%s", issue_id, title)
    return resp.get("data") or resp


# ---------------------------------------------------------------------------
# Markup / Drawing API — drawing annotations
# ---------------------------------------------------------------------------

def create_drawing_markup(
    project_id: str,
    version_urn: str,
    drawing_number: str,
    annotation_text: str,
    x: float = 0.0,
    y: float = 0.0,
) -> dict:
    """
    Add a markup annotation to an ACC drawing via the Document Management API.

    Args:
        project_id:      ACC project ID
        version_urn:     Base64-encoded URN of the document version to annotate
        drawing_number:  Human-readable drawing reference (e.g. "A-301")
        annotation_text: Text content of the markup
        x, y:            Approximate position on drawing (0.0–1.0 relative coords)

    Returns:
        Created markup dict from ACC API.
    """
    payload = {
        "type": "markup",
        "attributes": {
            "text": annotation_text,
            "urnVersion": version_urn,
            "position": {"x": x, "y": y},
            "drawingNumber": drawing_number,
        },
    }
    resp = _acc_post(
        f"/bim360/docs/v1/projects/{project_id}/markups",
        payload,
    )
    logger.info("ACC markup created on drawing %s for project %s", drawing_number, project_id)
    return resp.get("data") or resp


# ---------------------------------------------------------------------------
# Notifications API — in-app ACC notifications
# ---------------------------------------------------------------------------

def send_acc_notification(
    account_id: str,
    project_id: str,
    subject: str,
    body: str,
    recipient_ids: list[str],
) -> dict:
    """
    Send an ACC in-app notification to a list of users.

    Args:
        account_id:     ACC account/hub ID
        project_id:     ACC project ID
        subject:        Notification subject line
        body:           Notification body text
        recipient_ids:  List of ACC user IDs

    Returns:
        Response dict from ACC Notifications API.
    """
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
    logger.info(
        "ACC notification sent: subject=%s recipients=%d", subject, len(recipient_ids)
    )
    return resp
