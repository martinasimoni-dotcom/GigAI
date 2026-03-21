# Phase 1: Input Layer - Research

**Researched:** 2026-03-13
**Domain:** FastAPI webhooks, Google Cloud Pub/Sub publishing, Gmail API polling, Google Calendar API polling
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Fireflies Webhook (INPUT-01)**
- File: `src/input/webhooks/fireflies.py`
- Route: `POST /webhooks/fireflies`
- Validate incoming payload (must have transcript data or meeting info)
- Create a `RawEvent` with `source="fireflies"` and `raw_payload=request.body`
- Publish serialized RawEvent to Pub/Sub `PUBSUB_TOPIC_RAW_EVENTS` topic
- Must publish within 5 minutes of meeting end (per REQUIREMENTS.md INPUT-01)
- Return 200 on success, 400 on validation failure

**ACC Webhook (INPUT-02)**
- File: `src/input/webhooks/acc.py`
- Route: `POST /webhooks/acc`
- Validate incoming payload (must be a valid ACC event structure)
- Create a `RawEvent` with `source="acc"` and `raw_payload=request.body`
- Publish serialized RawEvent to Pub/Sub raw-events topic
- Return 200 on success, 400 on validation failure

**Gmail Polling Connector (INPUT-03)**
- File: `src/input/connectors/gmail.py`
- Use Google OAuth2 credentials (GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET from settings)
- Poll Gmail API for unread messages with material-related keywords
- Filter by subject/body keywords: "material", "substitution", "change", "approval", "RFI"
- For each matching email: create `RawEvent` with `source="gmail"`, publish to Pub/Sub
- Use `google-auth` + `google-api-python-client` packages
- Polling function callable as standalone (for Cloud Scheduler / Cloud Functions trigger)

**Calendar Polling Connector (INPUT-04)**
- File: `src/input/connectors/calendar.py`
- Use Google OAuth2 credentials (GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET reused for Calendar)
- Poll Google Calendar API for upcoming events with delivery/installation keywords
- Filter by event title/description: "delivery", "installation", "material", "inspection"
- For each matching event: create `RawEvent` with `source="calendar"`, publish to Pub/Sub
- Look-ahead window: next 7 days of calendar events
- Polling function callable as standalone

**Pub/Sub Client**
- Use `google-cloud-pubsub` Python package
- Publisher client initialized from `GOOGLE_CLOUD_PROJECT` and `PUBSUB_TOPIC_RAW_EVENTS` settings
- Helper function `publish_event(raw_event: RawEvent) -> str` returns message_id
- Serialize RawEvent to JSON bytes for publishing

**FastAPI App (src/main.py)**
- Create FastAPI app instance
- Include webhook router from `src/input/webhooks/`
- Basic health check endpoint: `GET /health`
- All routes prefixed appropriately

**Package Structure**
- `src/input/__init__.py`
- `src/input/webhooks/__init__.py`
- `src/input/connectors/__init__.py`

**Infrastructure**
- `infra/pubsub/setup.sh` — bash script to create raw-events topic and subscription via `gcloud pubsub`

### Claude's Discretion
- Error handling: use Python stdlib logging with JSON formatter (established in Phase 0 pattern)
- Webhook secret validation: accept any non-empty payload for Phase 1 (full auth in Phase 7 middleware)
- Polling interval: left to caller (not embedded in connector code)
- Message attributes on Pub/Sub publish: include `source` as message attribute for filtering

