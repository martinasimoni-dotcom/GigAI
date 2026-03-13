# Phase 7: Output + API — Context

**Gathered:** 2026-03-13
**Status:** Ready for planning
**Source:** PRD Express Path (CLAUDE_PLAN.md)

<domain>
## Phase Boundary

Phase 7 delivers the complete OUTPUT layer of the GigAI pipeline plus the FastAPI REST API:

1. **Proposal Builder** (OUT-01): `src/output/proposal_builder/builder.py` — formats Proposal objects for dashboard consumption
2. **Action Gateway** (OUT-02): `src/output/action_gateway/gateway.py` — routes approved actions to executors in parallel, handles partial failures
3. **ACC Executor** (OUT-03): `src/output/action_gateway/acc_executor.py` — ACC API calls (RFIs, tasks, issues, drawing markups)
4. **Gmail Executor** (OUT-04): `src/output/action_gateway/gmail_executor.py` — sends stakeholder emails via Gmail API
5. **Calendar Executor** (OUT-05): `src/output/action_gateway/calendar_executor.py` — creates follow-up calendar events
6. **Document Executor** (OUT-06): `src/output/action_gateway/document_executor.py` — ACC Document/Markup API for drawing annotations
7. **Dashboard Notifier** (OUT-07): `src/output/notifications/dashboard_notifier.py` — real-time push notifications to dashboard (WebSocket/SSE)
8. **ACC Notifier** (OUT-08): `src/output/notifications/acc_notifier.py` — secondary ACC notifications
9. **Email Notifier** (OUT-09): `src/output/notifications/email_notifier.py` — fallback email alerts
10. **Feedback Loop** (OUT-10): `src/output/feedback/feedback_loop.py` — logs decisions to PostgreSQL, embeds as pgvector patterns
11. **FastAPI Routes** (OUT-11): `src/api/routes.py` — all REST endpoints (proposals, decisions, feedback, health)
12. **FastAPI Middleware** (OUT-12): `src/api/middleware.py` — authentication, CORS, structured error handling

Also delivers:
- `src/output/__init__.py`, `src/output/proposal_builder/__init__.py`, `src/output/action_gateway/__init__.py`
- `src/output/notifications/__init__.py`, `src/output/feedback/__init__.py`
- `src/api/__init__.py`
- Unit tests for gateway, feedback_loop, and routes

</domain>

<decisions>
## Implementation Decisions

### Proposal Builder (OUT-01)
- File: `src/output/proposal_builder/builder.py`
- Function: `build_proposal_response(proposal: Proposal) -> dict`
- Formats a Proposal object into a dashboard-ready dict with: id, event_id, alert, actions (formatted), confidence_score (as percentage), recommendation, created_at
- Uses existing `Proposal` model from `src/shared/models/proposals.py`
- `src/output/proposal_builder/__init__.py` exports `build_proposal_response`

### Action Gateway (OUT-02)
- File: `src/output/action_gateway/gateway.py`
- Function: `execute_actions(proposal: Proposal) -> ExecutionResult`
- `ExecutionResult`: Pydantic v2 model with `proposal_id: str`, `results: list[ActionResult]`, `success_count: int`, `failure_count: int`
- `ActionResult`: Pydantic v2 model with `action_type: str`, `status: Literal["success", "failed", "skipped"]`, `message: str`, `error: str | None`
- Runs all executors in **parallel** using `asyncio.gather(*tasks, return_exceptions=True)` — if one fails, others continue
- Routes action_type → executor function: email→gmail_executor, task→acc_executor, calendar→calendar_executor, drawing→document_executor
- External API calls use stub implementations that log and return success (real credentials from .env, fallback to stub if not set)

### ACC Executor (OUT-03)
- File: `src/output/action_gateway/acc_executor.py`
- Function: `execute_acc_action(action: Action) -> ActionResult`
- Creates ACC task or RFI using ACC API (`ACC_TOKEN`, `ACC_ACCOUNT_ID` from env)
- If ACC credentials not set: log warning + return stub success (for demo without live ACC)
- Handles action_type "task": POST to ACC tasks endpoint
- Demo: creates task for Mike Torres (procurement) with description from action_data

### Gmail Executor (OUT-04)
- File: `src/output/action_gateway/gmail_executor.py`
- Function: `execute_gmail_action(action: Action) -> ActionResult`
- Sends email via Gmail API using service account credentials (`GMAIL_CREDENTIALS_JSON` from env)
- If Gmail credentials not set: log warning + return stub success
- Demo: sends email to Jane Miller (supplier) about window substitution

### Calendar Executor (OUT-05)
- File: `src/output/action_gateway/calendar_executor.py`
- Function: `execute_calendar_action(action: Action) -> ActionResult`
- Creates calendar event via Google Calendar API (`GOOGLE_CALENDAR_ID`, `GMAIL_CREDENTIALS_JSON` from env)
- If credentials not set: stub success
- Demo: creates 3-day follow-up event for window substitution review

### Document Executor (OUT-06)
- File: `src/output/action_gateway/document_executor.py`
- Function: `execute_document_action(action: Action) -> ActionResult`
- Adds markup to ACC drawing via ACC Document/Markup API
- If ACC credentials not set: stub success
- Demo: markup on drawing A-301 for window substitution annotation

### Dashboard Notifier (OUT-07)
- File: `src/output/notifications/dashboard_notifier.py`
- Function: `notify_dashboard(proposal_response: dict) -> None`
- Uses Server-Sent Events (SSE) via a shared in-memory event queue
- `get_event_stream()` — async generator yielding SSE data for FastAPI `/api/events` endpoint
- `notify_dashboard()` — pushes proposal to the event queue
- No external dependencies — pure in-memory SSE pattern

