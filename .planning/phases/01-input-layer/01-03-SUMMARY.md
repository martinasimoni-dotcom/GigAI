---
phase: 01-input-layer
plan: "03"
subsystem: api
tags: [fastapi, webhooks, pydantic-v2, httpx, anyio, asyncio, tdd, sys-modules-isolation]

# Dependency graph
requires:
  - phase: 01-input-layer
    plan: "02"
    provides: "publish_event() shared helper in src/input/pubsub.py"
provides:
  - "POST /webhooks/fireflies FastAPI route — validates transcript/meeting/meetingId/id keys, publishes RawEvent with source='fireflies'"
  - "POST /webhooks/acc FastAPI route — permissive validation (non-empty dict), publishes RawEvent with source='acc'"
  - "src/main.py FastAPI app — registers both webhook routers, exposes /health endpoint"
affects:
  - 01-input-layer (plans 04-06 can now use the FastAPI app pattern for connector endpoints)
  - tests (src.main.app is now importable for integration testing)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "sys.modules.pop for webhook test isolation: must pop src.input.webhooks PACKAGE (not just submodules) to prevent stale module attribute cross-test contamination"
    - "anyio_backend fixture with params=['asyncio']: locks async tests to asyncio when trio is not installed, preventing ModuleNotFoundError on trio backend"
    - "APIRouter pattern: each webhook file exports an APIRouter; src/main.py includes them all"

key-files:
  created:
    - src/main.py
    - src/input/webhooks/fireflies.py
    - src/input/webhooks/acc.py
  modified:
    - tests/unit/test_webhooks.py

key-decisions:
  - "sys.modules.pop must include 'src.input.webhooks' package: popping only the submodules leaves the package's attribute pointing to the old module object; from src.input.webhooks import fireflies retrieves the old module from the package attribute, bypassing the freshly-imported sys.modules entry — causing mock_publish patches to miss"
  - "anyio_backend fixture params=['asyncio']: trio not installed in Anaconda Intro_to_Python env; anyio parametrizes across all backends by default, causing ModuleNotFoundError on trio backend"
  - "Permissive ACC validation deferred: any non-empty dict accepted in Phase 1; full ACC schema validation deferred to Phase 7 as specified in CONTEXT.md"

patterns-established:
  - "Webhook test isolation: autouse setup_env fixture must pop the package module in addition to submodules (src.input.webhooks alongside fireflies/acc/main) to ensure fresh module identity per test"
  - "anyio asyncio-only: use @pytest.fixture(params=['asyncio']) def anyio_backend for projects without trio installed"

requirements-completed: [INPUT-01, INPUT-02]

# Metrics
duration: 18min
completed: 2026-03-13
---

# Phase 1 Plan 03: Webhook Endpoints Summary

**FastAPI POST /webhooks/fireflies and POST /webhooks/acc with key-based validation, RawEvent publishing, and sys.modules package-level isolation for reliable async test isolation**

## Performance

- **Duration:** 18 min
- **Started:** 2026-03-13T10:40:00Z
- **Completed:** 2026-03-13T10:58:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Implemented `src/input/webhooks/fireflies.py`: validates payload contains at least one of `transcript/meeting/meetingId/id`, returns 200 + message_id on success, 400 on empty or no-match payload
- Implemented `src/input/webhooks/acc.py`: permissive validation (any non-empty dict accepted), returns 200 + message_id on success, 400 on empty payload
- Created `src/main.py`: FastAPI app that includes both webhook routers and exposes `GET /health`
- 9/9 webhook tests pass green with full isolation between tests

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Add failing webhook tests** - `a26232c` (test)
2. **Task 1 GREEN: Implement fireflies.py + main.py** - `7d76cf4` (feat)
3. **Task 2 GREEN: Implement acc.py** - `6de141d` (feat)

**Plan metadata:** _(final docs commit below)_

_Note: TDD tasks have separate RED and GREEN commits. acc.py was implemented during Task 1's GREEN phase since both files share the same module isolation pattern; Task 2's commit captures acc.py alone._