### Deferred Ideas (OUT OF SCOPE)
- Cloud Functions deployment (infra/cloud_run/) — Phase 7+
- Full webhook signature verification (HMAC) — Phase 7 middleware
- Pub/Sub retry/dead-letter configuration — Phase 7+
- Gmail OAuth token refresh flow — Phase 7
- Multi-inbox / multi-calendar support — v2
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INPUT-01 | Fireflies webhook endpoint (POST /webhooks/fireflies): validate payload, publish to Pub/Sub raw-events topic within 5 minutes of meeting end | FastAPI APIRouter + Pub/Sub PublisherClient.publish() with future.result() for synchronous confirmation |
| INPUT-02 | ACC webhook endpoint (POST /webhooks/acc): validate payload, publish to Pub/Sub | Same pattern as INPUT-01 with `source="acc"` |
| INPUT-03 | Gmail API polling connector: detect material-related emails, publish to Pub/Sub | google.oauth2.credentials.Credentials + googleapiclient.discovery.build('gmail','v1') + users().messages().list(q=...) |
| INPUT-04 | Google Calendar polling connector: detect delivery/installation events, publish to Pub/Sub | build('calendar','v3') + events().list(timeMin=now, timeMax=+7days, singleEvents=True) |
</phase_requirements>

---

## Summary

Phase 1 implements four independent ingestion paths that all converge on a single output: serialized `RawEvent` JSON bytes published to the Google Cloud Pub/Sub `raw-events` topic. The phase produces no processing logic — it only captures and forwards.

The two webhook endpoints (Fireflies, ACC) are FastAPI `APIRouter` routes that receive POST payloads, perform lightweight structural validation, construct a `RawEvent` (using the already-complete Pydantic v2 model from Phase 0), and call a shared `publish_event()` helper. The two polling connectors (Gmail, Calendar) are standalone functions that build a Google API service client from stored OAuth2 credentials, query for matching items, and call the same `publish_event()` helper for each match. All four paths share one Pub/Sub publisher helper module.

The critical implementation detail across all four paths is that `google-cloud-pubsub`'s `publisher.publish()` returns a `Future` — call `.result()` on it to get the `message_id` and surface any publish errors synchronously. The Gmail and Calendar connectors use `google.oauth2.credentials.Credentials` constructed directly from `client_id`, `client_secret`, and `refresh_token` stored in the `.env` file — no browser OAuth flow needed at runtime.

**Primary recommendation:** Build `src/input/pubsub.py` as the shared publisher helper first; all four ingestion modules import from it. This prevents duplicated client construction and makes mock injection in tests trivial.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | >=0.109 (in requirements.txt) | Webhook HTTP endpoints, router | Already installed; async-first, Pydantic-native |
| google-cloud-pubsub | >=2.18 (in requirements.txt) | Publish RawEvent messages | Official GCP client; handles batching, futures |
| google-auth | >=2.27 (in requirements.txt) | OAuth2 credentials for Gmail/Calendar | Official Google auth library |
| google-api-python-client | not yet in requirements.txt | Gmail and Calendar REST API calls | Official discovery-based client |
| pydantic v2 | >=2.0 (in requirements.txt) | RawEvent construction and validation | Already established in Phase 0 |
| python-dotenv | >=1.0 (in requirements.txt) | Load .env at startup | Already in use via config/settings.py |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| uvicorn | >=0.27 (in requirements.txt) | ASGI server for FastAPI | Running the app locally / in Cloud Run |
| httpx | >=0.26 (in requirements.txt) | FastAPI TestClient in tests | Testing webhook endpoints |
| google-auth-httplib2 | latest | HTTP transport adapter for google-api-python-client | Required when building Gmail/Calendar service |

### Missing from requirements.txt

`google-api-python-client` is **not** in `requirements.txt` but is required for `googleapiclient.discovery.build()`. It must be added.

`google-auth-httplib2` is the standard HTTP transport for `google-api-python-client` and should also be added.

**Installation (additions needed):**
```bash
pip install google-api-python-client google-auth-httplib2
```

Add to `requirements.txt`:
```
google-api-python-client>=2.115
google-auth-httplib2>=0.2.0
```

---

## Architecture Patterns

### Recommended Project Structure

```
src/
├── main.py                      # FastAPI app, include_router, /health
├── input/
│   ├── __init__.py
│   ├── pubsub.py                # Shared: PublisherClient + publish_event()
│   ├── webhooks/
│   │   ├── __init__.py
│   │   ├── fireflies.py         # POST /webhooks/fireflies
│   │   └── acc.py               # POST /webhooks/acc
│   └── connectors/
│       ├── __init__.py
│       ├── gmail.py             # poll_gmail() standalone function
│       └── calendar.py          # poll_calendar() standalone function
infra/
└── pubsub/
    └── setup.sh                 # gcloud pubsub topic/subscription creation
```

