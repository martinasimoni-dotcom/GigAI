---
phase: 05-domain-processing
plan: "02"
subsystem: domain_processing
tags: [tdd, time-analysis, pydantic-v2, dateutil, conflict-detection]
dependency_graph:
  requires:
    - src/system/context/enrichment.py (EnrichedEvent)
    - src/shared/models/events.py (NormalizedEvent.quantity)
  provides:
    - src/system/domain_processing/time_analysis.py (analyze_time, TimeAnalysisResult)
  affects:
    - src/system/domain_processing/processor.py (time analysis step in pipeline)
tech_stack:
  added:
    - python-dateutil>=2.9 (schedule date parsing with graceful fallback)
  patterns:
    - TYPE_CHECKING guard prevents transitive config.settings import at module load
    - autouse fixture (env vars + sys.modules.pop) for settings-dependent test isolation
    - IMPL_AVAILABLE guard (Path.exists() + stat().st_size > 10) for safe test collection
key_files:
  created:
    - src/system/domain_processing/time_analysis.py
    - tests/unit/test_time_analysis.py
  modified: []
decisions:
  - TYPE_CHECKING guard used instead of direct import for EnrichedEvent in time_analysis.py to avoid transitive settings singleton trigger
  - TimeAnalysisResult defined inline in time_analysis.py per plan (not in shared models)
  - autouse fixture pattern (same as test_retrieval.py) applied to test_time_analysis.py for clean isolation
metrics:
  duration: "4 min"
  completed: "2026-03-13"
  tasks: 2
  files: 2
---

# Phase 5 Plan 02: Time Analysis Summary

**One-liner:** dateutil-based lead time calculation (42 days qty>10, 21 days default) with schedule conflict detection, 19 unit tests passing.

---

## What Was Built

`analyze_time(event: EnrichedEvent, schedule: list[dict] | None) -> TimeAnalysisResult` implements RULE-005 temporal reasoning for the domain processing pipeline:

- **Lead time calculation:** quantity > 10 units → 42 days (6 weeks); quantity <= 10 or None → 21 days (3 weeks default)
- **Conflict detection:** iterates over ACC schedule entries, parses dates with `dateutil.parser.parse()`, flags entries falling within `[today, today + lead_time_days]` inclusive
- **Graceful error handling:** unparseable date strings (ValueError, OverflowError, TypeError) are silently skipped
- **No LLM calls, no config.settings import** — pure logic module safe to import in test environments

`TimeAnalysisResult` Pydantic v2 model:
- `has_conflict: bool = False`
- `conflict_details: str | None = None`
- `lead_time_days: int = 21`
- `critical_path_affected: bool = False`
- `schedule_conflicts: list[dict] = []`

---

## TDD Execution

**RED (Task 1):** 19 tests written in `tests/unit/test_time_analysis.py`, all skipped (IMPL_AVAILABLE=False for empty file) — commit `cbc2c0e`

**GREEN (Task 2):** Implementation in `src/system/domain_processing/time_analysis.py`, all 19 tests pass — commit `cc82861`

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] python-dateutil not installed in Python 3.13 environment**
- **Found during:** Task 2 GREEN phase execution
- **Issue:** `ModuleNotFoundError: No module named 'dateutil'` — package was in requirements.txt but not installed in the Python 3.13 env used by pytest
- **Fix:** Ran `python -m pip install python-dateutil` targeting the correct interpreter
- **Files modified:** None (environment fix only)
- **Commit:** cc82861 (inline fix, no separate commit)

**2. [Rule 1 - Bug] Transitive config.settings import triggered via EnrichedEvent**
- **Found during:** Task 2 GREEN phase — tests failed with `pydantic_core.ValidationError: 3 validation errors for Settings`
- **Issue:** `time_analysis.py -> enrichment.py -> vector_store.py -> postgres.py -> config.settings` chain caused settings singleton to fire at import time, even though `time_analysis.py` itself doesn't import settings
- **Fix:** Changed direct import to `TYPE_CHECKING` guard (`from __future__ import annotations` + `if TYPE_CHECKING: from src.system.context.enrichment import EnrichedEvent`). This uses string-based annotations (PEP 563) so `EnrichedEvent` is only a type hint — no runtime import.
- **Files modified:** `src/system/domain_processing/time_analysis.py`
- **Commit:** cc82861

**3. [Rule 1 - Bug] Test file needed autouse fixture for settings isolation**
- **Found during:** Task 2 GREEN phase — even with TYPE_CHECKING fix, `make_event()` helper's lazy import of `EnrichedEvent` in tests still triggered the chain (via `src.system.context.__init__.py` re-exporting it)
- **Fix:** Added `_setup_env` autouse fixture following established `test_retrieval.py` pattern: `monkeypatch.setenv()` for required API keys + `sys.modules.pop()` for all modules in the chain before/after each test
- **Files modified:** `tests/unit/test_time_analysis.py`
- **Commit:** cc82861

---

## Decisions Made

1. **TYPE_CHECKING guard for EnrichedEvent import** — prevents transitive settings singleton trigger while preserving type annotation correctness for IDE support and mypy
2. **TimeAnalysisResult inline in time_analysis.py** — per CONTEXT.md discretion, domain-specific result models stay in their module rather than shared models
3. **autouse fixture pattern** — same isolation approach as test_retrieval.py (CTX-01/02) applied consistently across domain processing tests

---

## Self-Check: PASSED

Files verified:
- FOUND: src/system/domain_processing/time_analysis.py
- FOUND: tests/unit/test_time_analysis.py
- FOUND: .planning/phases/05-domain-processing/05-02-SUMMARY.md

Commits verified:
- cbc2c0e — test(05-02): add failing tests for time_analysis
- cc82861 — feat(05-02): implement time_analysis.py (GREEN)

Tests: 19 passed, 0 failed, 0 skipped
