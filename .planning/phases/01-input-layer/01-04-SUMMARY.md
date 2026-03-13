---
phase: 01-input-layer
plan: "04"
subsystem: input
tags: [gmail, google-calendar, polling, pubsub, connectors, google-api-python-client]

requires:
  - phase: 01-02
    provides: publish_event() helper for RawEvent publishing to Pub/Sub

provides:
  - poll_gmail() standalone function polling Gmail for unread material-related emails
  - poll_calendar() standalone function polling Google Calendar for delivery/installation events
  - Injectable publish_fn parameter on both connectors for full test isolation
  - GMAIL_KEYWORDS and GMAIL_QUERY constants for keyword-based email filtering
  - CALENDAR_KEYWORDS set for construction-relevant calendar event detection

affects:
  - 01-05 (Cloud Scheduler integration, if planned)
  - Any phase that orchestrates scheduled polling

tech-stack:
  added:
    - google-api-python-client>=2.115 (installed: 2.192.0)
    - google-auth>=2.27 (installed: 2.49.0)
    - google-auth-httplib2>=0.2.0 (installed: 0.3.0)
    - google-cloud-pubsub>=2.18 (installed for test env)
  patterns:
    - Lazy service client construction via _build_*_service() — not module-level
    - Injectable publish_fn for test isolation without patching global state
    - sys.modules.pop autouse fixture for settings-dependent module test isolation
    - datetime.now(timezone.utc) for RFC3339-compliant Calendar API time windows

key-files:
  created:
    - src/input/connectors/gmail.py
    - src/input/connectors/calendar.py
  modified:
    - tests/unit/test_connectors.py

key-decisions:
  - "sys.modules.pop autouse fixture required for connectors: importing them at test module level triggers config.settings singleton which fails without env vars — lazy imports inside test functions with autouse fixture setenv resolves this"
  - "Calendar uses singleEvents=True alongside orderBy=startTime — Calendar API requirement"
  - "Calendar uses datetime.now(timezone.utc) not datetime.utcnow() for RFC3339-compliant ISO strings"
  - "Both connectors reuse Gmail OAuth credentials (same Google account) for Calendar access"

patterns-established:
  - "Lazy service builder pattern: _build_*_service() called inside polling function body, never at module level"
  - "Injectable publish_fn=publish_event default allows production use and clean test mocking"
  - "Keyword filtering on combined summary+description text (lowercase) for Calendar events"

requirements-completed: [INPUT-03, INPUT-04]

duration: 5min
completed: 2026-03-13
---

# Phase 1 Plan 04: Gmail and Calendar Polling Connectors Summary

**Two polling-based input connectors using Google API Python client: poll_gmail() for unread material-related emails and poll_calendar() for delivery/installation events, both publishing RawEvents to Pub/Sub via injectable publish_fn**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-13T10:55:17Z
- **Completed:** 2026-03-13T11:00:12Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `poll_gmail()` polls Gmail for unread emails matching GMAIL_QUERY keyword filter and publishes one RawEvent per match with `source="gmail"` and `gmail_message_id` in payload
- `poll_calendar()` polls Calendar API for events in the next 7 days, filters by CALENDAR_KEYWORDS on summary+description, publishes one RawEvent per match with `source="calendar"`
- Both connectors use lazy service client construction and injectable `publish_fn` for complete test isolation
- 8/8 unit tests pass green (4 Gmail + 4 Calendar)

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement Gmail polling connector** - `c3c5cf0` (feat)
2. **Task 2: Implement Calendar polling connector** - `4bfa9b2` (feat)

**Plan metadata:** (docs commit, see below)

_Note: TDD tasks — tests written first (RED), then implementation (GREEN)_

## Files Created/Modified

- `src/input/connectors/gmail.py` - poll_gmail() with GMAIL_KEYWORDS, GMAIL_QUERY, lazy _build_gmail_service()
- `src/input/connectors/calendar.py` - poll_calendar() with CALENDAR_KEYWORDS, lazy _build_calendar_service(), RFC3339-compliant time window
- `tests/unit/test_connectors.py` - Full 8-test suite replacing skip stubs; autouse fixture for settings isolation

## Decisions Made

- Test file uses lazy imports (inside test functions) rather than module-level imports to avoid settings singleton triggering at collection time. Autouse fixture sets env vars and pops sys.modules before each test.
- Calendar credentials reuse Gmail OAuth settings (gmail_client_id, gmail_client_secret, gmail_refresh_token) since same Google account.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed missing google-api-python-client and google-auth packages**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** ModuleNotFoundError: No module named 'google' — packages in requirements.txt but not installed in active Python environment
- **Fix:** Installed google-api-python-client, google-auth, google-auth-httplib2, google-auth-oauthlib via pip
- **Files modified:** None (pip install only)
- **Verification:** Tests pass after install
- **Committed in:** c3c5cf0 (implicit — dependency install, not a code change)

**2. [Rule 3 - Blocking] Installed missing google-cloud-pubsub package**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** ImportError: cannot import name 'pubsub_v1' from 'google.cloud' — pubsub package not installed
- **Fix:** Installed google-cloud-pubsub via pip
- **Files modified:** None (pip install only)
- **Verification:** Tests pass after install
- **Committed in:** c3c5cf0 (implicit)

**3. [Rule 1 - Bug] Restructured test file to use lazy imports with autouse fixture**
- **Found during:** Task 1 (RED phase)
- **Issue:** Top-level `import src.input.connectors.gmail as gmail_module` triggered settings singleton at collection time, failing with ValidationError before any fixture ran
- **Fix:** Moved module imports inside each test function; added autouse `setup_env` fixture that sets env vars and pops sys.modules before each test
- **Files modified:** tests/unit/test_connectors.py
- **Verification:** All 8 tests collect and pass
- **Committed in:** c3c5cf0

---

**Total deviations:** 3 auto-fixed (2 blocking dependency installs, 1 test isolation bug)
**Impact on plan:** All auto-fixes required for correctness and test isolation. No scope creep.

## Issues Encountered

- Pre-existing `test_webhooks.py` failure (fastapi not installed) was present before this plan and is out of scope. Logged to deferred-items.

## User Setup Required

None — no new external service configuration required for these connectors beyond the Gmail OAuth credentials already in settings (gmail_client_id, gmail_client_secret, gmail_refresh_token).

## Next Phase Readiness

- Both connectors ready for integration with Cloud Scheduler (cron triggers)
- poll_gmail() and poll_calendar() are importable and testable without live credentials
- Full connector test suite (8/8) provides regression coverage
- Pre-existing fastapi/test_webhooks failure should be resolved before Phase 1 completion

---
*Phase: 01-input-layer*
*Completed: 2026-03-13*

## Self-Check: PASSED

- src/input/connectors/gmail.py: FOUND
- src/input/connectors/calendar.py: FOUND
- tests/unit/test_connectors.py: FOUND
- .planning/phases/01-input-layer/01-04-SUMMARY.md: FOUND
- Commit c3c5cf0 (Task 1): FOUND
- Commit 4bfa9b2 (Task 2): FOUND
