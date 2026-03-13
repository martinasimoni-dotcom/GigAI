---
phase: 02-knowledge-folder
plan: 01
subsystem: testing
tags: [pytest, wave-0, test-stubs, knowledge-folder, seed-script, chunkers]

# Dependency graph
requires:
  - phase: 01-input-layer
    provides: test infrastructure patterns (conftest fixtures, sys.modules.pop pattern, import-guard pattern)
provides:
  - Wave 0 pytest scaffold for all 5 knowledge folder requirements (KF-01 through KF-05)
  - 6 test stubs covering chunk_markdown_by_sections, chunk_team_directory, chunk_rules, chunk_historical_patterns, seed (delete-before-insert, embed_batch document type)
  - Automated verify command: pytest tests/unit/test_knowledge_folder.py --collect-only -q
affects: [02-knowledge-folder waves 1+, scripts/seed_knowledge_folder.py implementation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Wave 0 import-guard: try/except ImportError + pytestmark.skipif ensures collectability before implementation exists"
    - "autouse _setup_env fixture: setenv + sys.modules.pop for isolation of settings-dependent modules"
    - "patch.object(module, 'attr') for test isolation after sys.modules.pop"

key-files:
  created:
    - tests/unit/test_knowledge_folder.py
  modified: []

key-decisions:
  - "Wave 0 pattern: test file is always collectable; 6 tests skip (not error) when scripts/seed_knowledge_folder.py is absent"
  - "autouse fixture pops 8 sys.modules entries including parent packages to prevent import cache poisoning across tests"
  - "seed tests use patch.object on the scripts.seed_knowledge_folder module namespace, not string-based patch, for mock reliability after sys.modules.pop"

patterns-established:
  - "Wave 0 scaffold first: write guarded test stubs before any implementation — provides automated verify command for all subsequent waves"

requirements-completed: [KF-01, KF-02, KF-03, KF-04, KF-05]

# Metrics
duration: 1min
completed: 2026-03-13
---

# Phase 2 Plan 01: Knowledge Folder Wave 0 Test Scaffold Summary

**pytest Wave 0 scaffold with 6 import-guarded test stubs covering all 5 knowledge folder chunker and seed behaviors (KF-01 through KF-05)**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-13T11:33:07Z
- **Completed:** 2026-03-13T11:34:19Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Created tests/unit/test_knowledge_folder.py with 6 test stubs covering all chunker functions (markdown sections, team directory, rules, historical patterns) and seed script behaviors (delete-before-insert, embed_batch input_type)
- All 6 tests collect cleanly with no import errors or syntax errors before implementation exists
- All 6 tests skip (not fail) with reason "seed_knowledge_folder.py not yet implemented" when IMPL_AVAILABLE=False
- Established autouse _setup_env fixture matching existing project patterns (setenv + sys.modules.pop for 8 modules)

## Task Commits

Each task was committed atomically:

1. **Task 1: Write test stubs for all chunker functions and seed script** - `eb6f361` (test)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `tests/unit/test_knowledge_folder.py` - Wave 0 test scaffold with 6 stubs for KF-01 through KF-05

## Decisions Made

- Used patch.object(skf, "get_connection") and patch.object(skf, "embed_batch") for seed tests rather than string-based patches — more reliable after sys.modules.pop per established project decision
- test_seed_calls_delete_before_insert verifies call ordering (DELETE index < INSERT index) in addition to presence, providing stronger correctness guarantee
- embed_batch mock returns `len(texts)` embeddings dynamically rather than fixed 100 — more robust for varying batch sizes

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Wave 0 scaffold complete; automated verify command established: `pytest tests/unit/test_knowledge_folder.py --collect-only -q`
- Ready for Wave 1: implement scripts/seed_knowledge_folder.py with chunk_markdown_by_sections, chunk_team_directory, chunk_rules, chunk_historical_patterns, seed
- All 6 tests will transition from SKIPPED to PASSED once implementation is complete

---
*Phase: 02-knowledge-folder*
*Completed: 2026-03-13*