### Pattern 1: Shared Pub/Sub Publisher Module

**What:** A single module `src/input/pubsub.py` that constructs the `PublisherClient` and topic path once, then exposes `publish_event(raw_event: RawEvent) -> str`.

**When to use:** Called by all four ingestion paths. Centralizes client construction, topic path formatting, JSON serialization, and future resolution.

**Example:**
```python
# Source: https://docs.cloud.google.com/python/docs/reference/pubsub/latest/google.cloud.pubsub_v1.publisher.client.Client
import json
from google.cloud import pubsub_v1
from config.settings import settings
from src.shared.models.events import RawEvent

_publisher: pubsub_v1.PublisherClient | None = None
_topic_path: str | None = None


def _get_publisher() -> tuple[pubsub_v1.PublisherClient, str]:
    global _publisher, _topic_path
    if _publisher is None:
        _publisher = pubsub_v1.PublisherClient()
        _topic_path = _publisher.topic_path(
            settings.google_cloud_project,
            settings.pubsub_topic_raw_events,
        )
    return _publisher, _topic_path


def publish_event(raw_event: RawEvent) -> str:
    """Publish a RawEvent to Pub/Sub. Returns message_id."""
    publisher, topic_path = _get_publisher()
    data: bytes = json.dumps(raw_event.model_dump(mode="json"), default=str).encode("utf-8")
    future = publisher.publish(topic_path, data, source=raw_event.source)
    message_id: str = future.result()  # blocks until confirmed or raises
    return message_id
```

Key details:
- `topic_path()` produces `"projects/{project}/topics/{topic}"` — required format.
- `data` must be `bytes` — the library raises `TypeError` on strings.
- `**attrs` keyword args become Pub/Sub message attributes (used for subscription filtering).
- `future.result()` raises `google.api_core.exceptions.GoogleAPICallError` on failure.
- `model_dump(mode="json")` on Pydantic v2 model produces JSON-serializable dict (handles `datetime` as ISO strings when `default=str` is passed to `json.dumps`).

### Pattern 2: FastAPI APIRouter for Webhooks

**What:** Each webhook file creates an `APIRouter` and defines routes on it. `src/main.py` uses `app.include_router()`.

**When to use:** Keeps webhook files self-contained; easy to test in isolation with `TestClient`.

**Example:**
```python
# src/input/webhooks/fireflies.py
import logging
import uuid
from fastapi import APIRouter, HTTPException, Request

from src.input.pubsub import publish_event
from src.shared.models.events import RawEvent

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/webhooks/fireflies")
async def receive_fireflies(request: Request) -> dict:
    body = await request.json()

    # Lightweight structural validation — full HMAC in Phase 7
    if not body or not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Empty or non-JSON payload")
    if "transcript" not in body and "meeting" not in body:
        raise HTTPException(status_code=400, detail="Missing transcript or meeting data")

    raw_event = RawEvent(
        event_id=str(uuid.uuid4()),
        source="fireflies",
        raw_payload=body,
    )
    message_id = publish_event(raw_event)
    logger.info({"event": "fireflies_published", "message_id": message_id})
    return {"status": "ok", "message_id": message_id}
```

```python
# src/main.py
from fastapi import FastAPI
from src.input.webhooks.fireflies import router as fireflies_router
from src.input.webhooks.acc import router as acc_router

app = FastAPI(title="GigAI")
app.include_router(fireflies_router)
app.include_router(acc_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
```

### Pattern 3: Google OAuth2 Credentials from Stored Refresh Token

**What:** Construct `google.oauth2.credentials.Credentials` directly from `client_id`, `client_secret`, and `refresh_token` stored in `.env`. No browser flow needed at runtime.

**When to use:** Both Gmail and Calendar connectors. The refresh token was obtained once (during initial setup) and is stored in `GMAIL_REFRESH_TOKEN`.