## Files Created/Modified
- `src/main.py` - FastAPI app entry point: includes fireflies and acc routers, GET /health endpoint
- `src/input/webhooks/fireflies.py` - POST /webhooks/fireflies: validates `_REQUIRED_KEYS` intersection, publishes RawEvent with source="fireflies"
- `src/input/webhooks/acc.py` - POST /webhooks/acc: permissive non-empty dict validation, publishes RawEvent with source="acc"
- `tests/unit/test_webhooks.py` - Replaced Wave 0 stubs with 9 full tests; autouse `setup_env` with package-level sys.modules clearing; `anyio_backend` fixture limiting to asyncio

## Decisions Made
- **Package-level sys.modules.pop required**: `from src.input.webhooks import fireflies` in `src/main.py` retrieves the `fireflies` attribute from the `src.input.webhooks` package module object. If only the submodule is popped, the package still holds a reference to the old module. The new `sys.modules["src.input.webhooks.fireflies"]` entry is a different object than what the package's attribute returns, causing `mock_publish` patches to target the wrong module. Fix: also pop `src.input.webhooks` from sys.modules so the package is reimported fresh and its attributes are rebound.
- **anyio_backend locked to asyncio**: trio not installed in the test environment; `pytest_plugins = ("anyio",)` causes anyio to parametrize all `@pytest.mark.anyio` tests over all installed backends. Adding `@pytest.fixture(params=["asyncio"]) def anyio_backend` restricts parametrization to asyncio only.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created src/main.py (empty file)**
- **Found during:** Task 1 RED (test collection)
- **Issue:** Tests import `from src.main import app` but `src/main.py` was an empty file with no `app` object
- **Fix:** Created `src/main.py` with FastAPI app, `/health` endpoint, and both webhook router registrations
- **Files modified:** src/main.py
- **Verification:** Tests can import `app` successfully
- **Committed in:** 7d76cf4 (Task 1 GREEN commit)

**2. [Rule 1 - Bug] Added setup_env autouse fixture with sys.modules.pop**
- **Found during:** Task 1 GREEN (test run — second test failing with DefaultCredentialsError)
- **Issue:** `config.settings.Settings()` singleton raises `ValidationError` at import time if env vars not set; additionally the `src.input.webhooks` package module cached a reference to the old `fireflies` module object after the first test, causing subsequent tests to call the real (unmocked) `publish_event`
- **Fix:** Added `setup_env` autouse fixture: setenv for 3 required config fields + sys.modules.pop for config.settings, pubsub, webhooks package, both webhook submodules, and src.main. Added `anyio_backend` fixture to prevent trio backend parametrization failure
- **Files modified:** tests/unit/test_webhooks.py
- **Verification:** 9/9 tests pass in sequence without cross-test contamination
- **Committed in:** 7d76cf4 (Task 1 GREEN commit)

---

**Total deviations:** 2 auto-fixed (1 blocking: missing app object; 1 bug: module isolation)
**Impact on plan:** Both fixes necessary for tests to run. The sys.modules package-level isolation pattern is a new discovery not previously documented — added to STATE.md accumulated context.

## Issues Encountered
- Pre-existing failure in `tests/unit/test_vector_store.py` and `tests/unit/test_voyage_client.py` (numpy binary incompatibility: `ValueError: numpy.dtype size changed`) — confirmed pre-existing before this plan. Out of scope, not fixed.

## User Setup Required
None — no external service configuration required. Tests mock publish_event; no GCP credentials needed for unit tests.

## Next Phase Readiness
- `src/main.py` app is importable; plans 04-06 can use `from src.main import app` for connector endpoint testing
- Both webhook routers registered and tested; the webhook test isolation pattern (package-level sys.modules.pop) is documented for plans 04-06 to follow
- Pre-existing numpy issue in test_vector_store.py still deferred

---
*Phase: 01-input-layer*
*Completed: 2026-03-13*

## Self-Check: PASSED

- FOUND: src/main.py
- FOUND: src/input/webhooks/fireflies.py
- FOUND: src/input/webhooks/acc.py
- FOUND: tests/unit/test_webhooks.py
- FOUND: .planning/phases/01-input-layer/01-03-SUMMARY.md
- FOUND commit: a26232c (test RED)
- FOUND commit: 7d76cf4 (feat GREEN Task 1)
- FOUND commit: 6de141d (feat GREEN Task 2)
