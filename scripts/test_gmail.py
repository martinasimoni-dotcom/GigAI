"""
Test Gmail credentials — run from project root:
  python scripts/test_gmail.py
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import httpx
from config import settings


async def test_gmail():
    print("=" * 50)
    print("Gmail Credentials Check")
    print("=" * 50)

    # Check credentials present
    missing = []
    if not settings.GMAIL_CLIENT_ID:       missing.append("GMAIL_CLIENT_ID")
    if not settings.GMAIL_CLIENT_SECRET:   missing.append("GMAIL_CLIENT_SECRET")
    if not settings.GMAIL_REFRESH_TOKEN:   missing.append("GMAIL_REFRESH_TOKEN")

    if missing:
        print(f"❌ Missing credentials: {missing}")
        return

    print(f"✅ GMAIL_CLIENT_ID     : {settings.GMAIL_CLIENT_ID[:20]}...")
    print(f"✅ GMAIL_CLIENT_SECRET : {settings.GMAIL_CLIENT_SECRET[:10]}...")
    print(f"✅ GMAIL_REFRESH_TOKEN : {settings.GMAIL_REFRESH_TOKEN[:20]}...")
    print(f"   GMAIL_ENABLED      : {settings.GMAIL_ENABLED}")
    print(f"   GMAIL_FROM_EMAIL   : {settings.GMAIL_FROM_EMAIL}")
    print()

    # Try to get access token
    print("Testing token refresh...")
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.GMAIL_CLIENT_ID,
                "client_secret": settings.GMAIL_CLIENT_SECRET,
                "refresh_token": settings.GMAIL_REFRESH_TOKEN,
                "grant_type": "refresh_token",
            },
        )

    if resp.status_code == 200:
        data = resp.json()
        token = data.get("access_token", "")
        print(f"✅ Token valid — access_token: {token[:30]}...")
        print()
        print("📧 Gmail is READY TO SEND")
    else:
        print(f"❌ Token refresh FAILED: HTTP {resp.status_code}")
        print(f"   Response: {resp.text[:400]}")
        print()
        if "invalid_grant" in resp.text:
            print("   FIX: GMAIL_REFRESH_TOKEN is expired.")
            print("   Run: python scripts/get_gmail_token.py  (or see GET_GMAIL_CALENDAR_CREDENTIALS.md)")
        elif "invalid_client" in resp.text:
            print("   FIX: GMAIL_CLIENT_ID or GMAIL_CLIENT_SECRET is wrong.")

    print("=" * 50)


asyncio.run(test_gmail())
