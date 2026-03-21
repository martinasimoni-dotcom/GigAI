---
phase: 00-foundation
plan: 01
subsystem: infra
tags: [pydantic, pydantic-settings, pgvector, postgresql, python, testing, sql]

# Dependency graph
requires: []
provides:
  - requirements.txt with pinned deps (no openai)
  - .env.example with all required env vars
  - config/settings.py: pydantic_settings BaseSettings with fail-fast required fields
  - src/shared/models/events.py: RawEvent, NormalizedEvent Pydantic v2 models
  - src/shared/models/proposals.py: Signal, Action, Proposal Pydantic v2 models
  - src/shared/models/config.py: EventTypeConfig Pydantic v2 model
  - infra/sql/001_create_tables.sql: pgvector extension + 6 tables with vector(1024) columns
  - infra/sql/002_create_indexes.sql: HNSW indexes with vector_cosine_ops + B-tree indexes
  - 8 Wave 0 test stub files collected by pytest with 0 errors
affects:
  - 00-02 (DB layer uses models and settings)
  - all subsequent phases (every phase imports these models)

# Tech tracking
tech-stack:
  added:
    - pydantic>=2.0 (Pydantic v2 BaseModel, field_validator, ConfigDict)
    - pydantic-settings>=2.1.0 (BaseSettings for env var loading)
    - pgvector (vector(1024) SQL column type, HNSW indexes)
  patterns:
    - Pydantic v2 API exclusively (field_validator + @classmethod, ConfigDict, Literal types, Field with constraints)
    - BaseSettings fail-fast pattern: required fields have no defaults, ValidationError raised at startup
    - TDD Red-Green: test stubs created before implementation modules exist
    - Lazy imports in test stubs using try/except to allow pytest collection before implementation

key-files:
  created:
    - requirements.txt
    - .env.example
    - config/__init__.py
    - config/settings.py
    - src/shared/models/events.py
    - src/shared/models/proposals.py
    - src/shared/models/config.py
    - infra/sql/001_create_tables.sql
    - infra/sql/002_create_indexes.sql
    - tests/__init__.py
    - tests/unit/__init__.py
    - tests/conftest.py
    - tests/unit/test_scaffold.py
    - tests/unit/test_settings.py
    - tests/unit/test_models_events.py
    - tests/unit/test_models_proposals.py
    - tests/unit/test_models_config.py
    - tests/unit/test_sql_migrations.py
  modified:
    - pyproject.toml (removed --cov addopts, asyncio_mode, updated deps, requires-python=3.11)

key-decisions:
  - "No openai package anywhere — requirements.txt uses anthropic>=0.40.0 and voyageai>=0.2.3 exclusively"
  - "Pydantic v2 API only — field_validator with @classmethod, ConfigDict, no v1 @validator decorators"
  - "Settings module-level singleton settings = Settings() causes fail-fast behavior at import time when env vars missing"
  - "SQL migration uses pgvector HNSW syntax: USING hnsw (embedding vector_cosine_ops) for cosine similarity"
  - "Test stubs use lazy imports (try/except ImportError → pytest.skip) to allow pytest collection before implementation exists"

patterns-established:
  - "Pydantic v2 validators: use @field_validator + @classmethod, not @validator (v1 deprecated)"
  - "Settings fail-fast: BaseSettings with required fields (no defaults) raises ValidationError at module import if env missing"
  - "SQL vectors: vector(1024) column type, HNSW index with vector_cosine_ops for cosine similarity"
  - "Test isolation: test_settings tests delete sys.modules cache to force fresh import with new env state"

requirements-completed: [FOUND-01, FOUND-06, FOUND-07, FOUND-08, FOUND-09, FOUND-10]

# Metrics
duration: 7min
completed: 2026-03-12
---

# Phase 0 Plan 01: Foundation Scaffold Summary

**Pydantic v2 data models (RawEvent, NormalizedEvent, Signal, Action, Proposal, EventTypeConfig), fail-fast pydantic_settings config, pgvector SQL schema with 6 tables + HNSW indexes, and 30 passing Wave 0 unit tests**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-12T15:09:34Z
- **Completed:** 2026-03-12T15:16:41Z
- **Tasks:** 3
- **Files modified:** 19

## Accomplishments

- All 30 unit tests pass green: scaffold (7), settings (4), models (10), SQL migrations (7), config (2)
- Pydantic v2 models enforce all domain constraints: Literal source validation, forbidden extra fields, non-empty summary, confidence score bounds, action type allowlist
- SQL migration defines pgvector extension + 6 tables with vector(1024) embeddings and HNSW cosine similarity indexes
- Settings module fails fast with pydantic ValidationError if ANTHROPIC_API_KEY, VOYAGE_API_KEY, or DATABASE_URL missing from environment

## Task Commits

Each task was committed atomically:

