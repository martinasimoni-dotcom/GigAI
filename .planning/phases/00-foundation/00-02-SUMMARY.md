---
phase: 00-foundation
plan: 02
subsystem: database
tags: [psycopg2, pgvector, postgres, voyageai, anthropic, embeddings, vector-search, tdd]

# Dependency graph
requires:
  - phase: 00-01
    provides: config/settings.py (fail-fast BaseSettings), src/shared/models/events.py, src/shared/models/proposals.py
provides:
  - src/shared/db/postgres.py: ThreadedConnectionPool with register_vector per-connection + execute/fetch_one/fetch_all/execute_many
  - src/shared/db/vector_store.py: embed_and_store (input_type="document") + search with <=> cosine operator (input_type="query")
  - src/shared/llm/claude.py: call_sonnet (claude-sonnet-4-20250514) and call_haiku (claude-haiku-4-5-20251001) with output_schema support
  - src/shared/llm/voyage.py: embed_text (result.embeddings[0]) and embed_batch (result.embeddings) using voyage-3
  - 22 new unit tests all passing green (total suite: 52 tests)
affects:
  - all subsequent phases (every pipeline stage uses DB layer and LLM clients)
  - phases 1-9 (postgres.py and vector_store.py are the shared infrastructure)

# Tech tracking
tech-stack:
  added:
    - psycopg2-binary>=2.9 (PostgreSQL driver with ThreadedConnectionPool)
    - pgvector>=0.2.4 (register_vector psycopg2 adapter)
    - anthropic>=0.40.0 (already in requirements, now implemented)
    - voyageai>=0.2.3 (already in requirements, now implemented)
    - tenacity>=8.2.3 (retry decorator for LLM calls)
  patterns:
    - register_vector per-connection: called on each pool.getconn() result, not once globally
    - voyage lazy client init: _get_client() prevents import-time AuthenticationError when VOYAGE_API_KEY not set
    - asymmetric embeddings: input_type="document" for storage, input_type="query" for retrieval
    - result.embeddings[0] access: voyageai returns EmbeddingsObject, not plain list
    - autouse env fixtures in tests that import modules with module-level settings

key-files:
  created:
    - src/shared/db/postgres.py
    - src/shared/db/vector_store.py
    - src/shared/llm/claude.py
    - src/shared/llm/voyage.py
    - tests/unit/test_postgres.py
    - tests/unit/test_vector_store.py
    - tests/unit/test_claude_client.py
    - tests/unit/test_voyage_client.py
  modified: []

key-decisions:
  - "register_vector(conn) called per-connection in get_connection() — not once globally — to avoid psycopg2.ProgrammingError on vector adaptation"
  - "voyage.py uses lazy _get_client() init (not module-level) to prevent AuthenticationError at import time when VOYAGE_API_KEY not in env"
  - "result.embeddings[0] for single embed, result.embeddings for batch — voyageai returns EmbeddingsObject not list"
  - "DB tests use autouse fixture that sets env vars + pops sys.modules to handle fail-fast settings singleton"
  - "vector_store tests use patch.object(vector_store, 'execute_values') not string-based patch to avoid module identity issues across test runs"

patterns-established:
  - "Per-connection pgvector registration: call register_vector(conn) inside get_connection() every time"
  - "Lazy client init pattern for external SDKs that validate API keys on Client() construction"
  - "Test isolation for fail-fast settings: autouse monkeypatch fixture sets env vars + pops sys.modules cache"
  - "Use patch.object(module, 'func') not patch('module.path.func') when module identity changes across test runs"

requirements-completed: [FOUND-02, FOUND-03, FOUND-04, FOUND-05]

# Metrics
duration: 9min
completed: 2026-03-12
---

# Phase 0 Plan 02: DB Layer + LLM Clients Summary

**psycopg2 ThreadedConnectionPool with per-connection register_vector, pgvector cosine similarity search using <=> operator, Claude Sonnet/Haiku wrappers with tenacity retry, and Voyage-3 lazy client with asymmetric document/query embeddings — 52 tests all green**

## Performance

- **Duration:** 9 min
- **Started:** 2026-03-12T15:20:32Z
- **Completed:** 2026-03-12T15:30:17Z
- **Tasks:** 3 (Wave 0 stubs + DB layer + LLM clients)
- **Files modified:** 8

## Accomplishments

- All 22 new unit tests pass green; full suite 52/52 with zero failures
- postgres.py implements the critical register_vector per-connection pattern — prevents psycopg2.ProgrammingError on vector type adaptation
- vector_store.py uses asymmetric Voyage-3 embeddings (document type for storage, query type for retrieval) with pgvector <=> cosine distance operator
- claude.py locks model strings as named constants (SONNET_MODEL, HAIKU_MODEL) with tenacity retry and optional structured output via output_schema
- voyage.py uses lazy _get_client() to avoid import-time AuthenticationError when API key not set in test environment

## Task Commits

Each task was committed atomically:

1. **Task 1: Wave 0 test stubs** - `91e1cac` (test)
2. **Task 2: DB layer (postgres.py, vector_store.py)** - `90be779` (feat)
3. **Task 3: LLM clients (claude.py, voyage.py)** - `23e25f3` (feat)

**Plan metadata:** (docs commit — created after summary)

_Note: TDD tasks have test commit (RED) bundled with implementation commit (GREEN) per plan structure. Tasks 2 and 3 were committed separately though voyage.py was needed to unblock vector_store tests._

## Files Created/Modified

