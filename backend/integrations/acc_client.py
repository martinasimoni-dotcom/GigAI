import httpx
import base64
import json as _json
from datetime import datetime, timezone, timedelta
from config import settings


def _jwt_exp(token: str) -> datetime | None:
    """Decode the 'exp' field from a JWT without verifying the signature."""
    try:
        payload_b64 = token.split(".")[1]
        # Add padding so base64 doesn't choke
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload = _json.loads(base64.urlsafe_b64decode(payload_b64))
        exp = payload.get("exp")
        if exp:
            return datetime.fromtimestamp(int(exp), tz=timezone.utc)
    except Exception:
        pass
    return None


def _strip_b(pid: str) -> str:
    """Return project ID without the 'b.' prefix."""
    return pid[2:] if pid.startswith("b.") else pid


def _add_b(pid: str) -> str:
    """Return project ID with the 'b.' prefix."""
    return pid if pid.startswith("b.") else f"b.{pid}"


# ---------------------------------------------------------------------------
# Process-level token cache — shared across all ACCClient instances so we
# don't fetch a new token on every poller tick or webhook handler invocation.
# ---------------------------------------------------------------------------
_cached_token:     str | None = None
_token_expires_at: datetime | None = None
# Mutable so refresh-token rotation can be persisted in-process
_current_refresh_token: str | None = None


