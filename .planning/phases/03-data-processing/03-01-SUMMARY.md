---
phase: 03-data-processing
plan: 01
subsystem: data-processing
tags: [pydantic, models, test-stubs, wave-0, tdd]
dependency_graph:
  requires: []
  provides:
    - NormalizedEvent with review_required, confidence, estimated_cost fields
    - test_normalizer.py collectable stubs (PROC-01, PROC-02)
    - test_scope_filter.py collectable stubs (PROC-03)
    - test_router.py collectable stubs (PROC-04, PROC-05)
  affects:
    - src/shared/models/events.py
    - tests/unit/test_normalizer.py
    - tests/unit/test_scope_filter.py
    - tests/unit/test_router.py
tech_stack:
  added: []
  patterns:
    - Path.exists() + st_size guard for Wave 0 test stubs (avoids pydantic ValidationError at collection time)
    - pytestmark.skipif at module level to skip all tests when impl file missing
    - autouse fixture for env var injection + sys.modules.pop isolation
    - TDD red-green cycle for model field additions
key_files:
  created:
    - tests/unit/test_normalizer.py
    - tests/unit/test_scope_filter.py
    - tests/unit/test_router.py
  modified:
    - src/shared/models/events.py
    - tests/unit/test_models_events.py
    - .planning/phases/03-data-processing/03-01-PLAN.md
decisions:
  - "Fields appended before the @field_validator block to preserve validator ordering"
  - "Path.exists() guard chosen over try/except ImportError — settings singleton raises ValidationError at import time before any fixture runs"
  - "pytestmark = pytest.mark.skipif at module level means entire file skips with a single IMPL_AVAILABLE check"
metrics:
  duration: "~5 min"
  completed: "2026-03-13"
  tasks: 2
  files: 5
---

# Phase 3 Plan 01: NormalizedEvent Extension + Wave 0 Test Stubs

**One-liner:** Extended NormalizedEvent with review_required/confidence/estimated_cost fields and created three fully-collectable pytest stub files using Path.exists() guards for Wave 0 of the data-processing pipeline.

---

## What Was Built

### Task 1: Extend NormalizedEvent (TDD)

Added three fields to `src/shared/models/events.py`, immediately before the `@field_validator` block:

```python
review_required: bool = False
confidence: int = Field(ge=0, le=100, default=50)
estimated_cost: Optional[float] = None
```

Added 3 tests to `tests/unit/test_models_events.py`:
- `test_normalized_event_new_fields_defaults` — verifies default values
- `test_normalized_event_confidence_bounds` — verifies ge=0, le=100 constraints
- `test_normalized_event_new_fields_set` — verifies explicit value assignment

All 8 tests in test_models_events.py pass. `extra="forbid"` still enforced.

**Commits:** 587290e

### Task 2: Write Collectable Test Stubs

Created three stub test files using the established Wave 0 pattern from `test_knowledge_folder.py`:

| File | Requirement | Tests |
|------|-------------|-------|
| tests/unit/test_normalizer.py | PROC-01, PROC-02 | 4 stubs |
| tests/unit/test_scope_filter.py | PROC-03 | 5 stubs |
| tests/unit/test_router.py | PROC-04, PROC-05 | 4 stubs |

All 13 tests collect cleanly. All 13 skip gracefully (IMPL_AVAILABLE=False) until implementation files exist with content.

**Commits:** 029d310

---

## Verification Results

```
python -m pytest tests/unit/test_models_events.py -x -q
# 8 passed

python -m pytest tests/unit/test_normalizer.py tests/unit/test_scope_filter.py tests/unit/test_router.py --collect-only -q
# 13 tests collected

python -m pytest tests/unit/test_normalizer.py tests/unit/test_scope_filter.py tests/unit/test_router.py -x -q
# 13 skipped (0 failed)
```

---

## Deviations from Plan

None — plan executed exactly as written.

---

## Self-Check: PASSED

Files confirmed present:
- src/shared/models/events.py — contains `review_required`, `confidence`, `estimated_cost`
- tests/unit/test_normalizer.py — 4 stubs, collectable
- tests/unit/test_scope_filter.py — 5 stubs, collectable
- tests/unit/test_router.py — 4 stubs, collectable

Commits confirmed:
- 587290e — feat(03-01): extend NormalizedEvent with review_required, confidence, estimated_cost
- 029d310 — feat(03-01): add collectable test stubs for normalizer, scope_filter, router