**Example:**
```python
# Source: https://googleapis.dev/python/google-auth/latest/reference/google.oauth2.credentials.html
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from config.settings import settings


def _build_gmail_service():
    creds = Credentials(
        token=None,
        refresh_token=settings.gmail_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.gmail_client_id,
        client_secret=settings.gmail_client_secret,
    )
    # Refresh to obtain a valid access token before making API calls
    creds.refresh(Request())
    return build("gmail", "v1", credentials=creds)


def _build_calendar_service():
    creds = Credentials(
        token=None,
        refresh_token=settings.gmail_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.gmail_client_id,
        client_secret=settings.gmail_client_secret,
    )
    creds.refresh(Request())
    return build("calendar", "v3", credentials=creds)
```

`settings.gmail_refresh_token` is already defined in `config/settings.py` and `.env.example`.

### Pattern 4: Gmail Polling with q= Parameter

**What:** Use `users().messages().list()` with a composed `q` query string to filter for unread material-related emails, then fetch each message to get subject/body.

**When to use:** `poll_gmail()` standalone function.

**Example:**
```python
# Source: https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/list
import uuid
from googleapiclient.discovery import build

GMAIL_KEYWORDS = ["material", "substitution", "change", "approval", "RFI"]
GMAIL_QUERY = "is:unread (" + " OR ".join(GMAIL_KEYWORDS) + ")"


def poll_gmail(publish_fn=publish_event) -> list[str]:
    """Poll for unread material-related emails. Returns list of message_ids published."""
    service = _build_gmail_service()
    results = service.users().messages().list(
        userId="me",
        q=GMAIL_QUERY,
        maxResults=50,
    ).execute()

    messages = results.get("messages", [])
    published_ids = []
    for msg in messages:
        full_msg = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="full",
        ).execute()

        raw_event = RawEvent(
            event_id=str(uuid.uuid4()),
            source="gmail",
            raw_payload={"gmail_message_id": msg["id"], "message": full_msg},
        )
        message_id = publish_fn(raw_event)
        published_ids.append(message_id)
    return published_ids
```

Notes:
- `users().messages().list()` returns only `id` and `threadId` — a second `messages().get()` call is required for full content.
- `format="full"` returns the full message with payload and headers.
- `maxResults` default is 100, max is 500.
- Pagination via `nextPageToken` is omitted for Phase 1 (handled if needed).

### Pattern 5: Google Calendar Polling with Time Window

**What:** Use `events().list()` with `timeMin`/`timeMax` as RFC3339 timestamps, `singleEvents=True` to expand recurring events, then filter by keyword in summary/description.

**When to use:** `poll_calendar()` standalone function with 7-day look-ahead.

**Example:**
```python
# Source: https://googleapis.github.io/google-api-python-client/docs/dyn/calendar_v3.events.html
import uuid
from datetime import datetime, timedelta, timezone

CALENDAR_KEYWORDS = {"delivery", "installation", "material", "inspection"}


def poll_calendar(publish_fn=publish_event) -> list[str]:
    """Poll calendar for delivery/installation events in next 7 days."""
    service = _build_calendar_service()
    now = datetime.now(timezone.utc)
    time_max = now + timedelta(days=7)

    events_result = service.events().list(
        calendarId="primary",
        timeMin=now.isoformat(),
        timeMax=time_max.isoformat(),
        singleEvents=True,
        orderBy="startTime",
        maxResults=50,
    ).execute()

    items = events_result.get("items", [])
    published_ids = []
    for event in items:
        summary = event.get("summary", "").lower()
        description = event.get("description", "").lower()
        text = summary + " " + description
        if any(kw in text for kw in CALENDAR_KEYWORDS):
            raw_event = RawEvent(
                event_id=str(uuid.uuid4()),
                source="calendar",
                raw_payload=event,
            )
            message_id = publish_fn(raw_event)
            published_ids.append(message_id)
    return published_ids
```

