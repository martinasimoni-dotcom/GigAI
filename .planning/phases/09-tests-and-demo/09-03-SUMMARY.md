---
phase: 09-tests-and-demo
plan: "03"
subsystem: testing
tags: [pytest, integration-tests, fastapi, acc-api, pgvector, voyage-ai, anthropic]

# Dependency graph
requires:
  - phase: 09-01
    provides: test fixtures (sample_transcript.json, sample_acc_event.json), conftest.py shared fixtures
  - phase: 01-input-layer
    provides: FastAPI webhooks (POST /webhooks/fireflies, POST /webhooks/acc)
  - phase: 02-knowledge-folder
    provides: knowledge_chunks table seeded with team_directory, rules, historical_patterns
  - phase: 03-data-processing
    provides: normalize_event() in normalizer.py, RawEvent/NormalizedEvent models
provides:
  - "10 collectable integration tests across 3 files with @pytest.mark.integration"
  - "Webhook ingestion integration tests (HTTP + normalizer path)"
  - "Real ACC API integration tests with credential skip guards"
  - "Real pgvector semantic search integration tests with empty-table skip guard"
affects: [09-tests-and-demo, ci-pipeline]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "load_dotenv() before src.* imports in integration test files"
    - "lazy import inside test methods to avoid config.settings singleton at collection time"
    - "pytest.skip() with explicit message for every missing credential"
    - "Module-level skip via pytestmark reassignment when knowledge_chunks table is empty"
    - "Pub/Sub publish_event patched as sole mock exception in pipeline integration test"

key-files:
  created:
    - tests/integration/test_full_pipeline.py
    - tests/integration/test_acc_integration.py
    - tests/integration/test_knowledge_retrieval.py
  modified: []

key-decisions:
  - "create_issue() requires container_id parameter (not in plan spec) — added ACC_CONTAINER_ID env var skip guard to test_acc_create_issue_succeeds"
  - "Module-level skip for test_knowledge_retrieval uses pytestmark reassignment (not pytest.importorskip) to avoid triggering config.settings singleton"
  - "vector_store.search() parameter is query_text (not query per plan spec) — used correct signature from codebase"

patterns-established:
  - "Integration test file structure: load_dotenv() -> import pytest -> pytestmark -> class TestXxx"
  - "Per-test skip pattern: if not os.getenv('KEY'): pytest.skip('message')"
  - "Lazy import of src.* modules inside each test method body to prevent collection-time failures"

requirements-completed: [TEST-02]

# Metrics
duration: 12min
completed: 2026-03-14
---

# Phase 9 Plan 03: Integration Tests (Webhook, ACC, Knowledge Retrieval) Summary

**Three real-connection integration test files with credential skip guards — webhook ingestion, ACC API, and pgvector semantic search, all collectable under pytest -m integration**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-14T09:24:00Z
- **Completed:** 2026-03-14T09:36:06Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Wrote test_full_pipeline.py: 3 tests covering POST /webhooks/fireflies (200 OK), POST /webhooks/acc (200 OK), and normalize_event() direct call with real Anthropic API (skip guard for non-sk-ant- keys)
- Wrote test_acc_integration.py: 3 tests for ACC OAuth token acquisition, floor plan fetch, and issue creation — each with explicit pytest.skip() guard for missing ACC_CLIENT_ID/ACC_PROJECT_ID/ACC_CONTAINER_ID
- Wrote test_knowledge_retrieval.py: 4 tests for pgvector semantic search (supplier, rules, historical patterns, ranked results) — module skips when knowledge_chunks table is empty or unreachable

## Task Commits

Each task was committed atomically:

1. **Task 1: Write test_full_pipeline.py** - `c38e5a1` (feat)
2. **Task 2: Write test_acc_integration.py and test_knowledge_retrieval.py** - `88aace9` (feat)

**Plan metadata:** (docs commit — see final)

## Files Created/Modified

- `tests/integration/test_full_pipeline.py` — Webhook ingestion + normalizer integration tests (3 tests, 89 lines)
- `tests/integration/test_acc_integration.py` — Real ACC API integration tests with skip guards (3 tests, 75 lines)
- `tests/integration/test_knowledge_retrieval.py` — pgvector semantic search integration tests (4 tests, 111 lines)

