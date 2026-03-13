---
phase: 2
slug: knowledge-folder
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-12
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml (testpaths = ["tests"]) |
| **Quick run command** | `pytest tests/unit/test_knowledge_folder.py -x -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds (unit only, mocked externals) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/unit/test_knowledge_folder.py -x -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 02-01 | 0 | KF-01..05 | unit | `pytest tests/unit/test_knowledge_folder.py -x -q` | ❌ W0 | ⬜ pending |
| 2-01-02 | 02-01 | 1 | KF-01 | manual+auto | `python -c "import json; open('knowledge_folder/glossary/demo_project.md')"` | ❌ W0 | ⬜ pending |
| 2-01-03 | 02-01 | 1 | KF-02 | auto | `python -c "import json; d=json.load(open('knowledge_folder/team_directory/demo_project.json')); assert len(d)>=6"` | ❌ W0 | ⬜ pending |
| 2-01-04 | 02-01 | 1 | KF-03 | auto | `python -c "import yaml; d=yaml.safe_load(open('knowledge_folder/rules/demo_project.yaml')); assert len(d.get('rules',[]))>=15"` | ❌ W0 | ⬜ pending |
| 2-01-05 | 02-01 | 1 | KF-04 | auto | `python -c "import json; d=json.load(open('knowledge_folder/historical_patterns/demo_project.json')); assert len(d)>=10"` | ❌ W0 | ⬜ pending |
| 2-02-01 | 02-02 | 2 | KF-05 | unit | `pytest tests/unit/test_knowledge_folder.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_knowledge_folder.py` — stubs for KF-01 through KF-05 (chunker logic, seed script)

*Existing conftest.py from Phase 0/1 covers mock DB and mock Voyage fixtures.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Running seed script against live DB populates knowledge_chunks table with ~45 rows | KF-05 | Requires live PostgreSQL with pgvector + live VOYAGE_API_KEY | Set env vars, run `python scripts/seed_knowledge_folder.py`, verify with `psql $DATABASE_URL -c "SELECT COUNT(*) FROM knowledge_chunks;"` |
| Semantic search returns relevant chunks for "window aluminum substitution" query | KF-05 | Requires live DB + live Voyage embeddings | Run `python -c "from src.shared.db.vector_store import search; print(search('window aluminum substitution', top_k=3))"` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
