"""
Autodesk ACC OAuth Token Generator
Run: python generate_acc_token.py

1. Opens browser for OAuth authorization
2. Catches callback on localhost:8080
3. Exchanges code for access token
4. Prints: ACC_ACCESS_TOKEN=<token>
"""
import os
import webbrowser
import urllib.parse
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
import httpx

CLIENT_ID = os.getenv("ACC_CLIENT_ID")
CLIENT_SECRET = os.getenv("ACC_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8080/callback"
SCOPES = "data:read data:write account:read"

AUTH_URL = "https://developer.api.autodesk.com/authentication/v2/authorize"
TOKEN_URL = "https://developer.api.autodesk.com/authentication/v2/token"

_auth_code = None


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _auth_code
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)

        if "code" in params:
            _auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"""
                <html><body style="font-family:sans-serif;text-align:center;padding:60px;background:#f0f4ff">
                <h2 style="color:#16a34a">&#10003; Authorized!</h2>
                <p>Token received. You can close this tab.</p>
                </body></html>
            """)
        else:
            error = params.get("error", ["unknown"])[0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(f"<html><body><h2>Error: {error}</h2></body></html>".encode())

    def log_message(self, format, *args):
        pass  # suppress server logs


def exchange_code(code: str) -> dict:
    credentials = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    response = httpx.post(
        TOKEN_URL,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def main():
    global _auth_code

    auth_params = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
    })
    auth_url = f"{AUTH_URL}?{auth_params}"

    # Start local callback server (handles one request then stops)
    server = HTTPServer(("localhost", 8080), CallbackHandler)
    t = Thread(target=server.handle_request, daemon=True)
    t.start()

    print("=" * 60)
    print("  Autodesk ACC Token Generator")
    print("=" * 60)
    print(f"\nScopes: {SCOPES}")
    print("\nOpening browser for authorization...")
    webbrowser.open(auth_url)
    print("Waiting for callback on localhost:8080 ...")
    print("(If browser didn't open, paste this URL manually:)")
    print(f"\n{auth_url}\n")

    t.join(timeout=120)
    server.server_close()

    if not _auth_code:
        print("❌ Timed out — no authorization code received.")
        return

    print("✅ Code received, exchanging for token...")

    try:
        data = exchange_code(_auth_code)
    except httpx.HTTPStatusError as e:
        print(f"❌ Token exchange failed ({e.response.status_code}): {e.response.text}")
        return

    token = data.get("access_token")
    expires_in = data.get("expires_in", 3600)

    print()
    print("=" * 60)
    print("  SUCCESS — copy this line into your .env file:")
    print("=" * 60)
    print(f"\nACC_ACCESS_TOKEN={token}\n")
    print(f"Expires in: {expires_in // 60} minutes")
    print("⚠️  Regenerate when it expires.")


if __name__ == "__main__":
    main()
