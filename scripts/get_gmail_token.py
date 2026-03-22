"""
Get Gmail OAuth refresh token using Google OAuth flow.
Run: python scripts/get_gmail_token.py

Prerequisites:
- GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET must be in .env
- Follow the browser prompt to authorize
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from dotenv import load_dotenv
load_dotenv()

import json

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.events",
]

CLIENT_ID = os.getenv("GMAIL_CLIENT_ID")
CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    print("❌ GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET must be set in .env")
    sys.exit(1)

print("🔐 Gmail OAuth Token Generator")
print("=" * 40)

try:
    from google_auth_oauthlib.flow import InstalledAppFlow

    REDIRECT_URI = "http://localhost:8080"

    client_config = {
        "installed": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uris": [REDIRECT_URI],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=8080)

    print(f"\n✅ Success! Add this to your .env file:")
    print(f"\nGMAIL_REFRESH_TOKEN={creds.refresh_token}")

    # Also show how to use it
    print(f"\nToken type: {creds.token_uri}")
    print("This token doesn't expire (only invalidated if you revoke access)")

except ImportError:
    print("❌ Missing package: pip install google-auth-oauthlib")
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nManual steps:")
    print(f"1. Go to: https://console.cloud.google.com/apis/credentials")
    print(f"2. Create OAuth 2.0 Client ID (Desktop app)")
    print(f"3. Use Client ID: {CLIENT_ID[:20]}...")
    print(f"4. Run this script again with the credentials")
