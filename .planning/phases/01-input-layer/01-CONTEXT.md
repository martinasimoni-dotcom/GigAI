# Phase 1: Input Layer — Context

**Gathered:** 2026-03-12
**Status:** Ready for planning
**Source:** PRD Express Path (CLAUDE_PLAN.md)

<domain>
## Phase Boundary

Phase 1 delivers all external event ingestion: two FastAPI webhook endpoints and two polling connectors, all publishing raw events to Google Cloud Pub/Sub.

- `POST /webhooks/fireflies` — receives Fireflies webhook payloads, validates, publishes to raw-events Pub/Sub topic within 5 seconds
- `POST /webhooks/acc` — receives ACC webhook payloads, validates, publishes to raw-events Pub/Sub topic
- Gmail polling connector — detects material-related emails in a monitored inbox, publishes to Pub/Sub
- Google Calendar polling connector — detects delivery/installation events on a monitored calendar, publishes to Pub/Sub
- `src/main.py` — FastAPI app wiring all endpoints

Nothing in Phase 1 processes events — it only ingests and publishes to the event bus.
</domain>

<decisions>
## Implementation Decisions

### Fireflies Webhook (INPUT-01)
- File: `src/input/webhooks/fireflies.py`
- Route: `POST /webhooks/fireflies`
- Validate incoming payload (must have transcript data or meeting info)
- Create a `RawEvent` with `source="fireflies"` and `raw_payload=request.body`
- Publish serialized RawEvent to Pub/Sub `PUBSUB_TOPIC_RAW_EVENTS` topic
- Must publish within 5 minutes of meeting end (per REQUIREMENTS.md INPUT-01)
- Return 200 on success, 400 on validation failure

### ACC Webhook (INPUT-02)
- File: `src/input/webhooks/acc.py`
- Route: `POST /webhooks/acc`
- Validate incoming payload (must be a valid ACC event structure)
- Create a `RawEvent` with `source="acc"` and `raw_payload=request.body`
- Publish serialized RawEvent to Pub/Sub raw-events topic
- Return 200 on success, 400 on validation failure

### Gmail Polling Connector (INPUT-03)
- File: `src/input/connectors/gmail.py`
- Use Google OAuth2 credentials (GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET from settings)
- Poll Gmail API for unread messages with material-related keywords
- Filter by subject/body keywords: "material", "substitution", "change", "approval", "RFI"
- For each matching email: create `RawEvent` with `source="gmail"`, publish to Pub/Sub
- Use `google-auth` + `google-api-python-client` packages
- Polling function callable as standalone (for Cloud Scheduler / Cloud Functions trigger)

### Calendar Polling Connector (INPUT-04)
- File: `src/input/connectors/calendar.py`
- Use Google OAuth2 credentials (GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET reused for Calendar)
- Poll Google Calendar API for upcoming events with delivery/installation keywords
- Filter by event title/description: "delivery", "installation", "material", "inspection"
- For each matching event: create `RawEvent` with `source="calendar"`, publish to Pub/Sub
- Look-ahead window: next 7 days of calendar events
- Polling function callable as standalone

### Pub/Sub Client
- Use `google-cloud-pubsub` Python package
- Publisher client initialized from `GOOGLE_CLOUD_PROJECT` and `PUBSUB_TOPIC_RAW_EVENTS` settings
- Helper function `publish_event(raw_event: RawEvent) -> str` returns message_id
- Serialize RawEvent to JSON bytes for publishing

### FastAPI App (src/main.py)
- Create FastAPI app instance
- Include webhook router from `src/input/webhooks/`
- Basic health check endpoint: `GET /health`
- All routes prefixed appropriately

### Package Structure
- `src/input/__init__.py`
- `src/input/webhooks/__init__.py`
- `src/input/connectors/__init__.py`

### Infrastructure
- `infra/pubsub/setup.sh` — bash script to create raw-events topic and subscription via `gcloud pubsub`

### Claude's Discretion
- Error handling: use Python stdlib logging with JSON formatter (established in Phase 0 pattern)
- Webhook secret validation: accept any non-empty payload for Phase 1 (full auth in Phase 7 middleware)
- Polling interval: left to caller (not embedded in connector code)
- Message attributes on Pub/Sub publish: include `source` as message attribute for filtering
</decisions>

<specifics>
## Specific Requirements

- Pub/Sub topic env var: `PUBSUB_TOPIC_RAW_EVENTS`
- Google Cloud project env var: `GOOGLE_CLOUD_PROJECT`
- Gmail credentials: `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`
- RawEvent source literals: `"fireflies"`, `"acc"`, `"gmail"`, `"calendar"` (already defined in Phase 0 models)
- Use `google-cloud-pubsub` (already in requirements.txt)
- Use `google-auth` (already in requirements.txt)
- FastAPI already in requirements.txt
- No OpenAI, no spaCy, no model training
- All secrets in .env, never hardcoded
- Pydantic v2 for any additional validation
</specifics>

<deferred>
## Deferred Ideas

- Cloud Functions deployment (infra/cloud_run/) — Phase 7+
- Full webhook signature verification (HMAC) — Phase 7 middleware
- Pub/Sub retry/dead-letter configuration — Phase 7+
- Gmail OAuth token refresh flow — Phase 7
- Multi-inbox / multi-calendar support — v2
</deferred>

---

*Phase: 01-input-layer*
*Context gathered: 2026-03-12 via PRD Express Path*
