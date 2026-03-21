---
phase: 09-tests-and-demo
plan: "01"
subsystem: testing
tags: [pytest, pytest-cov, coverage, fixtures, json, unit-tests, acc-client, processor, policy-engine]

requires:
  - phase: 08-dashboard
    provides: completed dashboard implementation with all phases functional
  - phase: 03-data-processing
    provides: normalizer.py and router.py implementations
  - phase: 05-domain-processing
    provides: processor.py, policy_engine.py implementations
  - phase: 07-output-api
    provides: ACC client implementation (acc.py)

provides:
  - Three populated fixture JSON files for window-substitution demo scenario
  - Unit test coverage gate at 80.97% (gate: 80%)
  - 6 new processor tests covering process_event() pipeline and _fetch_acc_schedule()
  - 11 new ACC client tests covering token caching, floor plan, schedule, issues, markup, notifications
  - 9 new policy_engine tests covering IN operator branches, boolean conditions, missing rules file
  - 2 new normalizer tests (empty summary validation, material field assertion)
  - 3 new router tests (YAML fallback, enrichment queries config, material_change happy path)

affects:
  - 09-02-PLAN (integration tests load these fixture files)
  - 09-03-PLAN (demo pipeline uses fixture data)

tech-stack:
  added: [pytest-cov, coverage (without C extension)]
  patterns:
    - "Coverage filter: CoverageWarning added to pyproject.toml filterwarnings ignore list to enable pytest-cov on Python 3.13 without C extension"
    - "ACC client test pattern: mock urllib.request.urlopen with sequential response list + call counter"
    - "Processor test pattern: patch.object on all 4 pipeline steps to test orchestration in isolation"

key-files:
  created:
    - tests/fixtures/sample_transcript.json
    - tests/fixtures/sample_acc_event.json
    - tests/fixtures/expected_proposal.json
    - tests/unit/test_processor.py
    - tests/unit/test_acc_client.py
  modified:
    - tests/unit/test_normalizer.py
    - tests/unit/test_router.py
    - tests/unit/test_policy_engine.py
    - pyproject.toml

key-decisions:
  - "pytest-cov CoverageWarning must be ignored in pyproject.toml filterwarnings because Python 3.13 coverage.py has no C extension — coverage works via pure Python tracer but emits CoverageWarning which pytest treats as error"
  - "Coverage gate uses standalone `coverage run` + `coverage report --fail-under=80` pattern as primary check — pytest-cov also works after filterwarnings fix"
  - "Pre-existing test failures (test_postgres.py::test_get_connection_calls_register_vector and test_vector_store.py::test_embed_and_store_calls_embed_batch) are psycopg2 MagicMock encoding issues, out of scope for this plan"

requirements-completed: [TEST-01, TEST-03]

duration: 25min
completed: 2026-03-14
---

# Phase 9 Plan 01: Fixtures and Coverage Gate Summary

**Three demo fixture JSON files created and unit test coverage raised from 71.46% to 80.97% by adding 31 new tests across 5 test files**

## Performance

- **Duration:** 25 min
- **Started:** 2026-03-14T00:00:00Z
- **Completed:** 2026-03-14T00:25:00Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Created all three fixture files for the window-substitution demo scenario: `sample_transcript.json` (Fireflies webhook with all `_REQUIRED_KEYS`), `sample_acc_event.json` (ACC issue.created for W-301..W-312), and `expected_proposal.json` (Proposal shape with all 4 action types: email, task, calendar, drawing)
- Raised overall test coverage from 71.46% to 80.97% — clearing the 80% gate required by Phase 9's success criteria
- Added 6 processor tests (full `process_event()` pipeline, `_fetch_acc_schedule()` error paths), 11 ACC client tests (token caching, floor plan filter, schedule, issue creation, markup, notification), and 9 policy engine tests (IN operator branches, boolean conditions, missing rules file, malformed conditions)

## Task Commits

1. **Task 1: Create demo fixture JSON files** - `1251a42` (feat)
2. **Task 2: Fill unit test coverage gaps** - `7295641` (feat)

**Plan metadata:** (docs commit — see final_commit step)

## Files Created/Modified

