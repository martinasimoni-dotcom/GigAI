---
phase: 06-decision-intelligence
plan: "01"
subsystem: decision-intelligence
tags: [confidence-scoring, proposal-prompt, pydantic-v2, tdd, no-llm]
dependency_graph:
  requires:
    - src/system/domain_processing/processor.py (ProcessingResult)
    - src/system/context/historical.py (HistoricalMatch)
    - src/shared/models/proposals.py (Proposal, Action, Signal)
  provides:
    - config/prompts/proposal.txt (Sonnet 4 system prompt)
    - src/system/decision_intelligence/confidence_scorer.py (score_proposal, ConfidenceResult)
  affects:
    - src/system/decision_intelligence/proposal_generator.py (reads proposal.txt as system prompt)
tech_stack:
  added: []
  patterns:
    - "4-factor weighted confidence formula (no LLM, deterministic)"
    - "TYPE_CHECKING guard for runtime-free Pydantic model imports"
    - "TDD RED/GREEN with IMPL_AVAILABLE Path.exists() guard"
    - "MagicMock for deep Pydantic model chains in tests"
key_files:
  created:
    - config/prompts/proposal.txt
    - src/system/decision_intelligence/confidence_scorer.py
    - tests/unit/test_confidence_scorer.py
  modified: []
decisions:
  - "Used confidence=60 (not 95) in demo scenario to produce ~85.5 score (plan specifies ~86 ±3)"
  - "7 tests written (plan required 5+): added boundary tests for score=80 and score=50 edge cases"
  - "TYPE_CHECKING import guard keeps confidence_scorer.py importable without triggering ProcessingResult/HistoricalMatch import chains at runtime"
metrics:
  duration: "~3 minutes"
  completed_date: "2026-03-13"
  tasks_completed: 2
  files_created: 3
  files_modified: 0
---

# Phase 06 Plan 01: Decision Intelligence Foundation Summary

Sonnet 4 proposal prompt and deterministic 4-factor confidence scorer with full TDD unit tests.

## What Was Built

### Task 1: config/prompts/proposal.txt

Full Sonnet 4 system prompt (6216 chars) for construction material change proposal generation. Sets role, describes input context, specifies all four action types (email, task, calendar, drawing), provides the complete JSON output schema inline, includes a concrete demo example (aluminum-to-wood window substitution with Jane Miller / Mike Torres / calendar / A-301 drawing), and instructs output-only JSON with no markdown.

### Task 2: confidence_scorer.py + test_confidence_scorer.py (TDD)

**RED phase:** 7 tests written and confirmed skipping via `IMPL_AVAILABLE` guard (`Path.exists() + st_size > 10`). Tests cover demo scenario, high-cost reject, medium review, empty historical matches, ConfidenceResult field validation, and two boundary cases (score=80, score=50 both map to "review").

**GREEN phase:** Implemented `score_proposal()` with the locked 4-factor formula:

| Factor | Weight | Logic |
|--------|--------|-------|
| data_clarity | 30% | `NormalizedEvent.confidence / 100.0` |
| historical_match | 25% | `mean(m.similarity)` or 0.0 if empty |
| cost_acceptable | 25% | 1.0 if cost ≤ 50K or None, 0.0 if cost > 50K |
| no_red_flags | 20% | 0.5 if `escalate_immediately`, 1.0 otherwise |

Recommendation thresholds: `>80` → accept, `50–80` → review, `<50` → reject.

## Test Results

```
7 passed in 0.04s

test_confidence_result_fields        PASSED
test_demo_scenario                   PASSED  (score=85.5, accept)
test_high_cost_reject                PASSED  (score=20.75, reject)
test_medium_confidence_review        PASSED  (score=76.75, review)
test_no_historical_matches           PASSED  (score=66.0, review)
test_boundary_exactly_80_is_review   PASSED
test_boundary_exactly_50_is_review   PASSED
```

## Verification

- `config/prompts/proposal.txt`: 6216 chars, contains `event_summary`, `recommended_actions`, `action_type`, `confidence_rationale`, `Jane Miller`
- `score_proposal()` demo scenario: `confidence=60, similarities=[0.92,0.88,0.90], cost=30K` → score=85.5 (within ±3 of 86)
- `score_proposal()` high-cost reject: `confidence=15, cost=75K, escalate=True` → score=20.75 (< 50, reject)
- Weights sum: 0.30 + 0.25 + 0.25 + 0.20 = 1.00

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

### Notes

- The plan's `<action>` section specified using `confidence=60` (not 95) for the demo scenario to hit the ~86% target. The math was pre-verified in the plan itself: `0.60*30 + 0.90*25 + 1.0*25 + 1.0*20 = 85.5`. This was intentional per the plan, not a deviation.
- Added 2 boundary tests (`test_boundary_exactly_80_is_review`, `test_boundary_exactly_50_is_review`) beyond the required 5. These confirm the `>80` and `<50` exclusive thresholds. Tracked as a positive addition.

## Self-Check

- [x] `config/prompts/proposal.txt` exists and has 6216 chars
- [x] `src/system/decision_intelligence/confidence_scorer.py` exists with `score_proposal` and `ConfidenceResult`
- [x] `tests/unit/test_confidence_scorer.py` exists with 7 tests, all passing
- [x] Commits: b72f7b9 (proposal.txt), 1a7dfbc (TDD RED tests), 8fb1eb3 (scorer implementation)

## Self-Check: PASSED
