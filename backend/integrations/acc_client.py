import httpx
from config import settings


class ACCClient:
    BASE_URL = "https://developer.api.autodesk.com"

    def __init__(self):
        self.access_token = settings.ACC_ACCESS_TOKEN
        self.hub_id = settings.ACC_HUB_ID
        self.project_id = settings.ACC_PROJECT_ID
        self.container_id = settings.ACC_CONTAINER_ID

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _is_token_valid(self) -> bool:
        return bool(
            self.access_token
            and self.access_token not in ("your_acc_access_token_here", "", None)
        )

    # -------------------------------------------------------------------------
    # RFI operations
    # -------------------------------------------------------------------------

    async def get_rfi(self, rfi_id: str, project_id: str | None = None) -> dict:
        """Fetch full RFI details by ID."""
        pid = project_id or self.project_id
        if not self._is_token_valid():
            print(f"⚠️  ACC: Would fetch RFI {rfi_id} (no token) — returning mock")
            return _mock_rfi(rfi_id, pid)

        url = f"{self.BASE_URL}/construction/rfis/v1/projects/{pid}/rfis/{rfi_id}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self._headers())
            if resp.status_code == 200:
                data = resp.json()
                return data.get("data", data)
            print(f"⚠️  ACC get_rfi {rfi_id} → {resp.status_code}: {resp.text[:200]}")
            return _mock_rfi(rfi_id, pid)

    async def create_rfi(
        self,
        title: str,
        description: str,
        project_id: str | None = None,
        linked_rfi_id: str | None = None,
    ) -> dict:
        """Create an RFI in ACC. Optionally links it to a source RFI."""
        pid = project_id or self.project_id
        if not self._is_token_valid():
            print(f"⚠️  ACC: Would create RFI '{title}' (no token)")
            return {"id": "mock-rfi-new", "status": "open", "title": title}

        body: dict = {"title": title, "description": description, "status": "open"}
        if linked_rfi_id:
            body["linkedIssues"] = [{"id": linked_rfi_id}]

        url = f"{self.BASE_URL}/construction/rfis/v1/projects/{pid}/rfis"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=self._headers(), json=body)
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", data)

    async def update_rfi(
        self,
        rfi_id: str,
        status: str,
        comment: str = "",
        project_id: str | None = None,
    ) -> dict:
        """Update RFI status (e.g. 'open' → 'answered' or 'closed')."""
        pid = project_id or self.project_id
        if not self._is_token_valid():
            print(f"⚠️  ACC: Would update RFI {rfi_id} → {status} (no token)")
            return {"id": rfi_id, "status": status}

        url = f"{self.BASE_URL}/construction/rfis/v1/projects/{pid}/rfis/{rfi_id}"
        body: dict = {"status": status}
        if comment:
            body["answer"] = comment
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.patch(url, headers=self._headers(), json=body)
            if resp.status_code in (200, 204):
                data = resp.json()
                return data.get("data", {"id": rfi_id, "status": status})
            print(f"⚠️  ACC update_rfi {rfi_id} → {resp.status_code}: {resp.text[:200]}")
            return {"id": rfi_id, "status": status}

    # -------------------------------------------------------------------------
    # User lookup
    # -------------------------------------------------------------------------

    async def get_user_email(self, user_id: str) -> str | None:
        """Resolve a user ID to an email address via ACC HQ API."""
        if not self._is_token_valid() or not user_id:
            return None
        # Strip hub prefix if present (hub ID is "b.<account-id>")
        account_id = (self.hub_id or "").lstrip("b.") or user_id
        url = f"{self.BASE_URL}/hq/v2/accounts/{account_id}/users/{user_id}"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=self._headers())
            if resp.status_code == 200:
                return resp.json().get("email")
        return None

    # -------------------------------------------------------------------------
    # Project context enrichment
    # -------------------------------------------------------------------------

    async def get_project_context(self, project_id: str | None = None) -> dict:
        """
        Return a lightweight project context dict for proposal enrichment.
        Attempts live data; falls back to a structured mock.
        """
        pid = project_id or self.project_id
        if not self._is_token_valid():
            return _mock_project_context(pid)

        info = await self.get_project_info(pid)
        return {
            "name": info.get("name", "Unknown Project"),
            "id": pid,
            "status": info.get("status", "active"),
            "items": [],  # extend later with BOQ / specs calls
        }

    async def get_project_info(self, project_id: str | None = None) -> dict:
        """Fetch project metadata."""
        pid = project_id or self.project_id
        if not self._is_token_valid():
            return {"name": "Sea house", "id": pid, "status": "active"}

        url = f"{self.BASE_URL}/project/v1/hubs/{self.hub_id}/projects/{pid}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self._headers())
            if resp.status_code == 200:
                return resp.json().get("data", {}).get("attributes", {})
            return {}

    # -------------------------------------------------------------------------
    # Notifications
    # -------------------------------------------------------------------------

    async def send_notification(self, message: str) -> None:
        """Send ACC notification (secondary — logged only for now)."""
        if not self._is_token_valid():
            print(f"⚠️  ACC: Would send notification: {message[:80]}")
            return
        print(f"📨 ACC notification: {message[:80]}")


# ---------------------------------------------------------------------------
# Mock helpers (used when no ACC access token is configured)
# ---------------------------------------------------------------------------

def _mock_rfi(rfi_id: str, project_id: str | None = None) -> dict:
    return {
        "id": rfi_id,
        "title": "Material Change Request — Porthole Windows",
        "description": (
            "Client requests replacing standard PVC porthole windows (40 units, Ø600mm) "
            "with high-spec aluminum-framed porthole windows. "
            "New spec: Ø700mm, marine-grade aluminum, double-glazed. "
            "Reason: improved durability and aesthetics for coastal environment. "
            "Affected areas: cabins 101–140, all exterior walls. "
            "Estimated cost difference to be confirmed by supplier."
        ),
        "assignedTo": "mock-user-001",
        "assignedToEmail": None,
        "status": "open",
        "createdAt": "2026-03-22T09:00:00Z",
        "projectId": project_id or settings.ACC_PROJECT_ID or "mock-project",
    }


def _mock_project_context(project_id: str | None = None) -> dict:
    return {
        "name": "Sea house",
        "id": project_id or settings.ACC_PROJECT_ID or "mock-project",
        "status": "active",
        "items": [
            {"type": "window", "spec": "PVC porthole Ø600mm", "quantity": 40, "unit_cost_eur": 380},
            {"type": "window", "spec": "Aluminum porthole Ø700mm", "quantity": 40, "unit_cost_eur": 620},
        ],
    }