- `src/shared/db/postgres.py` — ThreadedConnectionPool, get_connection() with register_vector, execute/fetch_one/fetch_all/execute_many
- `src/shared/db/vector_store.py` — embed_and_store() with execute_values + embed_batch(input_type="document"), search() with embed_text(input_type="query") and <=> operator
- `src/shared/llm/claude.py` — call_sonnet()/call_haiku() with SONNET_MODEL/HAIKU_MODEL constants, tenacity retry, optional output_schema
- `src/shared/llm/voyage.py` — lazy _get_client(), embed_text() returning result.embeddings[0], embed_batch() returning result.embeddings
- `tests/unit/test_postgres.py` — 5 tests: register_vector call, execute, fetch_one, fetch_all, execute_many
- `tests/unit/test_vector_store.py` — 5 tests: embed_batch document type, knowledge_chunks INSERT, embed_text query type, search returns list, <=> cosine operator
- `tests/unit/test_claude_client.py` — 6 tests: string return, model strings, system prompt, output_schema passthrough
- `tests/unit/test_voyage_client.py` — 6 tests: 1024-float return, query/document input types, .embeddings attribute access, voyage-3 model

## Decisions Made

- Lazy init for voyageai.Client() — voyageai raises AuthenticationError at Client() construction time without API key (unlike anthropic which defers the check). Used `_get_client()` accessor with module-level `_client: voyageai.Client | None = None` to prevent import-time failure in test environments.
- Test autouse env fixture — postgres.py and vector_store.py import config.settings at module level (fail-fast by design per Plan 01). Tests that import these modules need env vars set BEFORE import. Used `autouse=True` monkeypatch fixture that also pops sys.modules cache to force clean reimport.
- `patch.object(module, attr)` vs `patch(path)` — when `sys.modules` is popped between tests, the string-based `patch("src.shared.db.vector_store.execute_values")` can target a stale/different module instance. `patch.object(vector_store, "execute_values")` binds to the locally-imported module object, which is always correct.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed missing Python packages**
- **Found during:** Task 2 (DB layer implementation)
- **Issue:** psycopg2-binary, pgvector, anthropic, voyageai, tenacity not installed for the Python 3.13 Windows Store interpreter used by pytest
- **Fix:** Ran `python -m pip install psycopg2-binary pgvector anthropic voyageai tenacity` using the correct Python executable
- **Files modified:** None (pip install only)
- **Verification:** `python -c "import psycopg2, pgvector, anthropic, voyageai, tenacity"` succeeds
- **Committed in:** 90be779 (Task 2 commit, not a file change)

**2. [Rule 1 - Bug] Fixed test_postgres.py: module reimport broke env var context**
- **Found during:** Task 2 (running DB tests)
- **Issue:** Original test used `sys.modules.pop + from src.shared.db import postgres` inside the patch context to force reimport; the reimport triggered `config.settings` import which failed without env vars
- **Fix:** Replaced with `autouse` monkeypatch fixture that sets env vars + pops sys.modules before each test; simplified test to `patch.object(postgres, "get_pool", ...)` instead of reimporting
- **Files modified:** tests/unit/test_postgres.py
- **Verification:** All 5 postgres tests pass green
- **Committed in:** 90be779 (Task 2 commit)

**3. [Rule 1 - Bug] Fixed voyageai.Client() import-time AuthenticationError**
- **Found during:** Task 3 (running voyage tests)
- **Issue:** voyageai.Client() raises AuthenticationError on construction without VOYAGE_API_KEY; module-level `_client = voyageai.Client()` caused ImportError during test collection
- **Fix:** Changed to lazy init — `_client: voyageai.Client | None = None` + `_get_client()` accessor called inside embed_text/embed_batch
- **Files modified:** src/shared/llm/voyage.py
- **Verification:** `python -c "from src.shared.llm import voyage"` succeeds without env var; all 6 voyage tests pass
- **Committed in:** 23e25f3 (Task 3 commit)

**4. [Rule 1 - Bug] Fixed test_vector_store.py: execute_values patch target identity issue**
- **Found during:** Task 2 (running vector store tests in sequence)
- **Issue:** `patch("src.shared.db.vector_store.execute_values")` failed to mock when running after another test that had popped `src.shared.db.vector_store` from sys.modules — the real execute_values was called instead of the mock
- **Fix:** Changed to `patch.object(vector_store, "execute_values")` which binds to the locally-imported module instance
- **Files modified:** tests/unit/test_vector_store.py
- **Verification:** All 5 vector_store tests pass green in sequence
- **Committed in:** 90be779 (Task 2 commit)

---

**Total deviations:** 4 auto-fixed (1 blocking, 3 bugs)
**Impact on plan:** All fixes necessary for tests to pass in this environment (Windows, Python 3.13, no .env file). No scope creep. Core implementation matches plan spec exactly.

## Issues Encountered

- Windows Store Python 3.13 interpreter has a separate pip location from conda environments — packages installed to `C:\Users\Rafik\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\site-packages`
- voyageai v0.3.7 raises at Client() construction time (not on first API call) — differs from anthropic SDK behavior

## User Setup Required

None - all tests run without external service connections. DB and API calls are fully mocked.

## Next Phase Readiness

- Shared infrastructure complete — postgres.py, vector_store.py, claude.py, voyage.py ready for Phase 1+ imports
- All 4 modules pass their unit tests with proper isolation via mocking
- Full unit suite: 52/52 green, Phase 0 complete
- Ready for Phase 1: Input Layer (webhooks, connectors)

## Self-Check: PASSED

---
*Phase: 00-foundation*
*Completed: 2026-03-12*
