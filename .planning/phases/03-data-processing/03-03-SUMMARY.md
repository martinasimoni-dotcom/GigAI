---
phase: 03-data-processing
plan: 03
subsystem: data-processing
tags: [routing, haiku, pubsub, event-classification, yaml-config]
requirements: [PROC-04, PROC-05]

dependency_graph:
  requires:
    - 03-01  # NormalizedEvent model with confidence/review_required fields
    - 03-02  # normalizer and scope_filter (upstream pipeline steps)
  provides:
    - route_event() function classifying NormalizedEvent into one of 4 event types
    - RoutedEvent model with event, event_type, config, config_path
    - config/prompts/routing.txt — Haiku classification prompt
    - config/event_types/*.yaml — 4 validated EventTypeConfig stubs
  affects:
    - Phase 4 (context enrichment) — consumes RoutedEvent.config for enrichment queries

tech_stack:
  added: []
  patterns:
    - Haiku classification with JSON output_schema and fallback to "other"
    - Path(__file__).resolve() anchoring for config directory resolution
    - Pub/Sub publish pattern matching src/input/pubsub.py (PublisherClient per call)
    - EventTypeConfig Pydantic validation of YAML at load time

key_files:
  created:
    - config/prompts/routing.txt
    - config/event_types/material_change.yaml
    - config/event_types/schedule_update.yaml
    - config/event_types/rfi_request.yaml
    - config/event_types/other.yaml
    - src/system/data_processing/router.py
    - src/system/__init__.py
    - src/system/data_processing/__init__.py
  modified:
    - tests/unit/test_router.py  # stubs already existed; now run and pass

decisions:
  - "config_dir parameter added to route_event() for test-time injection without filesystem mocking"
  - "Path(__file__) anchor ensures config loading is CWD-independent"
  - "_VALID_EVENT_TYPES set used for O(1) fallback detection"
  - "Existing test stubs were correct as-is; no rewrite needed"

metrics:
  duration: "2m 45s"
  tasks_completed: 2
  files_created: 8
  files_modified: 1
  tests_passed: 13
  completed_date: "2026-03-13"
---

# Phase 3 Plan 03: Routing Prompt, YAML Configs, and Router Module Summary

**One-liner:** Haiku-based event classifier routing NormalizedEvents to one of 4 typed EventTypeConfig YAML stubs, with Pub/Sub publish and automatic "other" fallback.

## What Was Built

Completed the final step of the Phase 3 data processing pipeline. A NormalizedEvent can now flow through `normalize_event → filter_event → route_event` and emerge as a RoutedEvent ready for Phase 4 context enrichment.

### Task 1: Routing prompt and event type YAML configs

- `config/prompts/routing.txt` — Haiku prompt listing all 4 event types with descriptions and JSON output format
- `config/event_types/material_change.yaml` — working stub with signals and enrichment queries
- `config/event_types/schedule_update.yaml` — stub with schedule_update_needed signal
- `config/event_types/rfi_request.yaml` — minimal stub
- `config/event_types/other.yaml` — fallback config for unclassified events
- All 4 YAML files validated against EventTypeConfig Pydantic schema

### Task 2: Router module and package init files

- `src/system/data_processing/router.py` — `RoutedEvent` model + `route_event()` function
- `src/system/__init__.py` — package docstring
- `src/system/data_processing/__init__.py` — package docstring

**`route_event()` behavior:**
1. Reads `config/prompts/routing.txt` and appends the event JSON
2. Calls `call_haiku()` with routing prompt and JSON output schema
3. Validates response is one of `{material_change, schedule_update, rfi_request, other}`
4. Falls back to `"other"` if unknown type or Haiku call fails
5. Loads `config/event_types/{event_type}.yaml` and validates against EventTypeConfig
6. Falls back to `other.yaml` if YAML load/validation fails
7. Publishes NormalizedEvent to normalized-events Pub/Sub topic
8. Returns `RoutedEvent(event, event_type, config, config_path)`

## Test Results

```
tests/unit/test_normalizer.py   4 passed
tests/unit/test_scope_filter.py 5 passed
tests/unit/test_router.py       4 passed
Total Phase 3: 13 passed
```

Full suite: 85 passed, 1 failed (pre-existing pgvector mock), 14 errors (pre-existing missing fastapi). No regressions introduced.

## Deviations from Plan

None — plan executed exactly as written.

The plan mentioned optionally rewriting `test_router.py` with a `config_dir` parameter, but the existing stub tests already used correct path anchoring via the router's `__file__`-based `_CONFIG_DIR`. The `config_dir` optional parameter was still added to `route_event()` for future flexibility, and tests pass without using it.

## Self-Check: PASSED

Files created:
- config/prompts/routing.txt — FOUND
- config/event_types/material_change.yaml — FOUND
- config/event_types/schedule_update.yaml — FOUND
- config/event_types/rfi_request.yaml — FOUND
- config/event_types/other.yaml — FOUND
- src/system/data_processing/router.py — FOUND
- src/system/__init__.py — FOUND
- src/system/data_processing/__init__.py — FOUND

Commits:
- aacf07e — feat(03-03): add routing prompt and event type YAML configs — FOUND
- f88033b — feat(03-03): implement router module with RoutedEvent and route_event() — FOUND

Tests: 13/13 Phase 3 tests pass.
