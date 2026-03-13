---
phase: 01-input-layer
plan: "01"
subsystem: testing
tags: [pytest, google-api-python-client, google-auth-httplib2, wave-0, tdd, stubs]

# Dependency graph
requires:
  - phase: 00-foundation
    provides: "conftest.py with mock_anthropic_client, mock_voyage_client, mock_db_conn, test_env fixtures"
provides:
  - "Wave 0 test stubs for all Input Layer implementation tasks"
  - "Google API package entries in requirements.txt"
  - "mock_pubsub_publisher, mock_gmail_service, mock_calendar_service fixtures in conftest.py"
affects:
  - 01-input-layer (plans 02-06 use these test stubs as TDD targets)

# Tech tracking
tech-stack:
  added:
    - google-api-python-client>=2.115
    - google-auth-httplib2>=0.2.0
  patterns:
    - "Wave 0 Nyquist compliance: test stubs committed before implementation begins"
    - "Import-guarded test files: try/except ImportError + pytestmark skipif for graceful pre-implementation skipping"
    - "anyio pytest_plugins pattern for async webhook tests"

key-files:
  created:
    - tests/unit/test_webhooks.py
    - tests/unit/test_connectors.py
    - tests/unit/test_pubsub.py
    - tests/unit/test_main.py
  modified:
    - requirements.txt
    - tests/conftest.py

key-decisions:
  - "Import-guard pattern chosen over xfail: try/except ImportError + skipif avoids collection errors when implementation files don't exist yet"
  - "pytest_plugins anyio used in test_webhooks.py to parametrize async tests across asyncio and trio backends"

patterns-established:
  - "Wave 0 stubs: all implementation tasks must have named test stubs committed before Wave 1 code is written"
  - "Import guard: guard test-module imports with try/except and pytestmark.skipif so test files are always collectable"

requirements-completed: [INPUT-01, INPUT-02, INPUT-03, INPUT-04]

# Metrics
duration: 2min
completed: 2026-03-13
---

# Phase 1 Plan 01: Wave 0 Test Stubs and Google API Packages Summary

**Four Wave 0 test stub files with 11 named test targets plus mock_pubsub_publisher/gmail/calendar fixtures, enabling TDD for all Input Layer implementation tasks**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-13T10:27:09Z
- **Completed:** 2026-03-13T10:29:30Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Added google-api-python-client>=2.115 and google-auth-httplib2>=0.2.0 to requirements.txt; both packages importable in the project's Anaconda environment
- Created test_webhooks.py (4 stubs), test_connectors.py (4 stubs), test_pubsub.py (1 stub), test_main.py (2 stubs) — all 15 collect with 0 errors and show as SKIPPED
- Appended mock_pubsub_publisher, mock_gmail_service, mock_calendar_service fixtures to conftest.py without disturbing existing fixtures

## Task Commits

Each task was committed atomically:

1. **Task 1: Add missing packages to requirements.txt** - `c2dd4f3` (chore)
2. **Task 2: Create Wave 0 test stubs and new conftest fixtures** - `a748ece` (test)

**Plan metadata:** _(final docs commit below)_

## Files Created/Modified
- `requirements.txt` - Added google-api-python-client>=2.115 and google-auth-httplib2>=0.2.0 under # Google Cloud section
- `tests/unit/test_webhooks.py` - 4 async stubs for INPUT-01/02 (Fireflies and ACC webhooks)
- `tests/unit/test_connectors.py` - 4 stubs for INPUT-03/04 (Gmail and Calendar connectors)
- `tests/unit/test_pubsub.py` - 1 stub for publish_event helper
- `tests/unit/test_main.py` - 2 stubs for FastAPI app wiring (health endpoint, router registration)
- `tests/conftest.py` - Appended mock_pubsub_publisher, mock_gmail_service, mock_calendar_service fixtures

## Decisions Made
- Import-guard pattern (try/except ImportError + pytestmark.skipif) chosen over xfail: allows test files to be collected cleanly even when implementation modules don't exist yet, which is the correct Wave 0 behavior
- pytest_plugins = ("anyio",) used in test_webhooks.py so async tests are parametrized across both asyncio and trio backends automatically

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- `python -c "import googleapiclient"` failed because the shell's default `python` resolves to a WindowsApps stub (Python 3.13), while `pytest` uses the Anaconda env (Python 3.11). The packages are correctly installed in the Anaconda env where pytest runs — verified via `C:/Users/Rafik/anaconda3/envs/Intro_to_Python/python.exe -c "import googleapiclient; import google_auth_httplib2; print('OK')"` which returned OK.
- Pre-existing failure in test_postgres.py (ModuleNotFoundError: pydantic_settings not in Anaconda env) confirmed as out-of-scope pre-existing issue — not caused by this plan's changes.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Wave 0 test stubs are committed and all collect cleanly as SKIPPED
- Implementation plans (01-02 through 01-06) can now write code with test targets already in place
- google-api-python-client and google-auth-httplib2 are in requirements.txt and installed in the test environment

---
*Phase: 01-input-layer*
*Completed: 2026-03-13*