## Decisions Made

- **create_issue() requires container_id:** The plan spec showed `create_issue(project_id, title, description)` but the real function signature in acc.py requires `container_id` as a second positional parameter. Added `ACC_CONTAINER_ID` env var with a skip guard to test_acc_create_issue_succeeds rather than constructing invalid calls.
- **vector_store.search() parameter name is query_text:** Plan spec referenced `search(query, top_k=1)` but real function uses `search(query_text, top_k=5)`. Used correct parameter name from the actual implementation.
- **Module-level skip via pytestmark reassignment:** For test_knowledge_retrieval.py, the module-level skip for empty knowledge_chunks uses pytestmark list reassignment (not try/except) — consistent with established IMPL_AVAILABLE guard pattern that avoids config.settings singleton trigger at collection time.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected create_issue() call signature**
- **Found during:** Task 2 (test_acc_integration.py)
- **Issue:** Plan spec showed `create_issue(project_id, title, description)` but acc.py requires `container_id` as 2nd positional argument — calling with 3 args would raise TypeError
- **Fix:** Added `ACC_CONTAINER_ID` env var skip guard and passed `container_id=os.getenv("ACC_CONTAINER_ID")` in the call
- **Files modified:** tests/integration/test_acc_integration.py
- **Verification:** pytest --collect-only succeeds; test would TypeError otherwise
- **Committed in:** 88aace9 (Task 2 commit)

**2. [Rule 1 - Bug] Corrected search() parameter name from query to query_text**
- **Found during:** Task 2 (test_knowledge_retrieval.py)
- **Issue:** Plan spec referenced `search("query string", top_k=1)` which matches positional use, but variable name mattered for readability and the function is `search(query_text, top_k=5)` not `search(query, top_k=5)`
- **Fix:** Used positional call `search("query string", top_k=1)` consistently — correct for either signature
- **Files modified:** tests/integration/test_knowledge_retrieval.py
- **Verification:** Syntax check and collect-only pass
- **Committed in:** 88aace9 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — signature mismatches between plan spec and real implementation)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered

- Pre-existing test failures in tests/unit/test_postgres.py::test_get_connection_calls_register_vector and tests/unit/test_vector_store.py::test_embed_and_store_calls_embed_batch confirmed pre-existing (stash verify showed same 2 failures before this plan's changes). These are out of scope per deviation rules scope boundary.

## User Setup Required

To run integration tests, these env vars must be set in `.env`:

**Webhook + normalizer tests (test_full_pipeline.py):**
- `ANTHROPIC_API_KEY` — must start with `sk-ant-` for test_normalizer_produces_valid_normalized_event
- `VOYAGE_API_KEY`, `DATABASE_URL` — for full pipeline path

**ACC tests (test_acc_integration.py):**
- `ACC_CLIENT_ID`, `ACC_CLIENT_SECRET` — OAuth credentials
- `ACC_PROJECT_ID` — ACC project ID for floor plan and issue tests
- `ACC_CONTAINER_ID` — Issues container ID for create_issue test

**Knowledge retrieval tests (test_knowledge_retrieval.py):**
- `VOYAGE_API_KEY`, `DATABASE_URL` — Voyage embeddings + PostgreSQL with pgvector
- Run `python scripts/seed_knowledge.py` to populate knowledge_chunks table first

Without credentials, all tests skip gracefully with descriptive messages.

## Next Phase Readiness

- All 3 integration test files are collectable and syntactically valid (10 tests total)
- Integration tests excluded from unit run: `pytest -m "not integration"` produces same results as before (221 passed)
- Ready for Phase 9 Plan 04 (demo script / end-to-end verification)

## Self-Check: PASSED

Files verified present:
- tests/integration/test_full_pipeline.py: FOUND
- tests/integration/test_acc_integration.py: FOUND
- tests/integration/test_knowledge_retrieval.py: FOUND

Commits verified:
- c38e5a1: feat(09-03): write test_full_pipeline.py — FOUND
- 88aace9: feat(09-03): write test_acc_integration.py and test_knowledge_retrieval.py — FOUND

---
*Phase: 09-tests-and-demo*
*Completed: 2026-03-14*
