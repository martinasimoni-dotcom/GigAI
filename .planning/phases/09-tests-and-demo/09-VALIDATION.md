---
phase: 9
slug: tests-and-demo
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + pytest-cov + pytest-asyncio |
| **Config file** | pyproject.toml (`[tool.pytest.ini_options]`) |
| **Quick run command** | `python -m pytest tests/unit/ -q` |
| **Full suite command** | `python -m pytest tests/ -q --ignore=tests/unit/test_postgres.py` |
| **Integration suite** | `python -m pytest tests/integration/ -m integration -q` |
| **Estimated runtime** | ~15 seconds (unit), ~60 seconds (integration with real APIs) |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/unit/ -q`
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 9-01-01 | 01 | 1 | TEST-01 | unit+cov | `python -m pytest tests/unit/ --cov=src --cov-report=term-missing -q` | ⬜ pending |
| 9-01-02 | 01 | 1 | TEST-04 | script | `python scripts/test_retrieval_quality.py --dry-run` | ⬜ pending |
| 9-02-01 | 02 | 2 | TEST-02 | integration | `python -m pytest tests/integration/test_pipeline.py -m integration -q` | ⬜ pending |
| 9-02-02 | 02 | 2 | TEST-03 | script | `python scripts/run_demo.py` | ⬜ pending |
| 9-02-03 | 02 | 2 | TEST-05 | integration | `python -m pytest tests/integration/ -m integration -q` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/integration/` directory with `conftest.py` and `pytest.ini_options` marker registration
- [ ] `tests/fixtures/sample_transcript.json` — valid Fireflies payload
- [ ] `tests/fixtures/expected_proposal.json` — expected Proposal model output
- [ ] `scripts/run_demo.py` — demo script skeleton
- [ ] `scripts/test_retrieval_quality.py` — retrieval quality script skeleton

*Existing unit test infrastructure (190 tests) already covers phases 0-8.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full E2E with live Claude API | TEST-02 | Requires real ANTHROPIC_API_KEY + PostgreSQL | Run `pytest tests/integration/ -m integration` with real .env |
| Dashboard visual acceptance | DASH-05 | Browser required | `cd dashboard && npm run dev`, open localhost:5173 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