class ACCClient:
    BASE_URL = "https://developer.api.autodesk.com"
    AUTH_URL = "https://developer.api.autodesk.com/authentication/v2/token"
    # Refresh 5 minutes before actual expiry to avoid mid-request expiry.
    _EXPIRY_BUFFER = timedelta(minutes=5)

    def __init__(self):
        self.hub_id       = settings.ACC_HUB_ID
        self.project_id   = settings.ACC_PROJECT_ID
        self.container_id = settings.ACC_CONTAINER_ID

    # -------------------------------------------------------------------------
    # Token management
    # -------------------------------------------------------------------------

    async def _ensure_valid_token(self) -> str:
        """
        Return a valid ACC access token.

        Token sources (checked in order):
          1. In-process cache — reused until 5 min before expiry.
          2. ACC_ACCESS_TOKEN in .env — fresh JWT pasted from Postman.
             Expiry is read directly from the JWT; no guessing needed.
          3. ACC_REFRESH_TOKEN in .env — exchanged for a new access token.
             Autodesk may rotate the refresh token; the new one is stored
             in-process for the remainder of the backend session.

        Manual token workflow (Postman):
          Step 1 — Get authorization code:
            GET https://developer.api.autodesk.com/authentication/v2/authorize
              ?response_type=code
              &client_id=<ACC_CLIENT_ID>
              &redirect_uri=http://localhost:8080/callback
              &scope=data:read data:write account:read user-profile:read

          Step 2 — Exchange code for tokens:
            POST https://developer.api.autodesk.com/authentication/v2/token
            Body (x-www-form-urlencoded):
              grant_type=authorization_code
              code=<code from step 1>
              client_id=<ACC_CLIENT_ID>
              client_secret=<ACC_CLIENT_SECRET>
              redirect_uri=http://localhost:8080/callback

          Step 3 — Paste into .env:
            ACC_ACCESS_TOKEN=<access_token from response>
            ACC_REFRESH_TOKEN=<refresh_token from response>

          Step 4 — Restart backend. Tokens auto-refresh from here.
        """
        global _cached_token, _token_expires_at, _current_refresh_token

        now = datetime.now(timezone.utc)

        # ── 1. Return cached token if still valid ──────────────────────────────
        if (
            _cached_token
            and _token_expires_at
            and now < _token_expires_at - self._EXPIRY_BUFFER
        ):
            return _cached_token

        # ── 2. Seed cache from ACC_ACCESS_TOKEN on first call ──────────────────
        if not _cached_token and settings.ACC_ACCESS_TOKEN:
            exp = _jwt_exp(settings.ACC_ACCESS_TOKEN)
            if exp and now < exp - self._EXPIRY_BUFFER:
                _cached_token     = settings.ACC_ACCESS_TOKEN
                _token_expires_at = exp
                print(
                    f"🔑 ACC: loaded access token from .env "
                    f"(expires {exp.strftime('%H:%M:%S')} UTC)"
                )
                return _cached_token
            else:
                print("⚠️  ACC: ACC_ACCESS_TOKEN in .env is expired — trying refresh token…")

        # ── 3. Use refresh token to get a new access token ─────────────────────
        refresh_token = _current_refresh_token or settings.ACC_REFRESH_TOKEN
        if not refresh_token:
            raise RuntimeError(
                "ACC: no valid token available.\n"
                "  Set ACC_REFRESH_TOKEN (and optionally ACC_ACCESS_TOKEN) in .env.\n"
                "  See the manual Postman workflow in acc_client.py docstring."
            )

        print("🔑 ACC: exchanging refresh token for new access token…")
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                self.AUTH_URL,
                data={
                    "grant_type":    "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id":     settings.ACC_CLIENT_ID,
                    "client_secret": settings.ACC_CLIENT_SECRET,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        if resp.status_code != 200:
            body = resp.text[:400]
            hint = ""
            if "invalid_grant" in body or "expired" in body:
                hint = (
                    "\n  ⚠️  Refresh token expired. Use Postman to get fresh tokens,\n"
                    "      paste ACC_ACCESS_TOKEN + ACC_REFRESH_TOKEN into .env, restart."
                )
            raise RuntimeError(
                f"ACC token refresh failed ({resp.status_code}): {body}{hint}"
            )

        body       = resp.json()
        token      = body.get("access_token")
        expires_in = int(body.get("expires_in", 3600))

        if not token:
            raise RuntimeError(
                f"No access_token in refresh_token response: {resp.text[:300]}"
            )

        # Store rotated refresh token if Autodesk issued a new one
        new_rt = body.get("refresh_token")
        if new_rt and new_rt != refresh_token:
            print(f"   Refresh token rotated — updated in-process", flush=True)
            _current_refresh_token = new_rt

        _cached_token     = token
        _token_expires_at = now + timedelta(seconds=expires_in)
        print(
            f"   OK Token obtained via refresh_token — valid for {expires_in // 60} min "
            f"(until {_token_expires_at.strftime('%H:%M:%S')} UTC)",
            flush=True,
        )
        return _cached_token

    async def _headers(self) -> dict:
        token = await self._ensure_valid_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
            "x-ads-region":  settings.ACC_REGION,
        }

    def _is_token_valid(self) -> bool:
        """Guard — True when credentials are configured (either OAuth mode)."""
        return bool(settings.ACC_CLIENT_ID and settings.ACC_CLIENT_SECRET)

    # -------------------------------------------------------------------------
    # RFI operations
    # -------------------------------------------------------------------------

    async def list_rfis(
        self,
        project_id: str | None = None,
        limit: int = 25,
    ) -> list[dict]:
        """
        Return recent Issues from the ACC Issues API v2, mapped to the
        RFI-like structure the rest of the pipeline expects.

        The native RFI API requires 3-legged OAuth (user context).  The Issues
        API v2 works with 2-legged tokens and exposes RFIs as issues whose
        type contains "rfi" — we filter and normalise them here.

        Candidates tried (in order):
          1. /construction/issues/v2/projects/{id_no_b}/issues
          2. /construction/issues/v2/projects/{id_with_b}/issues
          3. /construction/issues/v1/projects/{id_no_b}/issues  (legacy)
          4. /construction/issues/v1/projects/{id_with_b}/issues
        """
        raw = project_id or self.project_id or ""
        if not self._is_token_valid():
            raise RuntimeError(
                "ACC credentials not configured. Set ACC_CLIENT_ID and ACC_CLIENT_SECRET in .env"
            )

        candidates = [
            ("v2", _strip_b(raw)),
            ("v2", _add_b(raw)),
            ("v1", _strip_b(raw)),
            ("v1", _add_b(raw)),
        ]

        async with httpx.AsyncClient(timeout=30) as client:
            for version, pid in candidates:
                url = f"{self.BASE_URL}/construction/issues/{version}/projects/{pid}/issues"
                params = {"limit": limit}
                print(f"   ACC list_rfis trying: GET {url}")
                resp = await client.get(url, headers=await self._headers(), params=params)
                print(f"   → HTTP {resp.status_code}")
                if resp.status_code == 200:
                    data  = resp.json()
                    items = data.get("results") or data.get("data") or []
                    if not isinstance(items, list):
                        items = []
                    print(f"   ✅ {len(items)} issue(s) returned via {version}/{pid}")
                    return [_issue_to_rfi(i) for i in items]
                # Only log the full error body on the first attempt
                if version == "v2" and not pid.startswith("b."):
                    print(f"   Full error: {resp.text[:400]}")

        print(f"⚠️  ACC list_rfis: all candidates failed for project {raw}")
        return []

    async def get_rfi(self, rfi_id: str, project_id: str | None = None) -> dict:
        """
        Fetch full RFI details by ID.

        Tries RFI API (v2/v1) and Issues API (v2) with both b./no-b. prefix variants.
        Raises RuntimeError if all candidates fail — no mock fallback.
        """
        raw = project_id or self.project_id or ""
        if not self._is_token_valid():
            raise RuntimeError(
                "ACC credentials not configured. Set ACC_CLIENT_ID and ACC_CLIENT_SECRET in .env"
            )

        pid_no_b = _strip_b(raw)
        pid_b    = _add_b(raw)
        headers  = await self._headers()

        # (api_path, project_id_variant)
        candidates = [
            (f"construction/rfis/v2/projects/{pid_no_b}/rfis/{rfi_id}",    "rfis/v2 (no b.)"),
            (f"construction/rfis/v2/projects/{pid_b}/rfis/{rfi_id}",        "rfis/v2 (b.)"),
            (f"construction/issues/v2/projects/{pid_no_b}/issues/{rfi_id}", "issues/v2 (no b.)"),
            (f"construction/issues/v2/projects/{pid_b}/issues/{rfi_id}",    "issues/v2 (b.)"),
            (f"construction/rfis/v1/projects/{pid_no_b}/rfis/{rfi_id}",    "rfis/v1 (no b.)"),
            (f"construction/rfis/v1/projects/{pid_b}/rfis/{rfi_id}",        "rfis/v1 (b.)"),
        ]

        last_status = None
        last_body   = ""

        async with httpx.AsyncClient(timeout=30) as client:
            for path, label in candidates:
                url = f"{self.BASE_URL}/{path}"
                print(f"   ACC get_rfi → GET {url}")
                resp = await client.get(url, headers=headers)
                print(f"   → HTTP {resp.status_code} ({label})")
                if resp.status_code == 200:
                    data = resp.json()
                    result = data.get("data", data)
                    print(f"   ✅ Got RFI: {result.get('title') or result.get('id', '?')!r}")
                    return result
                last_status = resp.status_code
                last_body   = resp.text[:400]
                if resp.status_code not in (404, 403, 401):
                    print(f"   Full error: {last_body}")

        raise RuntimeError(
            f"ACC get_rfi '{rfi_id}': all {len(candidates)} candidates failed. "
            f"Last response: HTTP {last_status} — {last_body}"
        )

    async def create_rfi(
        self,
        title: str,
        description: str,
        project_id: str | None = None,
        linked_rfi_id: str | None = None,
    ) -> dict:
        """Create an RFI in ACC. Optionally links it to a source RFI."""
        raw = project_id or self.project_id or ""
        if not self._is_token_valid():
            raise RuntimeError(
                "ACC credentials not configured. Set ACC_CLIENT_ID and ACC_CLIENT_SECRET in .env"
            )

        body: dict = {"title": title, "description": description}
        if linked_rfi_id:
            body["linkedIssues"] = [{"id": linked_rfi_id}]

        candidates = [
            f"{self.BASE_URL}/construction/rfis/v2/projects/{_strip_b(raw)}/rfis",
            f"{self.BASE_URL}/construction/rfis/v2/projects/{_add_b(raw)}/rfis",
            f"{self.BASE_URL}/construction/rfis/v1/projects/{_strip_b(raw)}/rfis",
        ]

        last_status = None
        last_body = ""
        async with httpx.AsyncClient(timeout=30) as client:
            for url in candidates:
                print(f"   ACC create_rfi → POST {url}")
                resp = await client.post(url, headers=await self._headers(), json=body)
                print(f"   → HTTP {resp.status_code}")
                if resp.status_code in (200, 201):
                    data = resp.json()
                    result = data.get("data", data)
                    print(f"   ✅ RFI created: {result.get('id', '?')}")
                    return result
                last_status = resp.status_code
                last_body = resp.text[:600]
                print(f"   Full error: {last_body}")

        raise RuntimeError(
            f"ACC create_rfi failed on all candidates. "
            f"Last response: HTTP {last_status} — {last_body}"
        )

    async def update_rfi(
        self,
        rfi_id: str,
        status: str,
        comment: str = "",
        project_id: str | None = None,
    ) -> dict:
        """Update RFI status (e.g. 'open' → 'answered' or 'closed')."""
        raw = project_id or self.project_id or ""
        if not self._is_token_valid():
            raise RuntimeError(
                "ACC credentials not configured. Set ACC_CLIENT_ID and ACC_CLIENT_SECRET in .env"
            )

        body: dict = {"status": status}
        if comment:
            body["answer"] = comment

        candidates = [
            ("v2", _strip_b(raw)),
            ("v2", _add_b(raw)),
            ("v1", _strip_b(raw)),
        ]
        last_status = None
        last_body = ""
        for version, pid in candidates:
            url = f"{self.BASE_URL}/construction/rfis/{version}/projects/{pid}/rfis/{rfi_id}"
            async with httpx.AsyncClient(timeout=30) as client:
                print(f"   ACC update_rfi → PATCH {url}")
                resp = await client.patch(url, headers=await self._headers(), json=body)
                print(f"   → HTTP {resp.status_code}")
                if resp.status_code in (200, 204):
                    data = resp.json() if resp.content else {}
                    return data.get("data", {"id": rfi_id, "status": status})
                last_status = resp.status_code
                last_body = resp.text[:400]
                print(f"   Error: {last_body}")

        raise RuntimeError(
            f"ACC update_rfi {rfi_id}: all candidates failed. "
            f"Last response: HTTP {last_status} — {last_body}"
        )

    # -------------------------------------------------------------------------
    # User lookup
    # -------------------------------------------------------------------------

    async def get_user_email(self, user_id: str) -> str | None:
        """
        Resolve an ACC user ID to an email address.

        Tries (in order):
          1. Construction Admin API v1 — works with 3-legged tokens
          2. Construction Admin API v2
          3. HQ v2 (2-legged only — included as last resort)
        """
        if not user_id or not self._is_token_valid():
            return None

        account_id = _strip_b(self.hub_id or "")
        pid_no_b   = _strip_b(self.project_id or "")
        pid_b      = _add_b(self.project_id or "")

        candidates = [
            # Construction Admin API — works with 3-legged OAuth
            f"{self.BASE_URL}/construction/admin/v1/projects/{pid_no_b}/users/{user_id}",
            f"{self.BASE_URL}/construction/admin/v1/projects/{pid_b}/users/{user_id}",
            f"{self.BASE_URL}/construction/admin/v2/projects/{pid_no_b}/users/{user_id}",
            # BIM360 Admin API
            f"{self.BASE_URL}/bim360/hq/v2/accounts/{account_id}/users/{user_id}",
        ]

        async with httpx.AsyncClient(timeout=15) as client:
            for url in candidates:
                print(f"   ACC get_user_email → GET {url}")
                resp = await client.get(url, headers=await self._headers())
                print(f"   → HTTP {resp.status_code}")
                if resp.status_code == 200:
                    data  = resp.json()
                    # Construction Admin API wraps response under "results" or root
                    user  = data.get("results", [data])[0] if isinstance(data.get("results"), list) else data
                    email = user.get("email") or user.get("emailAddress")
                    if email:
                        print(f"   ✅ Resolved email: {email}")
                        return email
                    print(f"   ⚠️  200 but no email field. Keys: {list(data.keys())}")
                else:
                    print(f"   Error: {resp.text[:200]}")

        print(f"   ⚠️  Could not resolve email for user {user_id}")
        return None

    # -------------------------------------------------------------------------
    # Project context enrichment
    # -------------------------------------------------------------------------

    async def get_project_context(self, project_id: str | None = None) -> dict:
        """Return a lightweight project context dict for proposal enrichment."""
        pid = project_id or self.project_id
        info = await self.get_project_info(pid)
        return {
            "name": info.get("name", "Unknown Project"),
            "id": pid,
            "status": info.get("status", "active"),
            "items": [],
        }

    async def get_project_info(self, project_id: str | None = None) -> dict:
        """Fetch project metadata from ACC."""
        pid = _add_b(project_id or self.project_id or "")
        url = f"{self.BASE_URL}/project/v1/hubs/{self.hub_id}/projects/{pid}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=await self._headers())
            if resp.status_code == 200:
                return resp.json().get("data", {}).get("attributes", {})
            print(f"   ⚠️  get_project_info: HTTP {resp.status_code} — {resp.text[:200]}")
            return {}

    # -------------------------------------------------------------------------
    # Notifications
    # -------------------------------------------------------------------------

    async def send_notification(self, message: str) -> None:
        """Send ACC notification (secondary — logged only for now)."""
        print(f"📨 ACC notification: {message[:80]}")


