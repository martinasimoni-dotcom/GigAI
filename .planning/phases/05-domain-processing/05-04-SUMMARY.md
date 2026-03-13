---
phase: 05-domain-processing
plan: 04
subsystem: domain_processing
tags: [pydantic-v2, signal-generator, processor, pipeline-orchestration, tdd]

# Dependency graph
requires:
  - phase: 05-02
    provides: analyze_time + TimeAnalysisResult (time conflict detection)
  - phase: 05-03
    provides: evaluate_policies + PolicyResult (YAML rule evaluation)
  - phase: 04-01
    provides: EnrichedEvent + enrich_event (context enrichment)
  - phase: 03-03
    provides: RoutedEvent (pre-loaded EventTypeConfig from router)
provides:
  - generate_signals(event, policy_result, time_result, config) → list[Signal]
  - ProcessingResult Pydantic v2 model (event, signals, policy_result, time_result)
  - process_event(routed_event) → ProcessingResult (full pipeline orchestrator)
  - domain_processing package with __all__ exports
affects: [06-decision-intelligence, 09-tests-demo, integration-pipeline]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Rule-to-signal mapping table (_RULE_SIGNAL_MAP) as inline dict — no DB/YAML lookup"
    - "set intersection for allowed_signals filtering (candidate_types & allowed)"
    - "sorted() on final_types for deterministic signal ordering"
    - "TYPE_CHECKING guard for EnrichedEvent in signal_generator.py — prevents config.settings trigger at import"

key-files:
  created:
    - src/system/domain_processing/signal_generator.py
    - src/system/domain_processing/processor.py
    - tests/unit/test_signal_generator.py
  modified:
    - src/system/domain_processing/__init__.py

key-decisions:
  - "signal_generator.py uses TYPE_CHECKING guard for EnrichedEvent import — avoids config.settings singleton trigger at module load (consistent with time_analysis.py and policy_engine.py patterns)"
  - "ProcessingResult defined inline in processor.py (not shared/models) — domain-specific result model per CONTEXT.md discretion"
  - "DOM-07 satisfied in processor.py: routed_event.config consumed directly — no redundant YAML reload"
  - "Demo verification script in PLAN.md used incorrect RawEvent constructor (missing event_id, wrong source) — fixed by using correct NormalizedEvent directly without RawEvent wrapper"

patterns-established:
  - "IMPL_AVAILABLE guard + lazy imports + autouse env fixture: consistent test isolation pattern across all domain processing tests"
  - "Signal deduplication via set: candidate_types accumulates rule mappings + time conflict, final_types filters to allowed set"
  - "Payload enrichment per signal type: material_order_required includes triggered_by + lead_time_days; schedule_update_needed includes conflict_details + conflicts; drawing_markup_required includes triggered_by"

requirements-completed: [DOM-05, DOM-06, DOM-07]

# Metrics
duration: 3min
completed: 2026-03-13
---

# Phase 5 Plan 04: Signal Generator + Processor Summary

**Rule-to-signal mapping with allowed_signals filtering, and full domain processing pipeline orchestration via process_event() consuming pre-loaded RoutedEvent.config (DOM-07)**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-13T15:21:30Z
- **Completed:** 2026-03-13T15:24:33Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- `generate_signals()` maps triggered policy rules + time conflicts to typed `Signal` objects, filtered to `config.allowed_signals`, deduplicated by `signal_type`
- `ProcessingResult` Pydantic v2 model and `process_event()` orchestrator wire the full domain pipeline: enrich → analyze_time → evaluate_policies → generate_signals
- 11 unit tests for signal_generator passing; 38 Phase 5 tests total passing
- Demo scenario confirmed: RULE-005 + RULE-008 + RULE-011 + has_conflict=True → `material_order_required`, `drawing_markup_required`, `schedule_update_needed`

## Task Commits

Each task was committed atomically:

1. **Task 1: signal_generator.py with tests** - `d013154` (feat + test, TDD)
2. **Task 2: processor.py and __init__.py** - `4d1674c` (feat)

**Plan metadata:** (docs commit — this summary)

_Note: TDD tasks may have multiple commits (test → feat → refactor). Task 1 used combined commit after RED confirmed (IMPL_AVAILABLE guard causes skip, not failure)._

## Files Created/Modified

- `src/system/domain_processing/signal_generator.py` — Rule→signal mapping table, `generate_signals()` with allowed_signals filter + deduplication
- `src/system/domain_processing/processor.py` — `ProcessingResult` model + `process_event()` pipeline orchestrator
- `src/system/domain_processing/__init__.py` — Package exports: `ProcessingResult`, `process_event`, `generate_signals`, `PolicyResult`, `evaluate_policies`, `TimeAnalysisResult`, `analyze_time`
- `tests/unit/test_signal_generator.py` — 11 unit tests: demo signals, allowed filter, no triggers, deduplication, valid Pydantic, escalate priority, time conflict

## Decisions Made

- `signal_generator.py` uses `from __future__ import annotations` + `TYPE_CHECKING` guard for `EnrichedEvent` import — prevents transitive `config.settings` singleton trigger at module load (consistent with `time_analysis.py` and `policy_engine.py` patterns established in 05-02 and 05-03).
- `ProcessingResult` is defined inline in `processor.py` rather than in `src/shared/models/` — domain-specific result model, per CONTEXT.md discretion established for `TimeAnalysisResult`.
- DOM-07 satisfied: `processor.py` uses `routed_event.config` directly — the `EventTypeConfig` is already loaded by `router.py` in Phase 3; no redundant YAML loading.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan verification script used incorrect RawEvent constructor**
- **Found during:** Overall verification step
- **Issue:** Plan's demo verification script used `RawEvent(source='test', raw_content='test')` — `RawEvent` requires `event_id`, `source` as Literal, and `raw_payload` dict (not `raw_content`). The script would fail at import.
- **Fix:** Ran verification using `NormalizedEvent` directly (no `RawEvent` wrapper needed for demo signal chain test; `EnrichedEvent` accepts `NormalizedEvent` directly).
- **Files modified:** None (verification script adapted inline; the implementation files are correct)
- **Verification:** Demo chain produced `{'schedule_update_needed', 'drawing_markup_required', 'material_order_required'}` — all 3 signals confirmed.
- **Committed in:** Not a separate commit — verification-only fix, no implementation files affected.

---

**Total deviations:** 1 (plan script bug, verification-only, no code changes required)
**Impact on plan:** Implementation files are 100% correct. Plan's inline demo script had stale RawEvent API; the actual verification confirmed success using the correct API.

## Issues Encountered

None — implementation matched plan exactly. All 38 Phase 5 tests pass on first run.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 5 domain processing pipeline is complete: `RoutedEvent → process_event() → ProcessingResult` with all signals
- Phase 6 (Decision Intelligence) can consume `ProcessingResult.signals` directly for proposal generation
- All 3 demo signals (`material_order_required`, `schedule_update_needed`, `drawing_markup_required`) are confirmed for the demo scenario

---
*Phase: 05-domain-processing*
*Completed: 2026-03-13*

## Self-Check: PASSED

Files verified:
- FOUND: src/system/domain_processing/signal_generator.py
- FOUND: src/system/domain_processing/processor.py
- FOUND: src/system/domain_processing/__init__.py
- FOUND: tests/unit/test_signal_generator.py

Commits verified:
- FOUND: d013154 (feat(05-04): implement signal_generator.py with tests)
- FOUND: 4d1674c (feat(05-04): implement processor.py and __init__.py)