- `tests/fixtures/sample_transcript.json` — Fireflies webhook demo payload with meetingId, id, meeting, transcript, attendees
- `tests/fixtures/sample_acc_event.json` — ACC issue.created webhook for W-301..W-312 aluminum-to-wood window change
- `tests/fixtures/expected_proposal.json` — Proposal shape with confidence_score=0.855, recommendation=accept, 4 actions
- `tests/unit/test_processor.py` — 6 tests for process_event() orchestration and _fetch_acc_schedule() error handling
- `tests/unit/test_acc_client.py` — 11 tests for ACC client functions via urllib mock
- `tests/unit/test_normalizer.py` — 2 new tests (empty summary ValidationError, material field assertion)
- `tests/unit/test_router.py` — 3 new tests (YAML-missing fallback, enrichment queries, material_change config)
- `tests/unit/test_policy_engine.py` — 9 new tests (IN operator variants, boolean/numeric operators, missing rules file)
- `pyproject.toml` — Added `ignore::coverage.exceptions.CoverageWarning` to filterwarnings

## Decisions Made

- `CoverageWarning` must be added to pytest filterwarnings — Python 3.13 coverage.py has no compiled C extension, emitting `CoverageWarning` which pytest (with `filterwarnings = ["error"]`) would treat as a hard error. Added `ignore::coverage.exceptions.CoverageWarning` to pyproject.toml.
- Scope expansion was required: normalizer (100%) and router (85.94%) were already above 80%, so the main coverage gap was in `processor.py` (48.72%) and `acc.py` (19.35%). Added tests for these modules to clear the overall 80% gate.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added pytest-cov filterwarnings fix and CoverageWarning ignore**
- **Found during:** Task 2 (coverage gate check)
- **Issue:** pytest-cov failed to start because `coverage.exceptions.CoverageWarning` (emitted when C extension is unavailable on Python 3.13) was treated as an error by `filterwarnings = ["error"]` in pyproject.toml
- **Fix:** Added `"ignore::coverage.exceptions.CoverageWarning"` to the filterwarnings list in pyproject.toml
- **Files modified:** `pyproject.toml`
- **Verification:** `python3.13 -m pytest tests/unit/ --cov=src --cov-fail-under=80 -q` exits 0
- **Committed in:** `1251a42` (Task 1 commit — included with fixture files)

**2. [Rule 2 - Missing Critical] Added tests for processor.py and acc.py (below 80%)**
- **Found during:** Task 2 (initial coverage check revealed 48.72% on processor.py, 19.35% on acc.py)
- **Issue:** Plan specified adding normalizer/router tests, but normalizer was already 100% and router was 85.94%. Coverage gate failure was due to processor.py (48.72%) and acc.py (19.35%) with zero tests
- **Fix:** Created `test_processor.py` (6 tests) and `test_acc_client.py` (11 tests) for the untested modules
- **Files modified:** `tests/unit/test_processor.py` (new), `tests/unit/test_acc_client.py` (new)
- **Verification:** Overall coverage raised to 80.97%, gate passed
- **Committed in:** `7295641` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking — pytest-cov startup, 1 missing critical — test coverage scope)
**Impact on plan:** Both auto-fixes essential. Scope expansion from normalizer/router to processor/acc was required to actually pass the coverage gate.

## Issues Encountered

- **Pre-existing test failures (deferred):** `test_postgres.py::test_get_connection_calls_register_vector` and `test_vector_store.py::test_embed_and_store_calls_embed_batch` fail due to psycopg2 `MagicMock` encoding issue (`KeyError` on `connection.encoding` mock attribute). These are pre-existing failures not caused by this plan's changes. Documented in deferred items.

## Coverage Results

| Module | Before | After |
|--------|--------|-------|
| `src/system/domain_processing/processor.py` | 48.72% | 94.87% |
| `src/shared/clients/acc.py` | 19.35% | 95.70% |
| `src/system/domain_processing/policy_engine.py` | 67.72% | 87.30% |
| `src/system/data_processing/normalizer.py` | 100% | 100% |
| `src/system/data_processing/router.py` | 85.94% | 96.88% |
| **TOTAL** | **71.46%** | **80.97%** |

## Next Phase Readiness

- All three fixture files exist with correct structure for integration tests (09-02)
- Coverage gate is green at 80.97%
- `tests/unit/` directory has 191 total tests (189 passing, 2 pre-existing failures unrelated to this plan)
- Ready to proceed to 09-02 (integration tests) and 09-03 (demo script)

---
*Phase: 09-tests-and-demo*
*Completed: 2026-03-14*

## Self-Check: PASSED

- FOUND: tests/fixtures/sample_transcript.json
- FOUND: tests/fixtures/sample_acc_event.json
- FOUND: tests/fixtures/expected_proposal.json
- FOUND: tests/unit/test_processor.py
- FOUND: tests/unit/test_acc_client.py
- FOUND: .planning/phases/09-tests-and-demo/09-01-SUMMARY.md
- FOUND commit 1251a42 (Task 1)
- FOUND commit 7295641 (Task 2)
