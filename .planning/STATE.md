---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: unknown
last_updated: "2026-03-13T11:47:17.511Z"
progress:
  total_phases: 10
  completed_phases: 3
  total_plans: 10
  completed_plans: 10
---

# STATE.md — GigAI
## Project Memory (Updated Each Session)

---

## Project Reference

**Project:** GigAI — Material Change Coordination Automation
**Core Value:** Eliminate manual PM coordination burden for material changes by automating capture, enrichment, proposal generation, and action execution — reducing 4 hours of work to under 12 minutes per change.
**Current Focus:** Phase 0 — Foundation

---

## Current Position

| Field | Value |
|-------|-------|
| Current Phase | Phase 2: Knowledge Folder |
| Current Plan | 02-03 complete |
| Status | Phase 2 complete |
| Last Updated | 2026-03-13 |
| Stopped At | Completed 02-knowledge-folder 02-03-PLAN.md |

### Progress Bar

```
Phase 0  [##########] 100% (2/2 plans complete)
Phase 1  [##########] 100% (5/5 plans complete)
Phase 2  [##########] 100% (3/3 plans complete)
Phase 3  [          ] 0%
Phase 4  [          ] 0%
Phase 5  [          ] 0%
Phase 6  [          ] 0%
Phase 7  [          ] 0%
Phase 8  [          ] 0%
Phase 9  [          ] 0%

Overall: 3/10 phases complete (10/10 total plans)
```

---

## Performance Metrics

| Metric | Target | Current |
|--------|--------|---------|
| PM coordination time reduction | 80% | Not measured |
| High-confidence proposal accuracy | >90% | Not measured |
| Event-to-proposal latency | <5 min | Not measured |
| PM acceptance rate | 75% | Not measured |

## Execution Metrics

| Phase | Duration | Tasks | Files |
|-------|----------|-------|-------|
| Phase 01-input-layer P02 | 6 min | 2 tasks | 3 files |
| Phase 01-input-layer P03 | 18 min | 2 tasks | 4 files |
| Phase 01-input-layer P04 | 5 min | 2 tasks | 3 files |
| Phase 01-input-layer P05 | 3 min | 1 task | 1 file |
| Phase 02-knowledge-folder P01 | 1 min | 1 task | 1 file |
| Phase 02-knowledge-folder P02 | 3 min | 3 tasks | 4 files |
| Phase 02-knowledge-folder P03 | 5 min | 2 tasks | 2 files |

## Accumulated Context

### Key Decisions Made

