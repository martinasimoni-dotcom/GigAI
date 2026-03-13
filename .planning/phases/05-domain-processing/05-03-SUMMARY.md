---
phase: 05-domain-processing
plan: "03"
subsystem: domain_processing
tags: [policy-engine, tdd, yaml-rules, safe-eval, pydantic-v2]
dependency_graph:
  requires:
    - src/system/context/enrichment.py (EnrichedEvent)
    - src/shared/models/config.py (EventTypeConfig)
    - knowledge_folder/rules/demo_project.yaml (rules YAML at runtime)
  provides:
    - src/system/domain_processing/policy_engine.py (evaluate_policies, PolicyResult)
  affects:
    - src/system/domain_processing/processor.py (consumes PolicyResult)
    - src/system/domain_processing/signal_generator.py (receives triggered_rules)
tech_stack:
  added:
    - ast.literal_eval (safe IN-list parsing — not eval/exec)
  patterns:
    - TYPE_CHECKING guard for import-time safety (avoids config.settings singleton)
    - String annotations ("EnrichedEvent") for runtime-safe type hints
    - AND-split + operator tokenization for safe rule condition evaluation
    - IMPL_AVAILABLE guard (Path.exists + stat.st_size) for test collection safety
    - autouse _setup_env fixture (monkeypatch env vars + sys.modules.pop) for test isolation
key_files:
  created:
    - src/system/domain_processing/policy_engine.py
    - tests/unit/test_policy_engine.py
  modified: []
decisions:
  - change_type derived from NormalizedEvent.event_type (NormalizedEvent has extra=forbid, no change_type field)
  - TYPE_CHECKING import guard for EnrichedEvent prevents config.settings singleton at module import
  - String annotations used for EnrichedEvent parameter types (Python 3.13 evaluates annotations at runtime)
  - _eval_sub returns False for unknown fields (safe default — unknown conditions never fire)
metrics:
  duration: "4 min"
  completed_date: "2026-03-13"
  tasks_completed: 2
  files_created: 2
  files_modified: 0
requirements_completed:
  - DOM-04
---

# Phase 5 Plan 03: Policy Engine Summary

Safe YAML rule evaluation engine with Pydantic v2 PolicyResult — evaluates 18 rules against EnrichedEvent using explicit operator tokenization (no eval/exec), correctly fires RULE-005 (lead time), RULE-007 (spec comparison), RULE-008 (structural review), RULE-011 (drawing markup), and RULE-015 (supplier quote) for the demo scenario.

## Tasks Completed

| Task | Type | Description | Commit |
|------|------|-------------|--------|
| 1 | test (RED) | Write failing tests for policy_engine | affa977 |
| 2 | feat (GREEN) | Implement policy_engine.py | 1f38032 |

## What Was Built

### PolicyResult (Pydantic v2 model)
```python
class PolicyResult(BaseModel):
    triggered_rules: list[str] = Field(default_factory=list)
    rule_details: list[dict] = Field(default_factory=list)
    escalate: bool = False
    alert_pm: bool = False
```

### evaluate_policies(event, config) -> PolicyResult
- Loads rules YAML from `config.rules_file` via `Path(config.rules_file).open()`
- Iterates all rules, calls `_evaluate_condition()` for each
- Sets `escalate=True` when any triggered rule has priority "critical"
- Sets `alert_pm=True` when any rule fires

### Safe Condition Evaluation
- `_evaluate_condition()` splits on " AND " → all sub-conditions must pass
- `_eval_sub()` tokenizes field/operator/value without eval() or exec()
- Supported operators: `==`, `!=`, `>`, `>=`, `<`, `<=`, `IN`
- `IN` uses `ast.literal_eval` to parse list literals (safe, literals only)
- Unknown fields return False (safe default)
- All exceptions caught and return False

## Demo Scenario Verification

For `quantity=12, material_original=aluminum, material_new=wood, change_type=material_substitution`:

| Rule | Condition | Result |
|------|-----------|--------|
| RULE-003 | estimated_cost > 50000 | Not triggered (cost=None→0) |
| RULE-005 | element_type == 'window' AND quantity > 10 | **TRIGGERED** |
| RULE-007 | change_type == 'material_substitution' | **TRIGGERED** |
| RULE-008 | material_original == 'aluminum' AND material_new == 'wood' AND element_type == 'window' AND quantity > 8 | **TRIGGERED** |
| RULE-011 | change_type IN ['material_substitution', 'scope_change', 'rfi_resolution'] | **TRIGGERED** |
| RULE-015 | change_type == 'material_substitution' AND po_issued == false | **TRIGGERED** |

5 rules triggered (>= 5 required), `escalate=False`, `alert_pm=True`.

For `estimated_cost=60000`: RULE-003 triggers, `escalate=True`.

## Test Coverage

```
tests/unit/test_policy_engine.py — 8 tests, all passing
  test_policy_result_is_valid_pydantic_model
  test_demo_scenario_triggers_rule_005_008_011
  test_demo_scenario_evaluates_at_least_5_rules
  test_high_cost_triggers_rule_003_and_escalate
  test_empty_rules_returns_empty_triggered_list
  test_unknown_field_in_condition_does_not_raise
  test_no_escalate_when_no_critical_rules_triggered
  test_evaluate_policies_returns_policy_result_type
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Module-level EnrichedEvent import triggered config.settings singleton**
- **Found during:** Task 2 (GREEN phase, first test run)
- **Issue:** `policy_engine.py` imported `EnrichedEvent` at module level → chain: enrichment.py → vector_store.py → postgres.py → config.settings → ValidationError on missing env vars
- **Fix:** Moved EnrichedEvent import behind `TYPE_CHECKING` guard; used string annotations `"EnrichedEvent"` in function signatures (Python 3.13 evaluates annotations at runtime without `from __future__ import annotations`)
- **Files modified:** `src/system/domain_processing/policy_engine.py`
- **Commit:** 1f38032

**2. [Rule 1 - Bug] NormalizedEvent has no change_type field (extra="forbid")**
- **Found during:** Task 2, test_demo_scenario_triggers_rule_005_008_011
- **Issue:** Plan's `_build_event_fields` referenced `event.event.change_type` which does not exist on NormalizedEvent (extra="forbid", field was intentionally stripped per STATE.md decision). Test helper also passed `change_type` to NormalizedEvent constructor causing ValidationError.
- **Fix:** `_build_event_fields` derives `change_type` from `event.event.event_type` (the routing classification serves as change_type for rule matching). Test helper passes `change_type` value as `event_type` parameter.
- **Files modified:** `src/system/domain_processing/policy_engine.py`, `tests/unit/test_policy_engine.py`
- **Commit:** 1f38032

**3. [Rule 3 - Blocking] Test isolation: autouse _setup_env fixture needed**
- **Found during:** Task 2, first test run after implementing policy_engine
- **Issue:** Tests importing EnrichedEvent lazily still triggered config.settings via `src.system.context.__init__` package import
- **Fix:** Added autouse `_setup_env` fixture to test file (monkeypatch env vars + sys.modules.pop for full import chain) — matches pattern from test_retrieval.py
- **Files modified:** `tests/unit/test_policy_engine.py`
- **Commit:** 1f38032

## Self-Check: PASSED

- `src/system/domain_processing/policy_engine.py` — exists, 270 lines
- `tests/unit/test_policy_engine.py` — exists, 320+ lines
- Commit affa977 — test(05-03): add failing tests for policy_engine
- Commit 1f38032 — feat(05-03): implement policy_engine.py with safe condition evaluation
- No bare eval()/exec() in policy_engine.py
- All 8 tests passing: `8 passed in 0.27s`
