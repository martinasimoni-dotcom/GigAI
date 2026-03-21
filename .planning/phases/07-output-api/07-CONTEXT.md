# Phase 7: Output + API — Context

**Gathered:** 2026-03-13
**Status:** Ready for planning (revised — real ACC integration)
**Source:** PRD Express Path (CLAUDE_PLAN.md)

<domain>
## Phase Boundary

Phase 7 delivers the complete OUTPUT layer plus FastAPI REST API. All external API calls
are real — no stubs, no silent fallbacks. Missing credentials raise errors.

1. **Proposal Builder** (OUT-01): `src/output/proposal_builder/builder.py`
2. **Action Gateway** (OUT-02): `src/output/action_gateway/gateway.py` — parallel dispatch
3. **ACC Executor** (OUT-03): `src/output/action_gateway/acc_executor.py` — real ACC Issues API
4. **Gmail Executor** (OUT-04): `src/output/action_gateway/gmail_executor.py` — real Gmail API
5. **Calendar Executor** (OUT-05): `src/output/action_gateway/calendar_executor.py` — real Google Calendar API
6. **Document Executor** (OUT-06): `src/output/action_gateway/document_executor.py` — real ACC Markup API
7. **Dashboard Notifier** (OUT-07): `src/output/notifications/dashboard_notifier.py` — SSE push
8. **ACC Notifier** (OUT-08): `src/output/notifications/acc_notifier.py` — real ACC Notifications API
9. **Email Notifier** (OUT-09): `src/output/notifications/email_notifier.py` — real Gmail API
10. **Feedback Loop** (OUT-10): `src/output/feedback/feedback_loop.py` — PostgreSQL + pgvector
11. **FastAPI Routes** (OUT-11): `src/api/routes.py`
12. **FastAPI Middleware** (OUT-12): `src/api/middleware.py`

Also delivers all package `__init__.py` files and extends `src/main.py`.

</domain>

<decisions>
## Implementation Decisions

### Shared ACC client
- Already implemented: `src/shared/clients/acc.py`
- `_get_acc_token()` — 2-legged OAuth2 with in-process token cache
- Functions: `get_floor_plan()`, `get_schedule_activities()`, `create_issue()`, `create_drawing_markup()`, `send_acc_notification()`
- Raises `RuntimeError` if `ACC_CLIENT_ID` / `ACC_CLIENT_SECRET` not set — never silently stubs

### Proposal Builder (OUT-01)
- File: `src/output/proposal_builder/builder.py`
- Function: `build_proposal_response(proposal: Proposal) -> dict`
- Returns dashboard-ready dict: id, event_id, alert, actions (formatted), confidence_score (percentage 0-100), recommendation, created_at (ISO timestamp)
- Imports `Proposal` from `src/shared/models/proposals.py`

### Action Gateway (OUT-02)
- File: `src/output/action_gateway/gateway.py`
- Function: `execute_actions(proposal: Proposal) -> ExecutionResult`
- `ExecutionResult`: Pydantic v2 — `proposal_id: str`, `results: list[ActionResult]`, `success_count: int`, `failure_count: int`
- `ActionResult`: Pydantic v2 — `action_type: str`, `status: Literal["success","failed"]`, `message: str`, `error: str | None`
- Runs all executors in parallel via `asyncio.gather(*tasks, return_exceptions=True)`
- One executor failing does NOT stop others — exception becomes `ActionResult(status="failed", error=str(exc))`
- Routes: `"email"` → gmail_executor, `"task"` → acc_executor, `"calendar"` → calendar_executor, `"drawing"` → document_executor

### ACC Executor (OUT-03)
- File: `src/output/action_gateway/acc_executor.py`
- Function: `execute_acc_action(action: Action) -> ActionResult`
- Uses `src.shared.clients.acc.create_issue()`
- Reads `ACC_PROJECT_ID`, `ACC_ISSUES_CONTAINER_ID` from env
- `action.action_data` must contain: `title`, `description`, optionally `assignee_id`, `due_date`
- Raises (caught → ActionResult failed) if credentials not set
- Returns `ActionResult(status="success", message=f"ACC issue created: {issue_id}")`

### Gmail Executor (OUT-04)
- File: `src/output/action_gateway/gmail_executor.py`
- Function: `execute_gmail_action(action: Action) -> ActionResult`
- Uses Gmail API v1 via `google-api-python-client`
- OAuth2 refresh token flow: `google.oauth2.credentials.Credentials` from `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`
- Sends email via `POST /gmail/v1/users/me/messages/send` with base64url-encoded RFC 2822 message
- `action.action_data` must contain: `to`, `subject`, `body`
- Raises (caught → ActionResult failed) if credentials not set

### Calendar Executor (OUT-05)
- File: `src/output/action_gateway/calendar_executor.py`
- Function: `execute_calendar_action(action: Action) -> ActionResult`
- Uses Google Calendar API v3 via `google-api-python-client` (same credentials as Gmail)
- Creates event in `GOOGLE_CALENDAR_ID` calendar
- `action.action_data` must contain: `summary`, `description`, `start_datetime` (ISO 8601), `end_datetime` (ISO 8601)
- Raises (caught → ActionResult failed) if credentials not set

