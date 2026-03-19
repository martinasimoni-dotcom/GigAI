"""
scripts/setup_gmail.py

Re-authenticates Gmail with the correct read scope and prints the new refresh token.
Run this once, then update GMAIL_REFRESH_TOKEN in your .env with the printed value.

Usage:
    python -m scripts.setup_gmail
"""
import json
import sys
import webbrowser
import urllib.parse
import urllib.request
import http.server
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import settings

REDIRECT_URI = "http://localhost:8080"
SCOPE = "https://www.googleapis.com/auth/gmail.readonly"

auth_code = None


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        auth_code = params.get("code", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h2>Done! You can close this tab and return to the terminal.</h2>")

    def log_message(self, *args):
        pass  # suppress request logs


def main():
    client_id = settings.gmail_client_id
    client_secret = settings.gmail_client_secret

    if not client_id or not client_secret:
        print("ERROR: GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET must be set in .env")
        sys.exit(1)

    # Build auth URL
    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)

    # Start local callback server
    server = http.server.HTTPServer(("localhost", 8080), _CallbackHandler)
    thread = threading.Thread(target=server.handle_request)
    thread.start()

    print("\nOpening browser for Gmail authentication...")
    print("If browser doesn't open, visit this URL manually:\n")
    print(auth_url)
    webbrowser.open(auth_url)

    thread.join(timeout=120)

    if not auth_code:
        print("ERROR: No auth code received. Did you complete the browser flow?")
        sys.exit(1)

    # Exchange code for tokens
    token_data = urllib.parse.urlencode({
        "code": auth_code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=token_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    with urllib.request.urlopen(req) as resp:
        tokens = json.loads(resp.read().decode("utf-8"))

    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        print("ERROR: No refresh_token returned. Try revoking access at myaccount.google.com and re-running.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("SUCCESS! Copy this line into your .env file:")
    print("=" * 60)
    print(f"GMAIL_REFRESH_TOKEN={refresh_token}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
