---
phase: 06-decision-intelligence
plan: 02
subsystem: decision-intelligence
tags: [proposal-generator, sonnet, tenacity, pydantic-v2, tdd]
dependency_graph:
  requires:
    - 06-01  # confidence_scorer, proposal.txt prompt
    - 05-xx  # ProcessingResult from domain_processing.processor
  provides:
    - generate_proposal callable for Phase 7 pipeline entry
  affects:
    - src/system/decision_intelligence/__init__.py (wired)
tech_stack:
  added:
    - tenacity (outer retry on parse/validation failures)
  patterns:
    - TDD (RED/GREEN/REFACTOR)
    - Lazy import pattern for call_sonnet (avoids module-level Anthropic() init)
    - IMPL_AVAILABLE guard + autouse isolate fixture + sys.modules.pop for test isolation
key_files:
  created:
    - src/system/decision_intelligence/proposal_generator.py
    - tests/unit/test_proposal_generator.py
  modified:
    - src/system/decision_intelligence/__init__.py
decisions:
  - "call_sonnet imported lazily inside generate_proposal() body to prevent anthropic.Anthropic() from reading ANTHROPIC_API_KEY at module import time"
  - "Outer @retry on generate_proposal catches JSONDecodeError and ValidationError from parse/validate step; call_sonnet's own inner @retry handles transient API errors separately"
  - "Test retry tests use generate_proposal.__wrapped__ + wait_none() to avoid 2-10s exponential waits in test suite"
  - "action_data stores full raw LLM action dict, so no information is lost if caller needs original fields"
metrics:
  duration: "~2.5 minutes"
  completed: "2026-03-13"
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  tests_passing: 12
---

# Phase 06 Plan 02: Proposal Generator Summary

**One-liner:** Sonnet 4 proposal generation with tenacity retries (3 attempts, exponential backoff) on JSONDecodeError/ValidationError, lazy call_sonnet import, and confidence_score stored as 0-1 fraction.

## What Was Built

`generate_proposal(processing_result: ProcessingResult) -> Proposal` — the core SYSTEM pipeline callable that wires the Phase 6 components together:

1. Reads `config/prompts/proposal.txt` via `Path(__file__)`-relative path (no `config.settings`)
2. Serializes `ProcessingResult` into a JSON user prompt via `_build_user_prompt()`
3. Calls `call_sonnet(prompt, system)` with the loaded system prompt
4. Parses the JSON response, maps `recommended_actions` to `Action` objects
5. Calls `score_proposal()` to compute confidence (0-100), divides by 100 for `Proposal.confidence_score` (0.0-1.0)
6. Builds and returns a validated `Proposal` Pydantic v2 model

The outer `@retry(stop_after_attempt(3), wait_exponential(...), reraise=True)` decorator wraps the entire body so any `json.JSONDecodeError` or `pydantic.ValidationError` from the parse/validate step triggers a retry.

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | TDD failing tests | b2da9b4 | tests/unit/test_proposal_generator.py |
| 1 (GREEN) | Implement proposal_generator.py | 09c7db2 | src/system/decision_intelligence/proposal_generator.py |
| 2 | Wire __init__.py | f4584dd | src/system/decision_intelligence/__init__.py |

## Test Results

All 12 Phase 6 tests pass together:

```
tests/unit/test_confidence_scorer.py   7 passed
tests/unit/test_proposal_generator.py  5 passed
Total: 12 passed in 1.88s
```

Test cases in `test_proposal_generator.py`:
- `test_generate_proposal_success` — happy path, 4 actions, valid event_id and confidence_score
- `test_generate_proposal_retries_on_json_error` — bad JSON twice then valid, confirms 3 calls made
- `test_generate_proposal_raises_after_max_retries` — always bad JSON, raises after 3 attempts
- `test_confidence_score_stored_as_fraction` — verifies score/100 conversion is applied
- `test_actions_mapped_from_llm` — verifies all 4 action_types present and action_data is dict

## Verification

- `python -c "from src.system.decision_intelligence import generate_proposal, score_proposal, ConfidenceResult; print('package imports OK')"` — PASSED
- No `from config.settings import settings` at module level — CONFIRMED
- `Proposal.confidence_score` in [0.0, 1.0] (Pydantic `ge=0.0, le=1.0`) — CONFIRMED
- All live API calls mocked — CONFIRMED

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- FOUND: src/system/decision_intelligence/proposal_generator.py
- FOUND: src/system/decision_intelligence/__init__.py
- FOUND: tests/unit/test_proposal_generator.py
- FOUND commit b2da9b4 (test RED)
- FOUND commit 09c7db2 (feat GREEN)
- FOUND commit f4584dd (feat __init__)
