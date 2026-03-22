#!/usr/bin/env python3
"""
Discover all available Autodesk webhook systems and events.

Usage:
    python scripts/list_available_webhook_events.py

Reads ACC_CLIENT_ID, ACC_CLIENT_SECRET, ACC_ACCESS_TOKEN from .env and
queries the APS Webhooks API to list every system and event available
for your credentials.

Autodesk Webhooks API docs:
    https://aps.autodesk.com/en/docs/webhooks/v1/reference/http/
"""
import sys
import os
import json
import asyncio
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

# Load .env before reading any env vars
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import httpx

# ── Constants ─────────────────────────────────────────────────────────────────
APS_BASE   = "https://developer.api.autodesk.com"
AUTH_URL   = f"{APS_BASE}/authentication/v2/token"
HOOKS_BASE = f"{APS_BASE}/webhooks/v1"

# Known systems to probe (the /systems endpoint may not be public)
KNOWN_SYSTEMS = [
    "data",
    "adsk.bim360",
    "autodesk.construction",
    "derivative",
    "adsk.core",
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


# ── Discovery helpers ─────────────────────────────────────────────────────────

async def get_systems(token: str) -> list[str]:
    """
    Try GET /webhooks/v1/systems to discover systems dynamically.
    Falls back to KNOWN_SYSTEMS if the endpoint returns an error.
    """
    url = f"{HOOKS_BASE}/systems"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, headers={"Authorization": f"Bearer {token}"})

    if resp.status_code == 200:
        try:
            data = resp.json()
            # Response shape varies — try common keys
            systems = (
                data.get("systems")
                or data.get("data")
                or (data if isinstance(data, list) else None)
            )
            if systems and isinstance(systems, list):
                names = [s.get("id") or s.get("name") or s if isinstance(s, str) else None
                         for s in systems]
                names = [n for n in names if n]
                if names:
                    return names
        except Exception:
            pass

    print(f"  /systems endpoint returned HTTP {resp.status_code} — using known system list")
    return KNOWN_SYSTEMS


async def get_events_for_system(token: str, system: str) -> list[dict]:
    """
    Probe GET /webhooks/v1/systems/{system}/events for available events.
    Returns a list of event dicts (raw API objects).
    """
    url = f"{HOOKS_BASE}/systems/{system}/events"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, headers={"Authorization": f"Bearer {token}"})

    if resp.status_code == 200:
        try:
            data = resp.json()
            events = (
                data.get("events")
                or data.get("data")
                or (data if isinstance(data, list) else [])
            )
            return events if isinstance(events, list) else []
        except Exception:
            return []

    return []


async def get_existing_hooks(token: str) -> list[dict]:
    """Return all registered webhooks (to infer valid event names from live hooks)."""
    hooks: list[dict] = []
    url = f"{HOOKS_BASE}/hooks?pageLimit=50"
    async with httpx.AsyncClient(timeout=20) as client:
        while url:
            resp = await client.get(url, headers={"Authorization": f"Bearer {token}"})
            if resp.status_code != 200:
                return hooks
            data = resp.json()
            hooks.extend(data.get("data", []))
            links = data.get("links", {})
            next_link = links.get("next", {})
            url = next_link.get("href") if isinstance(next_link, dict) else None
    return hooks


# ── Formatting helpers ────────────────────────────────────────────────────────

def hr(char: str = "─", width: int = 70) -> None:
    print(char * width)


