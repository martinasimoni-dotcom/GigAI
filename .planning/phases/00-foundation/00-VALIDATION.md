---
phase: 0
slug: foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-12
---

# Phase 0 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml (testpaths = ["tests"]) |
| **Quick run command** | `pytest tests/unit/ -x -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds (unit only, mocked externals) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/unit/ -x -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 0-01-01 | 01 | 1 | FOUND-01 | unit | `pytest tests/unit/test_settings.py -x -q` | ❌ W0 | ⬜ pending |
| 0-01-02 | 01 | 1 | FOUND-02 | unit | `pytest tests/unit/test_postgres.py -x -q` | ❌ W0 | ⬜ pending |
| 0-01-03 | 01 | 1 | FOUND-03 | unit | `pytest tests/unit/test_vector_store.py -x -q` | ❌ W0 | ⬜ pending |
| 0-01-04 | 01 | 1 | FOUND-04 | unit | `pytest tests/unit/test_claude_client.py -x -q` | ❌ W0 | ⬜ pending |
| 0-01-05 | 01 | 1 | FOUND-05 | unit | `pytest tests/unit/test_voyage_client.py -x -q` | ❌ W0 | ⬜ pending |
| 0-01-06 | 01 | 1 | FOUND-06 | unit | `pytest tests/unit/test_models_events.py -x -q` | ❌ W0 | ⬜ pending |
| 0-01-07 | 01 | 1 | FOUND-07 | unit | `pytest tests/unit/test_models_proposals.py -x -q` | ❌ W0 | ⬜ pending |
| 0-01-08 | 01 | 1 | FOUND-08 | unit | `pytest tests/unit/test_models_config.py -x -q` | ❌ W0 | ⬜ pending |
| 0-01-09 | 01 | 1 | FOUND-09 | manual | See manual verifications | N/A | ⬜ pending |
| 0-01-10 | 01 | 1 | FOUND-10 | unit | `pytest tests/unit/test_settings.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/__init__.py` — package marker
- [ ] `tests/unit/__init__.py` — package marker
- [ ] `tests/conftest.py` — shared fixtures (mock DB, mock LLM responses, mock Voyage responses)
- [ ] `tests/unit/test_settings.py` — stubs for FOUND-01, FOUND-10
- [ ] `tests/unit/test_postgres.py` — stubs for FOUND-02
- [ ] `tests/unit/test_vector_store.py` — stubs for FOUND-03
- [ ] `tests/unit/test_claude_client.py` — stubs for FOUND-04
- [ ] `tests/unit/test_voyage_client.py` — stubs for FOUND-05
- [ ] `tests/unit/test_models_events.py` — stubs for FOUND-06
- [ ] `tests/unit/test_models_proposals.py` — stubs for FOUND-07
- [ ] `tests/unit/test_models_config.py` — stubs for FOUND-08

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SQL migrations run cleanly, pgvector tables + HNSW indexes exist | FOUND-09 | Requires live PostgreSQL with pgvector extension installed | Run `psql $DATABASE_URL -f infra/sql/001_create_tables.sql` then `infra/sql/002_create_indexes.sql`; verify with `\dt` and `\di` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