# ---------------------------------------------------------------------------
# Issues → RFI normaliser
# ---------------------------------------------------------------------------

def _issue_to_rfi(issue: dict) -> dict:
    """
    Map an ACC Issues API v2 object to the RFI-like dict the pipeline expects.

    Issues API fields  →  RFI field
    ─────────────────────────────────────────────────────────────────────────
    id                 →  id
    title              →  title
    description        →  description
    assignedTo         →  assignedTo
    assignedToType     →  assignedToType
    status             →  status
    createdAt          →  createdAt
    updatedAt          →  updatedAt
    projectId / containerId  →  projectId
    """
    attrs = issue.get("attributes") or issue  # v2 wraps fields under "attributes"
    return {
        "id":              issue.get("id") or attrs.get("id", ""),
        "title":           attrs.get("title") or attrs.get("name") or "",
        "description":     attrs.get("description") or attrs.get("body") or "",
        "assignedTo":      (attrs.get("assignedTo") or {}).get("id") or attrs.get("assignedTo") or "",
        "assignedToType":  (attrs.get("assignedTo") or {}).get("type") or "",
        "assignedToEmail": (attrs.get("assignedTo") or {}).get("email") or "",
        "status":          attrs.get("status") or "open",
        "createdAt":       attrs.get("createdAt") or attrs.get("createdDate") or "",
        "updatedAt":       attrs.get("updatedAt") or attrs.get("updatedDate") or "",
        "projectId":       attrs.get("projectId") or attrs.get("containerId") or "",
        # Preserve the raw issue so downstream code can inspect it if needed
        "_raw_issue":      issue,
    }