Notes:
- `timeMin` and `timeMax` must be RFC3339 strings — `datetime.isoformat()` on a timezone-aware datetime produces the correct format (`+00:00` suffix, which GCP accepts).
- `singleEvents=True` is required when using `orderBy="startTime"`.
- `orderBy="startTime"` requires `singleEvents=True` (API returns error otherwise).

### Anti-Patterns to Avoid

- **Publishing strings instead of bytes:** `publisher.publish(topic, "some string")` raises `TypeError`. Always `.encode("utf-8")`.
- **Not calling `future.result()`:** The publish is fire-and-forget without it. Errors are silently lost.
- **Building service clients at module level:** `googleapiclient.discovery.build()` makes network calls. Build inside the function or use lazy initialization to avoid import-time failures.
- **Using `datetime.utcnow().isoformat() + "Z"`:** Produces a naive datetime string. Prefer `datetime.now(timezone.utc).isoformat()` for RFC3339-compliant output.
- **Calling `creds.refresh()` once globally:** Access tokens expire after 1 hour. The `google-api-python-client` library auto-refreshes if you pass valid `Credentials` — but if you cache `creds` across long-lived processes, verify the library's auto-refresh behavior.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Topic path formatting | `f"projects/{proj}/topics/{topic}"` | `publisher.topic_path(project, topic)` | Official method validates format; avoids typos in path |
| Message serialization | Custom binary encoding | `json.dumps(...).encode("utf-8")` | Pub/Sub is schema-agnostic; JSON is downstream-parsable |
| Access token refresh | Manual HTTP call to token endpoint | `creds.refresh(Request())` or auto-refresh via google-api-python-client | Library handles expiry, retry, transport |
| Gmail query construction | Parsing email headers manually | Gmail `q=` parameter with `is:unread` syntax | Server-side filtering; no wasted API calls on irrelevant messages |
| Calendar time filtering | Fetching all events and filtering locally | `timeMin`/`timeMax` params in `events().list()` | Server-side filtering; handles recurring events correctly |
| UUID generation | Custom ID schemes | `str(uuid.uuid4())` | Already used in Phase 0 pattern for event_id |

**Key insight:** The Google API client libraries handle HTTP transport, retry on 5xx, credential refresh, and pagination token management. Do not reimplement any of these.

---

## Common Pitfalls

### Pitfall 1: `google-api-python-client` Not in requirements.txt

**What goes wrong:** `ImportError: No module named 'googleapiclient'` at runtime.

**Why it happens:** `google-cloud-pubsub` and `google-auth` are listed but `google-api-python-client` (which provides `googleapiclient.discovery`) is not.

**How to avoid:** Add `google-api-python-client>=2.115` and `google-auth-httplib2>=0.2.0` to `requirements.txt` before implementing the connectors.

**Warning signs:** Import error in `gmail.py` or `calendar.py` on first run.

### Pitfall 2: RawEvent `raw_payload` Must Be a dict, Not Bytes

**What goes wrong:** `RawEvent(source="fireflies", raw_payload=await request.body())` raises `ValidationError` because the Pydantic model defines `raw_payload: dict`.

**Why it happens:** `request.body()` returns `bytes`; `request.json()` returns `dict`.

**How to avoid:** Always use `await request.json()` and pass the resulting dict to `raw_payload`. The raw bytes are not needed for Phase 1.

**Warning signs:** `pydantic.ValidationError: raw_payload: Input should be a valid dictionary`.

### Pitfall 3: `GOOGLE_CLOUD_PROJECT` Empty at Runtime Causes Silent Pub/Sub Failures

**What goes wrong:** `publisher.topic_path("", "raw-events")` produces `"projects//topics/raw-events"` — an invalid path. Publish calls raise `google.api_core.exceptions.NotFound`.

**Why it happens:** `settings.google_cloud_project` has a default of `""` in `config/settings.py` (not a required field). If not set in `.env`, it silently uses empty string.

**How to avoid:** In the `publish_event()` helper, assert `settings.google_cloud_project` is non-empty before constructing the topic path. Or make `google_cloud_project` a required field in `Settings`.

**Warning signs:** `404 Resource not found: projects//topics/raw-events`.

