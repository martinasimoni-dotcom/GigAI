---
phase: 02-knowledge-folder
plan: 03
subsystem: knowledge-folder
tags: [seed-script, chunking, pgvector, voyage-3, unit-tests]
dependency_graph:
  requires: [02-01, 02-02]
  provides: [KF-05, seed-script, knowledge-chunk-tests]
  affects: [phase-04-retrieval]
tech_stack:
  added: []
  patterns: [lazy-import-test-pattern, single-batch-embed, bulk-insert-execute_values, path-exists-import-guard]
key_files:
  created:
    - scripts/seed_knowledge_folder.py
  modified:
    - tests/unit/test_knowledge_folder.py
decisions:
  - "Lazy imports inside test functions (not module-level) to avoid pydantic ValidationError from config.settings singleton at pytest collection time — matching test_connectors.py pattern"
  - "Path.exists() import guard instead of try/except import for IMPL_AVAILABLE — avoids triggering settings singleton before env vars are set by autouse fixture"
  - "seed() uses two separate DB connections: one for DELETE (committed independently) and one for INSERT — matches plan spec exactly"
metrics:
  duration_seconds: 269
  completed_date: "2026-03-13"
  tasks_completed: 2
  files_changed: 2
---

# Phase 2 Plan 3: Knowledge Folder Seed Script Summary

Idempotent seed script with 4 chunkers (markdown/team/rules/history), single Voyage-3 batch call, and bulk INSERT via execute_values — all 6 unit tests passing.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Implement seed_knowledge_folder.py | f67ad55 | scripts/seed_knowledge_folder.py |
| 2 | Fill in real test implementations | fd22288 | tests/unit/test_knowledge_folder.py |

## What Was Built

`scripts/seed_knowledge_folder.py` — runnable, idempotent seed script:

- `chunk_markdown_by_sections(text)` — splits on `## ` headings, returns `(heading, section_text)` tuples
- `chunk_team_directory(path)` — one `(meta, text)` tuple per JSON member with `meta["type"] == "team_member"`
- `chunk_rules(path)` — one `(meta, text)` tuple per YAML rule with `meta["rule_id"]` and `"Rule ID:"` in text
- `chunk_historical_patterns(path)` — one `(meta, text)` tuple per JSON event with `meta["event_id"]` and `"Event ID:"` in text
- `seed()` — collects all chunks (42 total), calls `embed_batch()` exactly once with `input_type="document"`, DELETEs existing rows before INSERT, bulk-inserts with per-row metadata via `execute_values`

Chunk counts: 5 glossary + 7 team + 18 rules + 12 history = 42 total (well under 128 Voyage-3 batch limit).

`tests/unit/test_knowledge_folder.py` — 6 unit tests all passing:
- 4 chunker unit tests using `tmp_path` with synthetic data
- 2 seed() behavioral tests using `monkeypatch.setattr` for module-level attribute patching

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test collection failure due to settings singleton ValidationError**
- **Found during:** Task 2
- **Issue:** The plan's proposed `try/except ImportError` import guard failed because `config.settings` raises `pydantic_core.ValidationError` (not `ImportError`) when env vars are absent at pytest collection time. This prevented the test file from being collected entirely.
- **Fix:** Replaced the collection-time import guard with a `Path.exists()` file size check for `IMPL_AVAILABLE`. Moved all module imports to lazy imports inside each test function body (after autouse fixture sets env vars and pops `sys.modules`). This matches the existing `test_connectors.py` pattern already established in the project.
- **Files modified:** `tests/unit/test_knowledge_folder.py`
- **Commit:** fd22288

## Verification Results

```
pytest tests/unit/test_knowledge_folder.py -x -q
......
6 passed in 0.70s

Chunker verification against real content files:
OK: 5 glossary + 7 team + 18 rules + 12 history = 42 total chunks (< 128 Voyage limit)

Importability check:
importable OK
```

## Self-Check: PASSED

- `scripts/seed_knowledge_folder.py` — FOUND (250 lines)
- `tests/unit/test_knowledge_folder.py` — FOUND (6 tests passing)
- Commit f67ad55 — FOUND
- Commit fd22288 — FOUND
