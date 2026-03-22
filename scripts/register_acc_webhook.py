#!/usr/bin/env python3
"""
Register an Autodesk Construction Cloud webhook for RFI / Issue creation events.

Usage:
    python scripts/register_acc_webhook.py

Reads ACC_CLIENT_ID, ACC_CLIENT_SECRET, ACC_HUB_ID, ACC_PROJECT_ID from .env.
Prompts for your ngrok URL, then registers:
    POST [ngrok_url]/webhooks/acc

Autodesk Webhooks API docs:
    https://aps.autodesk.com/en/docs/webhooks/v1/reference/http/
"""
import sys
import os
import json
import asyncio
from pathlib import Path

# ── Path setup — load config from backend/ regardless of cwd ─────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

# Load .env before importing settings
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import httpx

# ── Constants ─────────────────────────────────────────────────────────────────
APS_BASE   = "https://developer.api.autodesk.com"
AUTH_URL   = f"{APS_BASE}/authentication/v2/token"
HOOKS_BASE = f"{APS_BASE}/webhooks/v1"

# Candidate events for RFI / Issue creation, ordered by preference.
# We try them in order and stop at the first successful registration.
# Reference: https://aps.autodesk.com/en/docs/webhooks/v1/reference/events/
CANDIDATE_EVENTS = [
    # ACC RFI (primary target — ACC Construction Cloud)
    {
        "system": "autodesk.construction",
        "event":  "autodesk.construction.workflow:rfis-1.created.v1",
        "label":  "ACC RFIs — created (v1)",
    },
    # ACC Issues (covers RFIs, submittals, etc. in the newer Issues API)
    {
        "system": "autodesk.construction",
        "event":  "autodesk.construction.workflow:issues-1.created.v1",
        "label":  "ACC Issues — created (v1)",
    },
    # BIM 360 Field quality issues (legacy but widely deployed)
    {
        "system": "adsk.bim360",
        "event":  "quality:issues:created",
        "label":  "BIM 360 Quality Issues — created",
    },
    # Data Management — new version added (useful if RFIs live in DM)
    {
        "system": "data",
        "event":  "dm.version.added",
        "label":  "Data Management — version added",
    },
]


# ── Auth helpers ──────────────────────────────────────────────────────────────