### Pitfall 4: `singleEvents` Required for `orderBy="startTime"`

**What goes wrong:** Calendar API returns `400 Bad Request: "orderBy" requires "singleEvents=True"` when both are set.

**Why it happens:** Recurring event series cannot be ordered by start time without expansion.

**How to avoid:** Always set `singleEvents=True` when using `orderBy="startTime"`.

### Pitfall 5: Pub/Sub Future Not Awaited Masks Publish Errors

**What goes wrong:** Endpoint returns 200 but the message was never actually published.

**Why it happens:** `publisher.publish()` is asynchronous internally. Without `.result()`, failures (topic not found, quota exceeded) are silently dropped.

**How to avoid:** Always call `future.result()` in `publish_event()`. Wrap in try/except to return structured error to the webhook caller.

### Pitfall 6: `model_dump()` Returns `datetime` Objects, Breaking `json.dumps()`

**What goes wrong:** `json.dumps(raw_event.model_dump())` raises `TypeError: Object of type datetime is not JSON serializable`.

**Why it happens:** `RawEvent.received_at` is a `datetime` field. `model_dump()` without `mode="json"` returns the Python `datetime` object.

**How to avoid:** Use `raw_event.model_dump(mode="json")` which converts `datetime` to ISO strings, or pass `default=str` to `json.dumps()`.

---

## Code Examples

Verified patterns from official sources:

### Pub/Sub: Publish with Attributes and Get message_id

```python
# Source: https://docs.cloud.google.com/python/docs/reference/pubsub/latest/google.cloud.pubsub_v1.publisher.client.Client
from google.cloud import pubsub_v1
import json

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path("my-project", "raw-events")

data = json.dumps({"event_id": "abc", "source": "fireflies"}).encode("utf-8")
future = publisher.publish(topic_path, data, source="fireflies")
message_id = future.result()  # str, e.g. "1234567890"
```

### Gmail: List Unread Messages Matching Query

```python
# Source: https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/list
results = service.users().messages().list(
    userId="me",
    q="is:unread (material OR substitution OR RFI)",
    maxResults=50,
).execute()
messages = results.get("messages", [])  # list of {"id": ..., "threadId": ...}

# Fetch full message content
full = service.users().messages().get(userId="me", id=messages[0]["id"], format="full").execute()
```

### Calendar: List Events in 7-Day Window

```python
# Source: https://googleapis.github.io/google-api-python-client/docs/dyn/calendar_v3.events.html
from datetime import datetime, timedelta, timezone

now = datetime.now(timezone.utc)
events_result = service.events().list(
    calendarId="primary",
    timeMin=now.isoformat(),
    timeMax=(now + timedelta(days=7)).isoformat(),
    singleEvents=True,
    orderBy="startTime",
).execute()
items = events_result.get("items", [])
```

### OAuth2 Credentials from Stored Refresh Token

```python
# Source: https://googleapis.dev/python/google-auth/latest/reference/google.oauth2.credentials.html
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

creds = Credentials(
    token=None,
    refresh_token="stored_refresh_token",
    token_uri="https://oauth2.googleapis.com/token",
    client_id="client_id.apps.googleusercontent.com",
    client_secret="client_secret",
)
creds.refresh(Request())  # Obtains a valid access_token
```

### FastAPI Router + include_router

