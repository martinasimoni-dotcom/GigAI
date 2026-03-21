---
phase: 3
slug: data-processing
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-12
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml (testpaths = ["tests"]) |
| **Quick run command** | `pytest tests/unit/test_normalizer.py tests/unit/test_scope_filter.py tests/unit/test_router.py -x -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~20 seconds (unit only, all Haiku calls mocked) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/unit/test_normalizer.py tests/unit/test_scope_filter.py tests/unit/test_router.py -x -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 03-01 | 0 | PROC-01..05 | unit | `pytest tests/unit/test_normalizer.py tests/unit/test_scope_filter.py tests/unit/test_router.py --collect-only -q` | ❌ W0 | ⬜ pending |
| 3-01-02 | 03-01 | 0 | PROC-02 | unit | `pytest tests/unit/test_models_events.py -x -q` | ✅ exists | ⬜ pending |
| 3-02-01 | 03-02 | 1 | PROC-01,02 | unit | `pytest tests/unit/test_normalizer.py -x -q` | ❌ W0 | ⬜ pending |
| 3-02-02 | 03-02 | 1 | PROC-03 | unit | `pytest tests/unit/test_scope_filter.py -x -q` | ❌ W0 | ⬜ pending |
| 3-03-01 | 03-03 | 2 | PROC-04,05 | unit | `pytest tests/unit/test_router.py -x -q` | ❌ W0 | ⬜ pending |
| 3-03-02 | 03-03 | 2 | PROC-04,05 | unit | `pytest tests/unit/test_router.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_normalizer.py` — stubs for PROC-01, PROC-02
- [ ] `tests/unit/test_scope_filter.py` — stubs for PROC-03
- [ ] `tests/unit/test_router.py` — stubs for PROC-04, PROC-05
- [ ] NormalizedEvent model updated with `review_required`, `confidence`, `estimated_cost` fields

*Existing conftest.py has mock_llm fixtures. Need: mock_call_haiku fixture for data_processing tests.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Demo transcript produces NormalizedEvent with correct fields | PROC-02 | Requires live ANTHROPIC_API_KEY | Set API key, run `python -c "from src.system.data_processing.normalizer import normalize_event; ..."` with sample transcript |
| Router classifies demo transcript as material_change | PROC-05 | Requires live ANTHROPIC_API_KEY | Set API key, run `python -c "from src.system.data_processing.router import route_event; ..."` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