async def get_two_legged_token(client_id: str, client_secret: str) -> str:
    """Exchange client credentials for a 2-legged access token."""
    print("  Fetching 2-legged access token…")
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            AUTH_URL,
            data={
                "grant_type":    "client_credentials",
                "client_id":     client_id,
                "client_secret": client_secret,
                "scope":         "data:read data:write account:read",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if resp.status_code != 200:
        raise RuntimeError(
            f"Token request failed ({resp.status_code}): {resp.text[:300]}"
        )
    token = resp.json().get("access_token")
    if not token:
        raise RuntimeError(f"No access_token in response: {resp.text[:300]}")
    expires_in = resp.json().get("expires_in", 3600)
    print(f"  ✅ Token obtained (expires in {expires_in // 60} min)")
    return token


async def validate_token(token: str) -> bool:
    """Quick sanity-check: try a lightweight authenticated request."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{HOOKS_BASE}/hooks?pageLimit=1",
            headers={"Authorization": f"Bearer {token}"},
        )
    return resp.status_code in (200, 204)


# ── Webhook helpers ───────────────────────────────────────────────────────────

async def list_existing_hooks(token: str, callback_url_prefix: str | None = None) -> list[dict]:
    """Return all registered webhooks, optionally filtered by callback prefix."""
    hooks: list[dict] = []
    url = f"{HOOKS_BASE}/hooks?pageLimit=50"
    async with httpx.AsyncClient(timeout=20) as client:
        while url:
            resp = await client.get(url, headers={"Authorization": f"Bearer {token}"})
            if resp.status_code != 200:
                print(f"  ⚠️  Could not list hooks ({resp.status_code}): {resp.text[:200]}")
                return []
            data = resp.json()
            page_hooks = data.get("data", [])
            if callback_url_prefix:
                page_hooks = [
                    h for h in page_hooks
                    if h.get("callbackUrl", "").startswith(callback_url_prefix)
                ]
            hooks.extend(page_hooks)
            # Pagination
            links = data.get("links", {})
            next_link = links.get("next", {})
            url = next_link.get("href") if isinstance(next_link, dict) else None
    return hooks


async def register_hook(
    token:        str,
    system:       str,
    event:        str,
    callback_url: str,
    hub_id:       str,
    project_id:   str,
) -> tuple[int, dict]:
    """
    Register a single webhook and return (status_code, response_body).

    Scope rules (from Autodesk Webhooks API docs):
      autodesk.construction  →  scope key: "project"  only
      adsk.bim360            →  scope key: "hub"       only (account-level) or "project"
      data                   →  scope keys: "hub", "project", "folder", "resource"

    autoReactivateHook is only valid for the "data" system.
    hookAttribute values must all be strings.
    """
    # Ensure IDs carry the 'b.' prefix required by APS
    def b(id_: str) -> str:
        return id_ if id_.startswith("b.") else f"b.{id_}"

    hub_scoped     = b(hub_id)
    project_scoped = b(project_id)

    # ── Build scope per system ─────────────────────────────────────────────────
    # autodesk.construction: only "project" is a valid scope key.
    # adsk.bim360:           "hub" scopes to the whole account;
    #                        "project" scopes to one project.
    # data:                  both "hub" and "project" are accepted.
    if system == "autodesk.construction":
        scope = {"project": project_scoped}
    elif system == "adsk.bim360":
        scope = {"project": project_scoped}
    else:
        # data and any future systems
        scope = {"hub": hub_scoped, "project": project_scoped}

    # ── Build payload ─────────────────────────────────────────────────────────
    payload: dict = {
        "callbackUrl": callback_url,
        "scope": scope,
        # hookAttribute must be a flat object whose values are all strings.
        "hookAttribute": {
            "app":       "gigai",
            "projectId": project_scoped,
        },
    }

    # autoReactivateHook is only recognised by the "data" system.
    if system == "data":
        payload["autoReactivateHook"] = True

    # ── Debug output ──────────────────────────────────────────────────────────
    url = f"{HOOKS_BASE}/systems/{system}/events/{event}/hooks"
    print("  ── Request ──────────────────────────────────────────")
    print(f"  POST {url}")
    print(f"  Payload:\n{json.dumps(payload, indent=4)}")
    print("  ─────────────────────────────────────────────────────")

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type":  "application/json",
                "x-ads-region":  "US",
            },
            json=payload,
        )

    print(f"  HTTP {resp.status_code}")
    if resp.text:
        try:
            print(f"  Response:\n{json.dumps(resp.json(), indent=4)}")
        except Exception:
            print(f"  Response body: {resp.text[:500]}")
    print()

    return resp.status_code, resp.json() if resp.text else {}


async def delete_hook(token: str, system: str, event: str, hook_id: str) -> bool:
    url = f"{HOOKS_BASE}/systems/{system}/events/{event}/hooks/{hook_id}"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.delete(url, headers={"Authorization": f"Bearer {token}"})
    return resp.status_code in (200, 204)


# ── UI helpers ────────────────────────────────────────────────────────────────

def ask(prompt: str, default: str = "") -> str:
    try:
        val = input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    return val or default


def hr(char: str = "─", width: int = 60) -> None:
    print(char * width)


def section(title: str) -> None:
    print()
    hr()
    print(f"  {title}")
    hr()


# ── Main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║       GigAI — Register ACC Webhook                       ║")
    print("╚══════════════════════════════════════════════════════════╝")

    # ── 1. Load settings ──────────────────────────────────────────────────────
    section("1 · Load credentials from .env")
    try:
        from config import settings
    except Exception as e:
        print(f"  ❌ Failed to load config: {e}")
        print(f"     Make sure .env exists at: {ROOT / '.env'}")
        sys.exit(1)

    client_id     = settings.ACC_CLIENT_ID
    client_secret = settings.ACC_CLIENT_SECRET
    hub_id        = settings.ACC_HUB_ID
    project_id    = settings.ACC_PROJECT_ID
    stored_token  = settings.ACC_ACCESS_TOKEN

    missing = [k for k, v in {
        "ACC_CLIENT_ID":     client_id,
        "ACC_CLIENT_SECRET": client_secret,
        "ACC_HUB_ID":        hub_id,
        "ACC_PROJECT_ID":    project_id,
    }.items() if not v]
    if missing:
        print(f"  ❌ Missing required .env variables: {', '.join(missing)}")
        sys.exit(1)

    # Show what we loaded (masked)
    def mask(s: str) -> str:
        return s[:6] + "…" + s[-4:] if len(s) > 12 else "***"

    print(f"  ACC_CLIENT_ID     = {mask(client_id)}")
    print(f"  ACC_CLIENT_SECRET = {mask(client_secret)}")
    print(f"  ACC_HUB_ID        = {hub_id}")
    print(f"  ACC_PROJECT_ID    = {project_id}")
    print(f"  ACC_ACCESS_TOKEN  = {'set (' + mask(stored_token) + ')' if stored_token else 'not set'}")

    # ── 2. Resolve access token ───────────────────────────────────────────────
    section("2 · Resolve access token")
    token = None

    # Try the stored 3-legged token first
    if stored_token and stored_token not in ("your_acc_access_token_here", ""):
        print("  Validating stored ACC_ACCESS_TOKEN…")
        if await validate_token(stored_token):
            token = stored_token
            print("  ✅ Stored token is valid")
        else:
            print("  ⚠️  Stored token is expired or invalid")

    # Fall back to 2-legged client credentials
    if not token:
        print("  Requesting 2-legged token via client credentials…")
        print("  (Webhooks registration works with 2-legged tokens)")
        try:
            token = await get_two_legged_token(client_id, client_secret)
        except RuntimeError as e:
            print(f"  ❌ {e}")
            print()
            print("  Checklist:")
            print("  • ACC_CLIENT_ID / ACC_CLIENT_SECRET correct?")
            print("  • App has 'Webhook' API enabled at aps.autodesk.com/myapps")
            print("  • Scopes include: data:read  data:write  account:read")
            sys.exit(1)

    # ── 3. ngrok URL ──────────────────────────────────────────────────────────
    section("3 · Callback URL")
    print("  Your backend must be publicly reachable.")
    print("  Start ngrok:  ngrok http 8000")
    print()
    ngrok_url = ask("  Enter your ngrok HTTPS URL (e.g. https://abc123.ngrok-free.app): ")
    if not ngrok_url:
        print("  ❌ URL is required")
        sys.exit(1)
    ngrok_url = ngrok_url.rstrip("/")
    if not ngrok_url.startswith("https://"):
        print("  ⚠️  ACC requires HTTPS — prepending https://")
        ngrok_url = "https://" + ngrok_url.lstrip("http://")

    callback_url = f"{ngrok_url}/webhooks/acc"
    print(f"  Callback URL: {callback_url}")

    # ── 4. Show existing hooks ────────────────────────────────────────────────
    section("4 · Existing webhooks for this callback")
    existing = await list_existing_hooks(token, ngrok_url)
    if existing:
        print(f"  Found {len(existing)} existing hook(s) pointing to this URL:")
        for h in existing:
            print(f"    • [{h.get('hookId', '?')[:12]}…] "
                  f"{h.get('system','?')}/{h.get('event','?')}"
                  f"  status={h.get('status','?')}")
        print()
        ans = ask("  Delete existing hooks before registering? [y/N]: ", "n")
        if ans.lower() == "y":
            for h in existing:
                deleted = await delete_hook(
                    token,
                    h.get("system", ""),
                    h.get("event", ""),
                    h.get("hookId", ""),
                )
                status = "✅ deleted" if deleted else "⚠️  failed to delete"
                print(f"    {status}: {h.get('hookId','?')[:12]}…")
    else:
        print("  No existing hooks found for this ngrok URL.")

    # ── 5. Choose event ───────────────────────────────────────────────────────
    section("5 · Select webhook event")
    print("  Available event presets (for RFI / Issue creation):\n")
    for i, e in enumerate(CANDIDATE_EVENTS, 1):
        print(f"    [{i}] {e['label']}")
        print(f"        system: {e['system']}")
        print(f"        event:  {e['event']}")
        print()
    print(f"    [c] Custom  — enter system and event manually")
    print()

    choice = ask("  Select [1]: ", "1")

    if choice.lower() == "c":
        system = ask("  System: ").strip()
        event  = ask("  Event:  ").strip()
        label  = "Custom"
    else:
        try:
            idx = int(choice) - 1
            selected = CANDIDATE_EVENTS[idx]
            system = selected["system"]
            event  = selected["event"]
            label  = selected["label"]
        except (ValueError, IndexError):
            print("  Invalid choice — defaulting to option 1")
            selected = CANDIDATE_EVENTS[0]
            system = selected["system"]
            event  = selected["event"]
            label  = selected["label"]

    print(f"\n  → Registering: {label}")
    print(f"    System:  {system}")
    print(f"    Event:   {event}")

    # ── 6. Register ───────────────────────────────────────────────────────────
    section("6 · Register webhook")
    print(f"  Hub ID:     {hub_id}")
    print(f"  Project ID: {project_id}")
    print(f"  Callback:   {callback_url}")
    print()

    status_code, resp_body = await register_hook(
        token=token,
        system=system,
        event=event,
        callback_url=callback_url,
        hub_id=hub_id,
        project_id=project_id,
    )

    if status_code in (200, 201):
        hook_id = resp_body.get("hookId", resp_body.get("id", "?"))
        print("  ✅ Webhook registered successfully!")
        print()
        print(f"  Hook ID:    {hook_id}")
        print(f"  System:     {system}")
        print(f"  Event:      {event}")
        print(f"  Callback:   {callback_url}")
        print(f"  Status:     {resp_body.get('status', 'active')}")

        # Offer to save hook ID to .env
        print()
        ans = ask("  Save hook ID to .env as ACC_WEBHOOK_ID? [Y/n]: ", "y")
        if ans.lower() != "n":
            _save_env_var("ACC_WEBHOOK_ID", hook_id)

        section("Next steps")
        print("  1. Keep ngrok running:        ngrok http 8000")
        print("  2. Keep backend running:      cd backend && python main.py")
        print("  3. Create an RFI in ACC — GigAI will receive the webhook")
        print("     and automatically generate + email a proposal.")
        print()
        print("  Test the webhook manually:")
        print(f"    curl -X POST {callback_url} \\")
        print(f"      -H 'Content-Type: application/json' \\")
        print(f"      -d @scripts/sample_rfi_webhook.json")
        print()
        _write_sample_payload(project_id)

    elif status_code == 409:
        print("  ⚠️  Webhook already exists for this system/event/scope (409 Conflict).")
        print("     Delete the existing hook first (option in step 4) and retry.")
        if resp_body:
            print(f"     Response: {json.dumps(resp_body, indent=4)}")

    elif status_code == 401:
        print("  ❌ Unauthorised (401). Token may lack required scopes.")
        print("     Scopes needed:  data:read  data:write  account:read")
        print("     Regenerate token at: https://aps.autodesk.com/myapps")

    elif status_code == 403:
        print("  ❌ Forbidden (403). Check:")
        print("     • Hub ID / Project ID are correct")
        print("     • Your app is added to the ACC project")
        print("     • Token has account:read scope")
        if resp_body:
            print(f"     Response: {json.dumps(resp_body, indent=4)}")

    else:
        print(f"  ❌ Registration failed (HTTP {status_code})")
        if resp_body:
            print(f"     Response: {json.dumps(resp_body, indent=2)}")
        print()
        print("  Common fixes:")
        print("  • Try a different event preset (option 2 or 3)")
        print("  • Verify ACC_HUB_ID starts with 'b.' in your .env")
        print("  • Make sure the callback URL is HTTPS and publicly reachable")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _save_env_var(key: str, value: str) -> None:
    """Append or update a variable in the root .env file."""
    env_path = ROOT / ".env"
    lines: list[str] = []
    found = False
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if line.startswith(f"{key}=") or line.startswith(f"{key} ="):
                lines[i] = f"{key}={value}"
                found = True
                break
    if not found:
        lines.append(f"{key}={value}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  ✅ Saved {key} to .env")


def _write_sample_payload(project_id: str) -> None:
    """Write a sample webhook payload for manual testing."""
    sample = {
        "version": "1.0",
        "messageType": "notification",
        "payload": {
            "event": "autodesk.construction.workflow:rfis-1.created.v1",
            "projectId": project_id if project_id.startswith("b.") else f"b.{project_id}",
            "timestamp": "2026-03-22T10:00:00.000Z",
            "data": {
                "id": "rfi-test-001",
                "title": "Material Change Request — Test",
                "description": (
                    "Client requests replacing PVC porthole windows (40 units, Ø600mm) "
                    "with aluminum-framed porthole windows (Ø700mm, marine-grade). "
                    "Reason: improved durability for coastal environment."
                ),
                "assignedTo": "test-user-001",
                "assignedToEmail": "test@example.com",
                "status": "open",
                "createdAt": "2026-03-22T10:00:00.000Z",
                "projectId": project_id if project_id.startswith("b.") else f"b.{project_id}",
            },
        },
    }
    out_path = ROOT / "scripts" / "sample_rfi_webhook.json"
    out_path.write_text(json.dumps(sample, indent=2), encoding="utf-8")
    print(f"  Sample payload written to: scripts/sample_rfi_webhook.json")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nAborted.")