```python
# Source: https://fastapi.tiangolo.com/reference/apirouter/
from fastapi import FastAPI, APIRouter

router = APIRouter()

@router.post("/webhooks/fireflies")
async def receive_fireflies(request: Request) -> dict: ...

# In main.py:
app = FastAPI()
app.include_router(router)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `datetime.utcnow().isoformat() + "Z"` | `datetime.now(timezone.utc).isoformat()` | Python 3.11 deprecation of utcnow() | RFC3339-compliant; no DeprecationWarning in Python 3.12+ |
| `model.dict()` (Pydantic v1) | `model.model_dump(mode="json")` (Pydantic v2) | Pydantic v2.0 (2023) | Required — `dict()` raises PydanticUserError in v2 |
| `@validator` (Pydantic v1) | `@field_validator` + `@classmethod` (Pydantic v2) | Pydantic v2.0 (2023) | Already established in Phase 0 |
| `google.cloud.pubsub_v1.PublisherClient()` with service account JSON file | Default Application Default Credentials (ADC) for Cloud Run | Current (2024) | In Cloud Run, no credentials file needed — ADC auto-detects the service account |

**Deprecated/outdated:**
- `model.dict()`: Raises `PydanticUserError` in this project (see STATE.md). Use `model.model_dump()`.
- `datetime.utcnow()`: Deprecated in Python 3.12. Use `datetime.now(timezone.utc)`.

---

## Open Questions

1. **`google-api-python-client` must be added to `requirements.txt`**
   - What we know: The package is not listed but is required for `googleapiclient.discovery.build()`.
   - What's unclear: Whether the project's virtual environment already has it installed as a transitive dependency.
   - Recommendation: Explicitly add `google-api-python-client>=2.115` and `google-auth-httplib2>=0.2.0` to `requirements.txt` in Wave 0 of the plan.

2. **`GMAIL_REFRESH_TOKEN` not yet populated in developer's `.env`**
   - What we know: The field is defined in `config/settings.py` and `.env.example`. It has a default of `""`.
   - What's unclear: Whether the developer has a valid refresh token for testing.
   - Recommendation: The plan should include a setup note: obtain a refresh token via `google-auth-oauthlib` `InstalledAppFlow` once; store in `.env`. Connector tests can mock the credential layer.

3. **Fireflies webhook payload schema**
   - What we know: Fireflies sends a JSON payload; the validation rule is "must have transcript data or meeting info".
   - What's unclear: The exact field names in the Fireflies webhook payload (e.g., `transcript`, `meeting`, `meetingId`). No official schema was found.
   - Recommendation: Validate permissively in Phase 1 — check that `body` is a non-empty dict with at least one of `["transcript", "meeting", "meetingId", "id"]`. Full schema validation is Phase 7.

4. **ACC webhook payload schema**
   - What we know: ACC sends construction project events; the validation rule is "must be a valid ACC event structure".
   - What's unclear: The exact field names (e.g., `eventType`, `resource`, `payload`).
   - Recommendation: Same permissive approach — validate that `body` is a non-empty dict. Full ACC schema validation deferred to Phase 7.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ (pyproject.toml `[tool.pytest.ini_options]`) |
| Config file | `pyproject.toml` — `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/unit/test_input_layer.py -x` |
| Full suite command | `pytest tests/ -x --ignore=tests/integration` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INPUT-01 | POST /webhooks/fireflies with valid payload returns 200 and publishes to Pub/Sub | unit | `pytest tests/unit/test_webhooks.py::test_fireflies_valid -x` | Wave 0 |
| INPUT-01 | POST /webhooks/fireflies with missing transcript/meeting returns 400 | unit | `pytest tests/unit/test_webhooks.py::test_fireflies_invalid -x` | Wave 0 |
| INPUT-02 | POST /webhooks/acc with valid payload returns 200 and publishes | unit | `pytest tests/unit/test_webhooks.py::test_acc_valid -x` | Wave 0 |
| INPUT-02 | POST /webhooks/acc with empty body returns 400 | unit | `pytest tests/unit/test_webhooks.py::test_acc_invalid -x` | Wave 0 |
| INPUT-03 | poll_gmail() with mocked Gmail service publishes matching emails | unit | `pytest tests/unit/test_connectors.py::test_poll_gmail -x` | Wave 0 |
| INPUT-03 | poll_gmail() with no matching emails publishes nothing | unit | `pytest tests/unit/test_connectors.py::test_poll_gmail_no_match -x` | Wave 0 |
| INPUT-04 | poll_calendar() with mocked Calendar service publishes matching events | unit | `pytest tests/unit/test_connectors.py::test_poll_calendar -x` | Wave 0 |
| INPUT-04 | poll_calendar() filters events outside keyword list | unit | `pytest tests/unit/test_connectors.py::test_poll_calendar_no_match -x` | Wave 0 |
| INPUT-01/02 | publish_event() serializes RawEvent to bytes and returns message_id | unit | `pytest tests/unit/test_pubsub.py::test_publish_event -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/unit/test_input_layer.py tests/unit/test_webhooks.py tests/unit/test_connectors.py tests/unit/test_pubsub.py -x`
- **Per wave merge:** `pytest tests/ -x --ignore=tests/integration`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/unit/test_webhooks.py` — covers INPUT-01, INPUT-02 webhook endpoints via `httpx.AsyncClient`
- [ ] `tests/unit/test_connectors.py` — covers INPUT-03, INPUT-04 polling functions with mocked Google API services
- [ ] `tests/unit/test_pubsub.py` — covers `publish_event()` helper with mocked `PublisherClient`
- [ ] `tests/conftest.py` — add `mock_pubsub_publisher` and `mock_gmail_service` fixtures