1. **Task 1: Wave 0 test stubs** - `0113983` (test)
2. **Task 2: Project scaffold** - `d24e3f5` (feat)
3. **Task 3: Pydantic models + SQL migrations** - `1d51dcf` (feat)

**Plan metadata:** (docs commit — created after summary)

_Note: TDD tasks have test commit (RED) bundled with implementation commit (GREEN) per plan structure._

## Files Created/Modified

- `requirements.txt` — Cleaned: no openai, has anthropic>=0.40.0, voyageai>=0.2.3, pydantic-settings, pgvector
- `.env.example` — All required env vars: ANTHROPIC_API_KEY, VOYAGE_API_KEY, DATABASE_URL, GCP, ACC, Gmail
- `config/__init__.py` — Package marker
- `config/settings.py` — pydantic_settings BaseSettings with 3 required fields, fail-fast on missing
- `src/shared/models/events.py` — RawEvent (Literal source), NormalizedEvent (extra=forbid, non-empty summary)
- `src/shared/models/proposals.py` — Signal, Action (Literal action_type), Proposal (confidence_score 0-1 bounds)
- `src/shared/models/config.py` — EventTypeConfig with list field defaults
- `infra/sql/001_create_tables.sql` — CREATE EXTENSION IF NOT EXISTS vector + 6 tables + vector(1024) columns
- `infra/sql/002_create_indexes.sql` — HNSW indexes with vector_cosine_ops + B-tree indexes on FK/status
- `pyproject.toml` — Updated: requires-python>=3.11, cleaned deps (no openai), removed broken addopts
- `tests/conftest.py` — Shared fixtures: mock_anthropic_client, mock_voyage_client, mock_db_conn, test_env
- `tests/unit/test_scaffold.py` — 7 tests for requirements.txt and .env.example
- `tests/unit/test_settings.py` — 4 tests for Settings fail-fast behavior
- `tests/unit/test_models_events.py` — 5 tests for RawEvent and NormalizedEvent
- `tests/unit/test_models_proposals.py` — 5 tests for Signal, Action, Proposal
- `tests/unit/test_models_config.py` — 2 tests for EventTypeConfig
- `tests/unit/test_sql_migrations.py` — 7 tests for SQL migration files

## Decisions Made

- Used `Literal["fireflies", "acc", "gmail", "calendar"]` for source validation (not a custom validator) — simpler and gives better error messages
- Settings module-level singleton `settings = Settings()` is intentional: causes fail-fast at import time, which tests cover by catching the ValidationError that propagates from the import
- HNSW index syntax uses `ON table_name USING hnsw (column ops)` form (pgvector >= 0.5.0 syntax) rather than the older index method syntax

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed pyproject.toml addopts that prevented pytest collection**
- **Found during:** Task 1 (Wave 0 test stubs)
- **Issue:** pyproject.toml had `--cov=src --cov-report=*` in addopts and `asyncio_mode = "auto"` — pytest-cov and pytest-asyncio are not installed, causing INTERNALERROR with `--strict-config` on collection
- **Fix:** Removed `--cov` addopts, `asyncio_mode = "auto"`, and `--strict-config` from pyproject.toml pytest config
- **Files modified:** pyproject.toml
- **Verification:** `python -m pytest tests/ --collect-only -q` shows 30 tests collected, 0 errors
- **Committed in:** 0113983 (Task 1 commit)

**2. [Rule 1 - Bug] Fixed test_settings.py import strategy for module-level singleton**
- **Found during:** Task 2 (scaffold implementation)
- **Issue:** Initial test strategy used `from config.settings import Settings` inside test then called `Settings(_env_file=None)`, but the module-level `settings = Settings()` executes at import time and raises ValidationError before the `with pytest.raises()` block is entered
- **Fix:** Updated tests to wrap the entire `import config.settings` statement inside `pytest.raises()`, since the ValidationError propagates out of the import itself
- **Files modified:** tests/unit/test_settings.py
- **Verification:** All 4 settings tests pass green
- **Committed in:** d24e3f5 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both fixes necessary for correct test behavior. No scope creep.

## Issues Encountered

- Python user site-packages path required verifying that `pydantic` was accessible to the correct Python binary. Confirmed via `python -c "import pydantic; print(pydantic.VERSION)"` — version 2.12.5 was already installed.

## User Setup Required

None - no external service configuration required for this plan. All test infrastructure runs without external dependencies.

## Next Phase Readiness

- All data contracts defined and validated — ready for Plan 00-02 (DB layer + LLM clients)
- Settings module provides all env var access patterns needed by postgres.py, claude.py, voyage.py
- Pydantic models provide input/output types for all pipeline stages
- SQL migrations ready to run against a PostgreSQL + pgvector database

## Self-Check: PASSED

All 18 implementation files verified to exist. All 3 task commits (0113983, d24e3f5, 1d51dcf) verified in git history. 30/30 tests pass green.

---
*Phase: 00-foundation*
*Completed: 2026-03-12*
