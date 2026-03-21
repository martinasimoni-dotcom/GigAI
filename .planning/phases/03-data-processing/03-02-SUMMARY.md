---
phase: 03-data-processing
plan: 02
subsystem: pipeline
tags: [haiku, pydantic, tenacity, normalization, scope-filter, json-extraction]

# Dependency graph
requires:
  - phase: 03-01
    provides: NormalizedEvent model with review_required/confidence/estimated_cost fields, RawEvent model, call_haiku() wrapper
provides:
  - config/prompts/normalization.txt — Haiku normalization prompt with flat-field schema and demo few-shot example
  - src/system/data_processing/normalizer.py — normalize_event() with tenacity retry and low-confidence flagging
  - src/system/data_processing/scope_filter.py — FilterResult model and filter_event() with location and cost checks
affects: [03-03-router, 04-enrichment, 05-domain-processing]

# Tech tracking
tech-stack:
  added: [tenacity retry decorator with retry_if_exception_type]
  patterns: [Haiku extraction with flat JSON schema, model_copy for immutable flag updates, case-insensitive location matching]

key-files:
  created:
    - config/prompts/normalization.txt
    - src/system/data_processing/normalizer.py
    - src/system/data_processing/scope_filter.py
  modified:
    - .planning/phases/03-data-processing/03-02-PLAN.md (status: complete)

key-decisions:
  - "change_type field stripped from Haiku output before NormalizedEvent(**data) to satisfy extra=forbid constraint"
  - "tenacity retry triggers on ValidationError, ValueError, and json.JSONDecodeError (not just ValidationError)"
  - "model_copy(update={review_required: True}) used to update immutable Pydantic model rather than mutating in place"
  - "filter_event() performs case-insensitive location matching via .lower() on both sides"

patterns-established:
  - "Haiku extraction pattern: call_haiku() → json.loads() → strip extra fields → NormalizedEvent(**data)"
  - "Low-confidence flag pattern: post-construction model_copy with review_required=True, no rejection"
  - "Scope filter pattern: FilterResult Pydantic model returned always, no exceptions raised"

requirements-completed: [PROC-01, PROC-02, PROC-03]

# Metrics
duration: 3min
completed: 2026-03-13
---

# Phase 3 Plan 02: Normalization Prompt, Normalizer, and Scope Filter Summary

**Haiku normalization prompt with flat-field JSON schema, normalize_event() with tenacity 3-attempt retry and confidence<70 review flag, and filter_event() scope/cost gate using FilterResult Pydantic model**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-13T14:09:59Z
- **Completed:** 2026-03-13T14:12:38Z
- **Tasks:** 2
- **Files modified:** 3 created, 1 modified

## Accomplishments

- `config/prompts/normalization.txt`: extraction prompt with flat NormalizedEvent field names, IMPORTANT rules preventing nested objects, and demo few-shot (aluminum→wood, 3rd floor, 12 units)
- `src/system/data_processing/normalizer.py`: `normalize_event()` calls Haiku, strips `change_type` to satisfy `extra="forbid"`, retries up to 3 times on ValidationError/ValueError/JSONDecodeError via tenacity, sets `review_required=True` for confidence<70
- `src/system/data_processing/scope_filter.py`: `FilterResult` Pydantic model with `passed/reason/escalate_immediately/alert_pm`, `filter_event()` rejects out-of-scope locations (alert_pm=True) and escalates cost>$50K (escalate_immediately=True), never raises
- 9 tests pass (4 normalizer + 5 scope filter), all Haiku calls mocked

## Task Commits

Each task was committed atomically:

1. **Task 1: Normalization prompt + normalizer module** - `526924e` (feat)
2. **Task 2: Scope filter module** - `fb1e588` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `config/prompts/normalization.txt` — Haiku extraction prompt with flat schema, IMPORTANT rules, few-shot demo
- `src/system/data_processing/normalizer.py` — normalize_event() with tenacity retry, change_type stripping, confidence flag
- `src/system/data_processing/scope_filter.py` — FilterResult model + filter_event() location/cost gate

## Decisions Made

- **Stripped `change_type` before Pydantic construction**: NormalizedEvent uses `extra="forbid"` so any field not in the model raises ValidationError. `change_type` is useful in the prompt but not in the model — removed via `data.pop("change_type", None)` before `NormalizedEvent(**data)`.
- **Retry covers three exception types**: `retry_if_exception_type((ValidationError, ValueError, json.JSONDecodeError))` catches malformed JSON, missing fields, and type coercion failures — all realistic Haiku failure modes.
- **model_copy for review_required**: Pydantic v2 models are effectively immutable after construction. `model_copy(update={"review_required": True})` is the correct pattern rather than attribute assignment.
- **Case-insensitive location matching**: `loc.lower()` on both sides of comparison prevents "3rd Floor" vs "3rd floor" mismatches.

## Deviations from Plan

None — plan executed exactly as written. The normalization.txt prompt wording, tenacity retry configuration, and FilterResult inline location were all delegated to Claude's discretion per 03-CONTEXT.md.

## Issues Encountered

None — all 9 tests passed on first run after implementation.

## User Setup Required

None — no external service configuration required. PUBSUB_TOPIC_NORMALIZED_EVENTS was already present in settings.py and .env.example from prior work.

## Next Phase Readiness

- `normalize_event()` and `filter_event()` are production-ready with full test coverage
- Plan 03-03 (router.py) can import both modules immediately
- `FilterResult` is available from `src.system.data_processing.scope_filter` for downstream use
- No blockers

---
## Self-Check: PASSED

- FOUND: config/prompts/normalization.txt
- FOUND: src/system/data_processing/normalizer.py
- FOUND: src/system/data_processing/scope_filter.py
- FOUND: .planning/phases/03-data-processing/03-02-SUMMARY.md
- FOUND: commit 526924e (feat(03-02): normalization prompt + normalizer)
- FOUND: commit fb1e588 (feat(03-02): scope filter module)
- Tests: 9/9 passed (4 normalizer + 5 scope filter)

*Phase: 03-data-processing*
*Completed: 2026-03-13*