**Mock strategy for tests:**
- Pub/Sub: `unittest.mock.patch("src.input.pubsub.pubsub_v1.PublisherClient")` — mock `publish()` to return a mock future with `.result()` returning `"test-message-id"`.
- Gmail: Pass a mock `publish_fn` to `poll_gmail(publish_fn=mock_publish)` via dependency injection; mock `_build_gmail_service()` with `patch.object`.
- Calendar: Same pattern — inject mock `publish_fn`; mock `_build_calendar_service()`.
- FastAPI: Use `httpx.AsyncClient(app=app, base_url="http://test")` for webhook endpoint tests.

---

## Sources

### Primary (HIGH confidence)

- [Python PublisherClient API Reference](https://docs.cloud.google.com/python/docs/reference/pubsub/latest/google.cloud.pubsub_v1.publisher.client.Client) — `publish()` signature, `topic_path()`, future return
- [Gmail users.messages.list API Reference](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/list) — `q` parameter, response structure
- [Calendar events.list API Reference](https://googleapis.github.io/google-api-python-client/docs/dyn/calendar_v3.events.html) — `timeMin`, `timeMax`, `singleEvents`, `orderBy`
- [google.oauth2.credentials Reference](https://googleapis.dev/python/google-auth/latest/reference/google.oauth2.credentials.html) — `Credentials` constructor with `refresh_token`
- `config/settings.py` (project) — confirms `google_cloud_project`, `pubsub_topic_raw_events`, `gmail_client_id`, `gmail_client_secret`, `gmail_refresh_token` field names
- `src/shared/models/events.py` (project) — confirms `RawEvent` schema: `event_id: str`, `source: Literal[...]`, `raw_payload: dict`, `received_at: datetime`

### Secondary (MEDIUM confidence)

- [FastAPI APIRouter Reference](https://fastapi.tiangolo.com/reference/apirouter/) — `include_router()`, `@router.post()` patterns; verified against FastAPI 0.109 in requirements.txt
- [Pub/Sub Publish Messages Guide](https://docs.cloud.google.com/pubsub/docs/publisher) — batching behavior, message attributes, future pattern

### Tertiary (LOW confidence)

- Fireflies webhook payload schema — not found in official docs; only community examples. Validate permissively.
- ACC webhook payload schema — not investigated; treat as opaque dict in Phase 1.

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — all packages verified against requirements.txt and official docs; one gap identified (`google-api-python-client` missing)
- Architecture: HIGH — patterns verified against official Python client library docs and FastAPI docs
- Pub/Sub publish pattern: HIGH — verified against official Python client reference (version 2.34.0)
- Gmail/Calendar polling: HIGH — verified against Google Workspace API reference and google-auth docs
- OAuth2 refresh token flow: HIGH — verified against google-auth 2.47.0 docs
- Pitfalls: HIGH — sourced from official docs, project STATE.md known gotchas, and API error message analysis
- Webhook payload schemas (Fireflies, ACC): LOW — no official schema documentation found

**Research date:** 2026-03-13
**Valid until:** 2026-04-13 (stable APIs; google-cloud-pubsub and google-api-python-client change slowly)