### ACC Notifier (OUT-08)
- File: `src/output/notifications/acc_notifier.py`
- Function: `notify_acc(proposal: Proposal) -> None`
- Posts ACC issue/comment as notification via ACC API
- If ACC credentials not set: stub (log only)

### Email Notifier (OUT-09)
- File: `src/output/notifications/email_notifier.py`
- Function: `notify_email(proposal: Proposal, recipient: str) -> None`
- Sends fallback email notification when dashboard unavailable
- Uses Gmail executor pattern (reuses GMAIL_CREDENTIALS_JSON)
- If no credentials: stub (log only)

### Feedback Loop (OUT-10)
- File: `src/output/feedback/feedback_loop.py`
- Function: `record_decision(proposal_id: str, decision: str, reason: str | None, proposal: Proposal) -> None`
- Stores decision in PostgreSQL `decisions` table: (proposal_id, decision, reason, timestamp, event_id)
- Embeds the decision pattern in pgvector using `src/shared/db/vector_store.py` `upsert()` or `add_documents()`
- Check actual vector_store.py write function name before implementing
- If DB not configured: log only (no crash) — uses `DATABASE_URL` from env
- `decisions` table creation: `CREATE TABLE IF NOT EXISTS decisions (id SERIAL PRIMARY KEY, proposal_id TEXT, event_id TEXT, decision TEXT, reason TEXT, created_at TIMESTAMPTZ DEFAULT NOW())`

### FastAPI Routes (OUT-11)
- File: `src/api/routes.py`
- Router: `APIRouter` with prefix `/api`
- Endpoints:
  - `GET /api/health` — returns `{"status": "ok", "version": "0.1.0"}`
  - `GET /api/proposals` — returns list of recent proposals from in-memory store (list of proposal_response dicts)
  - `POST /api/proposals/{proposal_id}/decision` — accepts `{"decision": "accept"|"reject", "reason": str|null}`, runs action gateway if accept, records feedback, returns ExecutionResult
  - `GET /api/events` — SSE stream endpoint using `EventSourceResponse` from `sse-starlette`
- In-memory proposal store: module-level `_proposals: list[dict]` (populated by `store_proposal()` function)
- `store_proposal(proposal_response: dict)` — appends to `_proposals` and calls `notify_dashboard()`
- Response within 2 seconds for GET/POST (external API calls in background or with timeout)

### FastAPI Middleware (OUT-12)
- File: `src/api/middleware.py`
- CORS: `CORSMiddleware` with `allow_origins=["*"]` (dev), `allow_methods=["*"]`, `allow_headers=["*"]`
- Auth: Simple API key middleware — checks `X-API-Key` header against `API_KEY` env var. If `API_KEY` not set: skip auth (dev mode). Health endpoint always public.
- Error handler: `@app.exception_handler(Exception)` returning `{"error": str(e), "type": type(e).__name__}` with 500 status
- `src/main.py` wiring: `app.add_middleware(CORSMiddleware, ...)` + include router from routes.py

### Package `__init__.py` files
- `src/output/__init__.py` — empty (marks package)
- `src/output/proposal_builder/__init__.py` — exports `build_proposal_response`
- `src/output/action_gateway/__init__.py` — exports `execute_actions`, `ExecutionResult`, `ActionResult`
- `src/output/notifications/__init__.py` — exports `notify_dashboard`, `get_event_stream`
- `src/output/feedback/__init__.py` — exports `record_decision`
- `src/api/__init__.py` — empty (marks package)

### Claude's Discretion
- Exact SSE implementation (asyncio.Queue vs list-based event store)
- Whether to create decisions table at module load or lazily
- Exact parallel execution pattern (asyncio.gather vs ThreadPoolExecutor — prefer asyncio.gather with async wrappers)
- Executor function signatures (sync vs async — prefer sync with async wrapper in gateway)
- How to serialize Action objects for executor dispatch
- Test isolation pattern for DB/external API calls

</decisions>

<specifics>
## Specific Requirements

- Demo: accept proposal → parallel execution of 4 actions: email to Jane Miller, task for Mike Torres, calendar follow-up, drawing markup on A-301
- Partial failure: if ACC fails, Gmail + Calendar still succeed; failure reported per-action in ExecutionResult
- All external API calls: stub if credentials not set (no crash, log warning)
- `sse-starlette` for SSE: `pip install sse-starlette` (or check requirements.txt)
- `src/shared/db/vector_store.py` — check upsert/write function name before using in feedback_loop
- `src/shared/llm/voyage.py` — used in feedback_loop for embedding decision patterns
- Pydantic v2 for ExecutionResult, ActionResult
- No OpenAI, no spaCy, all secrets in .env
- Tests: mock DB, mock external APIs, no live calls
- `src/main.py` already exists (from Phase 1 input layer) — extend it, don't replace
- Decision table DDL runs with `CREATE TABLE IF NOT EXISTS` (idempotent)
- `X-API-Key` auth header; skip if `API_KEY` env not set (dev mode)

</specifics>

<deferred>
## Deferred Ideas

- Real Gmail OAuth2 flow — Phase 9+ demo setup
- Real Google Calendar OAuth2 — Phase 9+ demo setup
- Real ACC API (live token) — Phase 9+ demo setup
- WebSocket bidirectional push — v2
- Proposal persistence to PostgreSQL — v2
- Background task queue (Celery/RQ) for execution — v2
- Rate limiting middleware — v2

</deferred>

---

*Phase: 07-output-api*
*Context gathered: 2026-03-13 via PRD Express Path*
