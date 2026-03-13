---
phase: 01-input-layer
plan: "02"
subsystem: infra
tags: [google-cloud-pubsub, pubsub_v1, lazy-init, tdd, gcp, bash, pydantic-v2]

# Dependency graph
requires:
  - phase: 01-input-layer
    plan: "01"
    provides: "mock_pubsub_publisher fixture in conftest.py; Wave 0 test_pubsub.py stub"
provides:
  - "publish_event() shared helper used by all four ingestion paths (webhooks + connectors)"
  - "infra/pubsub/setup.sh for one-time GCP Pub/Sub topic and subscription provisioning"
affects:
  - 01-input-layer (plans 03-06 import publish_event from src/input/pubsub.py)
  - 03-processing (raw-events-sub subscription consumed by normalization worker)

# Tech tracking
tech-stack:
  added:
    - google-cloud-pubsub>=2.18 (installed in Anaconda test env; was in requirements.txt but not installed)
    - pydantic-settings>=2.1.0 (installed in Anaconda test env; was in requirements.txt but not installed)
  patterns:
    - "Lazy publisher singleton: _get_publisher() initializes PublisherClient only on first call to avoid credential errors at import time"
    - "model_dump(mode='json') for datetime-safe serialization before json.dumps()"
    - "sys.modules.pop pattern: clear config.settings + src.input.pubsub before reimport in tests that import settings-dependent modules"

key-files:
  created:
    - src/input/pubsub.py
    - infra/pubsub/setup.sh
  modified:
    - tests/unit/test_pubsub.py

key-decisions:
  - "sys.modules.pop in reset_pubsub_globals fixture: required when testing modules that transitively import config.settings singleton — matches test_postgres.py established pattern"
  - "future.result() called synchronously in publish_event: surfaces publish errors immediately rather than silently dropping async failures"

patterns-established:
  - "Settings-dependent module test pattern: autouse fixture must setenv + pop sys.modules before import; matches test_postgres.py"
  - "Lazy init for GCP clients: use module-level _client = None + _get_client() accessor to prevent import-time credential failures"

requirements-completed: [INPUT-01, INPUT-02, INPUT-03, INPUT-04]

# Metrics
duration: 6min
completed: 2026-03-13
---

# Phase 1 Plan 02: Pub/Sub Publisher Helper and GCP Setup Script Summary

**Lazy-initialized PublisherClient with model_dump(mode='json') datetime serialization, source message attributes, and idempotent gcloud setup.sh for all four GigAI Pub/Sub topics**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-13T10:31:40Z
- **Completed:** 2026-03-13T10:37:30Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Implemented `src/input/pubsub.py` with `publish_event()`: lazy publisher init, datetime-safe JSON serialization via `model_dump(mode="json")`, source as Pub/Sub attribute, synchronous `future.result()` for error surfacing
- Created `infra/pubsub/setup.sh`: provisions 4 topics (raw-events, normalized-events, enriched-events, signals) and raw-events-sub pull subscription; idempotent bash script with fail-fast env var guard
- 4/4 unit tests pass green using `patch.object` for mock injection and `sys.modules.pop` for settings-module isolation

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Add failing tests** - `f1ebffe` (test)
2. **Task 1 GREEN: Implement src/input/pubsub.py** - `37006d7` (feat)
3. **Task 2: Create infra/pubsub/setup.sh** - `4bbc576` (chore)

**Plan metadata:** _(final docs commit below)_

_Note: TDD task has separate RED and GREEN commits_

## Files Created/Modified
- `src/input/pubsub.py` - Shared Pub/Sub publisher: lazy _get_publisher(), publish_event() with datetime serialization and source attribute
- `infra/pubsub/setup.sh` - One-time GCP provisioning: 4 topics + raw-events-sub subscription, idempotent, fail-fast
- `tests/unit/test_pubsub.py` - Replaced Wave 0 stub with 4 full tests; added env var setup + sys.modules clearing to autouse fixture

## Decisions Made
- `sys.modules.pop("config.settings", None)` added to `reset_pubsub_globals` autouse fixture: the config.settings module has a module-level `settings = Settings()` singleton that raises ValidationError if required env vars are not set. Popping from sys.modules + setting env vars before the import ensures each test starts clean. This matches the established pattern in `tests/unit/test_postgres.py`.
- `future.result()` called synchronously: Pub/Sub publish() is internally async and errors would be silently dropped without `.result()`. Synchronous call surfaces GoogleAPICallError immediately.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed google-cloud-pubsub in Anaconda env**
- **Found during:** Task 1 GREEN (first test run)
- **Issue:** `ImportError: cannot import name 'pubsub_v1' from 'google.cloud'` — google-cloud-pubsub was in requirements.txt but not installed in the Anaconda Intro_to_Python env used by pytest
- **Fix:** `pip install "google-cloud-pubsub>=2.18"` in the Anaconda env; installed 2.36.0
- **Files modified:** None (env install only)
- **Verification:** Import succeeds, tests run
- **Committed in:** 37006d7 (Task 1 GREEN commit, noted in message)

**2. [Rule 3 - Blocking] Installed pydantic-settings in Anaconda env**
- **Found during:** Task 1 GREEN (second test run after fixing pubsub install)
- **Issue:** `ModuleNotFoundError: No module named 'pydantic_settings'` — config.settings imports pydantic_settings which was in requirements.txt but not installed
- **Fix:** `pip install "pydantic-settings>=2.1.0"` in the Anaconda env; installed 2.13.1
- **Files modified:** None (env install only)
- **Verification:** config.settings importable, tests proceed
- **Committed in:** 37006d7 (Task 1 GREEN commit, noted in message)

**3. [Rule 1 - Bug] Added env var setup to reset_pubsub_globals fixture**
- **Found during:** Task 1 GREEN (third test run after installing packages)
- **Issue:** `ValidationError: 3 validation errors for Settings` — config.settings singleton fails at import when ANTHROPIC_API_KEY/VOYAGE_API_KEY/DATABASE_URL not set; monkeypatch in autouse fixture runs before test body but after module-level imports
- **Fix:** Added `monkeypatch.setenv()` calls + `sys.modules.pop()` for config.settings and src.input.pubsub to `reset_pubsub_globals` fixture; matches established pattern in `test_postgres.py`
- **Files modified:** tests/unit/test_pubsub.py
- **Verification:** 4/4 tests pass
- **Committed in:** 37006d7 (Task 1 GREEN commit)

---

**Total deviations:** 3 auto-fixed (2 blocking package installs, 1 bug in test fixture)
**Impact on plan:** All fixes required for tests to run. No scope creep. The sys.modules.pop pattern was already established in the project (test_postgres.py) so no new patterns introduced.

## Issues Encountered
- Pre-existing failure in `tests/unit/test_vector_store.py` (numpy binary incompatibility: `ValueError: numpy.dtype size changed`) confirmed present before this plan's changes via git stash check. Out of scope — logged to deferred items.

## User Setup Required
None - no external service configuration required. `infra/pubsub/setup.sh` requires `GOOGLE_CLOUD_PROJECT` and `gcloud` CLI to provision actual GCP resources, but this is optional for development.

## Next Phase Readiness
- `publish_event()` is importable and tested — plans 01-03 through 01-06 can now import from `src.input.pubsub`
- `infra/pubsub/setup.sh` ready for GCP provisioning when real credentials available
- Wave 0 test stubs for webhooks and connectors are in place; implementation plans can proceed

---
*Phase: 01-input-layer*
*Completed: 2026-03-13*