- **LLM stack**: Claude Sonnet 4 for proposals, Claude Haiku 4.5 for normalization/routing. No OpenAI, no fine-tuning, no spaCy.
- **Embeddings**: Voyage-3 at 1024 dimensions via voyageai Python package.
- **Database**: PostgreSQL 15 + pgvector with HNSW indexes. All structured state and vector store in one database.
- **Event bus**: Google Cloud Pub/Sub (at-least-once delivery). Topics: raw-events, normalized-events, enriched-events, signals.
- **No Claude Vision**: Drawing markups go through ACC markup API only.
- **Human-in-the-loop enforced**: Nothing executes without PM approval. >80% confidence = recommend accept, not auto-execute.
- **Demo scenario**: Window material substitution — Aluminum to Wood, 3rd Floor, 12 Units (W-301 to W-312). All demo data must support this exact scenario end-to-end.
- **Confidence weights**: Data clarity 30%, historical match 25%, cost acceptable 25%, no red flags 20%.
- **Config-driven pipeline**: Domain processing code is identical across event types; behavior is driven by YAML configs loaded per event_type.
- **Pydantic v2 API only**: Use field_validator + @classmethod and ConfigDict. No v1 @validator decorators (raises PydanticUserError).
- **Settings fail-fast**: module-level `settings = Settings()` singleton raises ValidationError at import if required env vars missing.
- **SQL vector indexes**: HNSW syntax is `USING hnsw (embedding vector_cosine_ops)` — operator class required for cosine similarity (pgvector >= 0.5.0).
- **No openai package**: requirements.txt uses anthropic>=0.40.0 exclusively. openai is banned from the project.
- **register_vector per-connection**: pgvector register_vector(conn) must be called on each individual connection from the pool, not once globally — prevents psycopg2.ProgrammingError on vector type adaptation.
- **Voyage lazy client**: voyageai.Client() raises AuthenticationError at construction (unlike anthropic which defers). Using _get_client() lazy accessor to prevent import-time failure.
- **result.embeddings[0] pattern**: voyageai embed() returns EmbeddingsObject. Access result.embeddings[0] (single) or result.embeddings (batch) — never result[0].
- **Asymmetric embeddings**: input_type="document" for storage, input_type="query" for retrieval — improves cosine similarity recall quality.
- **patch.object for test isolation**: When sys.modules is popped between tests, use patch.object(module, 'attr') not string-based patch("module.path.attr") to avoid module identity issues.
- **Wave 0 import-guard pattern**: Test stub files guard imports with try/except ImportError + pytestmark.skipif so files are always collectable even before implementation modules exist.
- **pytest anyio plugin**: Use pytest_plugins = ("anyio",) in async test files to parametrize across asyncio and trio backends.
- **sys.modules.pop for settings-dependent tests**: When testing modules that transitively import config.settings singleton, autouse fixture must setenv + pop sys.modules before import — matches test_postgres.py pattern. Required for any module importing config.settings.
- **future.result() synchronous in publish_event**: Pub/Sub publish() is internally async; calling future.result() synchronously surfaces GoogleAPICallError immediately rather than silently dropping failures.
- **sys.modules.pop must include PACKAGE module**: When popping submodules for test isolation, also pop the parent package (e.g., `src.input.webhooks`) — otherwise `from pkg import submod` retrieves the old module object from the package's attribute cache, bypassing the freshly-imported sys.modules entry and causing mock patches to miss.
- **anyio_backend fixture for asyncio-only tests**: Use `@pytest.fixture(params=["asyncio"]) def anyio_backend` to prevent anyio from parametrizing tests over trio when trio is not installed in the environment.
- **Connector test lazy import pattern**: Connectors importing config.settings must use lazy imports inside test functions (not module-level) with autouse fixture setting env vars + popping sys.modules — otherwise settings singleton triggers at collection time before any fixture runs.
- **Calendar singleEvents=True required**: Calendar API requires singleEvents=True when using orderBy="startTime" — hard API constraint.
- **Calendar datetime.now(timezone.utc)**: Use datetime.now(timezone.utc) not datetime.utcnow() for RFC3339-compliant ISO strings with timezone offset required by Calendar API.
- **test_main.py isolation pattern**: test_main.py requires same sys.modules.pop + env var setup as test_webhooks.py because import chain src.main -> src.input.webhooks -> src.input.pubsub -> config.settings triggers Settings() singleton at import time. Also requires anyio_backend fixture to restrict async tests to asyncio only.
- **Glossary chunk structure**: 5-section markdown maps 1:1 to pgvector chunks (one ## section per chunk) — seed script splits on ## headers.
- **Historical patterns retrieval design**: 3 aluminum-to-wood accepted precedents (EVT-001/010/012) support semantic search query "past aluminum to wood window change" — EVT-012 (12 units, structural review) is direct precedent for 3rd floor demo scenario.
- **Rules condition fields**: String-based conditions interpreted by LLM during enrichment, not executed programmatically — rules are advisory/routing, not a rule engine.
- **Seed script test lazy import pattern**: test_knowledge_folder.py uses Path.exists() for IMPL_AVAILABLE guard (avoids pydantic ValidationError at collection time) and lazy imports inside each test function — same as test_connectors.py pattern. try/except ImportError is insufficient when settings singleton raises ValidationError at import time.

### Architecture Principles

- All pipeline stage boundaries are validated with Pydantic v2.
- All secrets in .env, never hardcoded anywhere.
- YAML for all rules (knowledge_folder/rules/, config/event_types/).
- Structured JSON logs throughout.

### Known Constraints

- ACC API rate limits require caching of floor plan data — enrichment module must handle gracefully.
- Fireflies webhook must receive transcripts within 5 minutes of meeting end (per PRD acceptance criteria).
- Gmail and Calendar connectors use polling (not webhooks), which must be considered for latency budget.

### Open Questions (from PRD)

1. Email service: SendGrid vs. Gmail API — CLAUDE_PLAN.md specifies Gmail API.
2. PM tool integration: initially local DB tasks; Asana/Monday future.
3. Knowledge folder management: Git-based workflow for now.
4. Confidence threshold: Fixed at 80% for v1; configurability deferred.

---

## Session Continuity

### To Resume Work

1. Read this STATE.md to understand current position.
2. Read `.planning/ROADMAP.md` to find the current phase and its success criteria.
3. Read `CLAUDE_PLAN.md` for exact implementation steps for the current phase.
4. Begin implementing from the first incomplete item in the current phase.

### Files That Must Be Read at Session Start

- `.planning/STATE.md` (this file)
- `.planning/ROADMAP.md`
- `CLAUDE_PLAN.md`
- `PRD.md` (for acceptance criteria reference)

---

## Phase Completion Log

| Phase | Completed | Notes |
|-------|-----------|-------|
| Phase 0 | 2026-03-12 | Complete — 2 plans (scaffold + DB/LLM layer) |
| Phase 1 | 2026-03-13 | Complete — 5 plans (pubsub, fireflies/acc webhooks, Gmail/Calendar connectors, main.py wiring) — 26 unit tests passing |
| Phase 2 | 2026-03-13 | Complete — 3 plans (content files, DB schema + vector store, seed script) — 6 unit tests passing |
| Phase 3 | - | Not started |
| Phase 4 | - | Not started |
| Phase 5 | - | Not started |
| Phase 6 | - | Not started |
| Phase 7 | - | Not started |
| Phase 8 | - | Not started |
| Phase 9 | - | Not started |