### Document Executor (OUT-06)
- File: `src/output/action_gateway/document_executor.py`
- Function: `execute_document_action(action: Action) -> ActionResult`
- Uses `src.shared.clients.acc.create_drawing_markup()`
- Reads `ACC_PROJECT_ID` from env
- `action.action_data` must contain: `drawing_number`, `annotation_text`, optionally `version_urn`
- Raises (caught → ActionResult failed) if credentials not set

### Dashboard Notifier (OUT-07)
- File: `src/output/notifications/dashboard_notifier.py`
- Pure in-process SSE — no external API
- `notify_dashboard(proposal_response: dict) -> None` — pushes to `asyncio.Queue`
- `get_event_stream()` — async generator yielding SSE-formatted strings for FastAPI StreamingResponse

### ACC Notifier (OUT-08)
- File: `src/output/notifications/acc_notifier.py`
- Function: `notify_acc(proposal: Proposal) -> None`
- Uses `src.shared.clients.acc.send_acc_notification()`
- Reads `ACC_ACCOUNT_ID`, `ACC_PROJECT_ID` from env
- Raises RuntimeError if credentials not set

### Email Notifier (OUT-09)
- File: `src/output/notifications/email_notifier.py`
- Function: `notify_email(proposal: Proposal, recipient: str) -> None`
- Reuses Gmail executor pattern (same `GMAIL_CLIENT_ID/SECRET/REFRESH_TOKEN` credentials)
- Sends formatted fallback notification email

### Feedback Loop (OUT-10)
- File: `src/output/feedback/feedback_loop.py`
- Function: `record_decision(proposal_id: str, decision: str, reason: str | None, proposal: Proposal) -> None`
- DDL: `CREATE TABLE IF NOT EXISTS decisions (id SERIAL PRIMARY KEY, proposal_id TEXT, event_id TEXT, decision TEXT, reason TEXT, created_at TIMESTAMPTZ DEFAULT NOW())`
- Inserts row via `src.shared.db.postgres.get_connection()` / `release_connection()`
- Embeds decision text via `src.shared.db.vector_store` write function (check actual name)
- Raises if `DATABASE_URL` not set

### FastAPI Routes (OUT-11)
- File: `src/api/routes.py`
- `GET /api/health` — `{"status": "ok", "version": "0.1.0"}`
- `GET /api/proposals` — returns `_proposals` list
- `POST /api/proposals/{proposal_id}/decision` — `DecisionRequest(decision, reason)`, runs gateway if accept, records feedback
- `GET /api/events` — SSE stream via `StreamingResponse(get_event_stream())`
- `store_proposal(proposal_response: dict)` — appends to `_proposals`, calls `notify_dashboard()`

### FastAPI Middleware (OUT-12)
- File: `src/api/middleware.py`
- `CORSMiddleware`: `allow_origins=["*"]`, `allow_methods=["*"]`, `allow_headers=["*"]`
- `APIKeyMiddleware(BaseHTTPMiddleware)`: checks `X-API-Key` vs `API_KEY` env; 401 if set and mismatched; `/api/health` always public
- Global exception handler: `{"error": str(e), "type": type(e).__name__}` + HTTP 500

### Claude's Discretion
- Exact Gmail RFC 2822 message encoding (base64url)
- OAuth2 Credentials construction from refresh token (token_uri, scopes)
- asyncio.to_thread() wrappers for sync executor functions in gateway
- Test mocking strategy for Google API service objects and ACC client
- SSE queue maxsize

</decisions>

<specifics>
## Specific Requirements

- `src/shared/clients/acc.py` already exists — import and use in all ACC executors/notifiers
- Gmail/Calendar: `google.oauth2.credentials.Credentials(token=None, refresh_token=..., token_uri="https://oauth2.googleapis.com/token", client_id=..., client_secret=...)` then `.refresh(google.auth.transport.requests.Request())`
- `google-api-python-client` and `google-auth` already in requirements.txt; add `google-auth-oauthlib` if needed
- `sse-starlette>=1.6` must be added to requirements.txt
- NO stubs. NO silent fallbacks. Missing credentials = exception → ActionResult(status="failed") in gateway, or RuntimeError elsewhere
- Pydantic v2. No OpenAI. No spaCy. All secrets in .env.
- Tests: mock `src.shared.clients.acc` functions and `googleapiclient.discovery.build`; no live calls
- `src/main.py` must be extended — do NOT replace it

</specifics>

<deferred>
## Deferred Ideas

- WebSocket bidirectional push — v2
- Proposal persistence to PostgreSQL — v2
- Background task queue (Celery/RQ) for execution — v2
- Rate limiting middleware — v2
- 3-legged OAuth2 consent flow — refresh token is pre-obtained outside pipeline

</deferred>

---

*Phase: 07-output-api*
*Context gathered: 2026-03-13 via PRD Express Path — revised for real ACC/Gmail/Calendar integration*