def section(title: str) -> None:
    print()
    hr("═")
    print(f"  {title}")
    hr("═")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    print()
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║       GigAI — Discover Available ACC / APS Webhook Events            ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")

    # ── 1. Load credentials ───────────────────────────────────────────────────
    section("1 · Load credentials from .env")

    client_id     = os.getenv("ACC_CLIENT_ID", "")
    client_secret = os.getenv("ACC_CLIENT_SECRET", "")
    stored_token  = os.getenv("ACC_ACCESS_TOKEN", "")

    def mask(s: str) -> str:
        return s[:6] + "…" + s[-4:] if len(s) > 12 else "***"

    if client_id:
        print(f"  ACC_CLIENT_ID     = {mask(client_id)}")
    else:
        print("  ACC_CLIENT_ID     = ❌ not set")

    if client_secret:
        print(f"  ACC_CLIENT_SECRET = {mask(client_secret)}")
    else:
        print("  ACC_CLIENT_SECRET = ❌ not set")

    print(f"  ACC_ACCESS_TOKEN  = {'set (' + mask(stored_token) + ')' if stored_token else 'not set'}")

    if not client_id or not client_secret:
        print()
        print("  ❌ ACC_CLIENT_ID and ACC_CLIENT_SECRET are required in .env")
        sys.exit(1)

    # ── 2. Resolve access token ───────────────────────────────────────────────
    section("2 · Resolve access token")
    token = None

    if stored_token and stored_token not in ("your_acc_access_token_here", ""):
        print("  Validating stored ACC_ACCESS_TOKEN…")
        if await validate_token(stored_token):
            token = stored_token
            print("  ✅ Stored token is valid")
        else:
            print("  ⚠️  Stored token is expired or invalid — falling back to 2-legged")

    if not token:
        print("  Requesting 2-legged token via client credentials…")
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

    # ── 3. Discover systems ───────────────────────────────────────────────────
    section("3 · Discover webhook systems")
    print(f"  GET {HOOKS_BASE}/systems")
    systems = await get_systems(token)
    print(f"  Found {len(systems)} system(s) to probe: {', '.join(systems)}")

    # ── 4. List events per system ─────────────────────────────────────────────
    section("4 · Available events per system")

    all_results: dict[str, list[dict]] = {}
    total_events = 0

    for system in systems:
        url = f"{HOOKS_BASE}/systems/{system}/events"
        print(f"\n  GET {url}")
        events = await get_events_for_system(token, system)

        if events:
            all_results[system] = events
            total_events += len(events)
            print(f"  ✅  {system}  —  {len(events)} event(s):")
            hr("─", 70)
            for ev in events:
                # Normalise across different response shapes
                ev_id   = ev.get("id") or ev.get("eventId") or ev.get("event") or str(ev)
                ev_desc = ev.get("description") or ev.get("desc") or ""
                print(f"    • {ev_id}")
                if ev_desc:
                    print(f"        {ev_desc}")
        else:
            print(f"  —   {system}  —  no events returned (endpoint may not support discovery)")

    # ── 5. Infer events from existing hooks ───────────────────────────────────
    section("5 · Events inferred from your registered hooks")
    print(f"  GET {HOOKS_BASE}/hooks")
    existing_hooks = await get_existing_hooks(token)

    if existing_hooks:
        print(f"  Found {len(existing_hooks)} registered hook(s):\n")
        by_system: dict[str, set] = {}
        for h in existing_hooks:
            s = h.get("system", "unknown")
            e = h.get("event", "unknown")
            by_system.setdefault(s, set()).add(e)

        for sys_name, evts in sorted(by_system.items()):
            print(f"  System: {sys_name}")
            for evt in sorted(evts):
                print(f"    • {evt}")
    else:
        print("  No registered hooks found — nothing to infer from.")

    # ── 6. Summary ────────────────────────────────────────────────────────────
    section("6 · Summary")

    if all_results:
        print(f"  Total discoverable events: {total_events}\n")
        for system, events in all_results.items():
            print(f"  {system} ({len(events)} events):")
            for ev in events:
                ev_id = ev.get("id") or ev.get("eventId") or ev.get("event") or str(ev)
                print(f"    • {ev_id}")
        print()
    else:
        print("  No events were returned by the discovery endpoints.")
        print()
        print("  This is common — Autodesk does not publicly expose a full event catalogue.")
        print("  Use the known event names from the Webhooks API reference instead:")
        print()
        print("  ACC / APS well-known events (from official docs):")
        hr("─", 70)
        known = [
            ("data",                    "dm.version.added",                                "DM — new file version uploaded"),
            ("data",                    "dm.version.updated",                              "DM — file version updated"),
            ("data",                    "dm.folder.created",                               "DM — folder created"),
            ("adsk.bim360",             "quality:issues:created",                          "BIM 360 — quality issue created"),
            ("adsk.bim360",             "quality:issues:updated",                          "BIM 360 — quality issue updated"),
            ("adsk.bim360",             "rfis:created",                                    "BIM 360 — RFI created"),
            ("adsk.bim360",             "rfis:updated",                                    "BIM 360 — RFI updated"),
            ("adsk.bim360",             "submittals:created",                              "BIM 360 — submittal created"),
            ("autodesk.construction",   "autodesk.construction.workflow:rfis-1.created.v1",   "ACC — RFI created (v1)"),
            ("autodesk.construction",   "autodesk.construction.workflow:rfis-1.updated.v1",   "ACC — RFI updated (v1)"),
            ("autodesk.construction",   "autodesk.construction.workflow:issues-1.created.v1", "ACC — Issue created (v1)"),
            ("autodesk.construction",   "autodesk.construction.workflow:issues-1.updated.v1", "ACC — Issue updated (v1)"),
        ]
        for sys_name, event_id, description in known:
            print(f"  System : {sys_name}")
            print(f"  Event  : {event_id}")
            print(f"  Desc   : {description}")
            hr("·", 70)

    print()
    print("  Docs: https://aps.autodesk.com/en/docs/webhooks/v1/reference/events/")
    print()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nAborted.")
