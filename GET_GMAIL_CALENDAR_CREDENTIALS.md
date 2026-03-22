# Getting Gmail & Google Calendar API Credentials

You already have a Google OAuth Client ID and Secret — this guide shows how to enable
the APIs, add the correct scopes, and generate the refresh token that GIGAI needs.

---

## Step 1 — Enable the APIs in Google Cloud Console

1. Go to https://console.cloud.google.com
2. Select the project associated with your OAuth client
   (check https://console.cloud.google.com/apis/credentials to see which project owns
   Client ID `919904365153-...`)
3. In the left menu go to **APIs & Services → Library**
4. Search for **"Gmail API"** → click it → click **Enable**
5. Search for **"Google Calendar API"** → click it → click **Enable**

---

## Step 2 — Configure the OAuth Consent Screen

1. Go to **APIs & Services → OAuth consent screen**
2. If it says "Testing", add your Google account as a **Test user**:
   - Scroll to "Test users" → **+ Add users** → enter your Gmail address → Save
3. Make sure these scopes are listed (add them if missing):
   - `https://www.googleapis.com/auth/gmail.send`
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/calendar`
   - `https://www.googleapis.com/auth/calendar.events`

   To add scopes: click **Edit App** → **Add or remove scopes** → paste each scope above.

---

## Step 3 — Confirm Your OAuth Credentials

1. Go to **APIs & Services → Credentials**
2. Under "OAuth 2.0 Client IDs" you should see your client:
   `919904365153-qrkj4n2pi8oedg9onfcbdf9vc7h8g4f6.apps.googleusercontent.com`
3. Click the pencil (edit) icon
4. Under **Authorized redirect URIs**, make sure this URI is listed:
   ```
   http://localhost:8080
   ```
   If it's not there, click **+ Add URI**, paste it, and click **Save**.

---

## Step 4 — Generate the Refresh Token

Run the helper script from the project root:

```bash
python scripts/get_gmail_token.py
```

The script will:
1. Open a browser window asking you to log in with Google
2. Ask you to approve the Gmail + Calendar permissions
3. Print your `refresh_token` to the terminal

Copy the refresh token and paste it into your `.env`:

```
GMAIL_REFRESH_TOKEN=your_actual_refresh_token_here
```

### What the script does under the hood

```
GET https://accounts.google.com/o/oauth2/auth
  ?client_id=919904365153-...
  &redirect_uri=http://localhost:8080
  &response_type=code
  &scope=https://www.googleapis.com/auth/gmail.send
         https://www.googleapis.com/auth/gmail.readonly
         https://www.googleapis.com/auth/calendar
         https://www.googleapis.com/auth/calendar.events
  &access_type=offline
  &prompt=consent          ← forces Google to return a refresh token
```

---

## Step 5 — Verify It Works

```bash
# Test Gmail
python -c "
from scripts.get_gmail_token import test_gmail
test_gmail()
"

# Or just start the backend and check the /health endpoint
python -m uvicorn backend.main:app --reload
```

---

## Troubleshooting

| Error | Fix |
|---|---|
| `redirect_uri_mismatch` | Add `http://localhost:8080` to the OAuth client's redirect URIs (Step 3) |
| `access_denied` | Add your Google account as a Test user in the consent screen (Step 2) |
| `invalid_grant` | Refresh token has been revoked — re-run `get_gmail_token.py` |
| `insufficient_permission` | Missing a scope — re-run the script (Google will re-prompt for scopes) |
| Gmail API not enabled | Go back to Step 1 and enable the API |

---

## Summary of What Goes in .env

```
GMAIL_ENABLED=true
GMAIL_CLIENT_ID=919904365153-qrkj4n2pi8oedg9onfcbdf9vc7h8g4f6.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=GOCSPX-UpicgeusWghiUTlUbU0_6YAWELA
GMAIL_REFRESH_TOKEN=<paste token from get_gmail_token.py>
GMAIL_FROM_EMAIL=your@email.com
GMAIL_FROM_NAME=GigAI Material Coordinator

GOOGLE_CALENDAR_ENABLED=true
GOOGLE_CALENDAR_ID=primary   # or paste a specific calendar ID
```

The Calendar API uses the exact same OAuth client and refresh token as Gmail —
no extra credentials needed once Step 4 is done.
