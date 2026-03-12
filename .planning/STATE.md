---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: unknown
last_updated: "2026-03-12T15:38:15.195Z"
progress:
  total_phases: 10
  completed_phases: 1
  total_plans: 2
  completed_plans: 2
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
| Current Phase | Phase 1: Input Layer |
| Current Plan | 01-01 (Phase 0 complete) |
| Status | In progress |
| Last Updated | 2026-03-12 |

### Progress Bar

```
Phase 0  [##########] 100% (2/2 plans complete)
Phase 1  [          ] 0%
Phase 2  [          ] 0%
Phase 3  [          ] 0%
Phase 4  [          ] 0%
Phase 5  [          ] 0%
Phase 6  [          ] 0%
Phase 7  [          ] 0%
Phase 8  [          ] 0%
Phase 9  [          ] 0%

Overall: 1/10 phases complete
```

---

## Performance Metrics

| Metric | Target | Current |
|--------|--------|---------|
| PM coordination time reduction | 80% | Not measured |
| High-confidence proposal accuracy | >90% | Not measured |
| Event-to-proposal latency | <5 min | Not measured |
| PM acceptance rate | 75% | Not measured |

---

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
| Phase 1 | - | Not started |
| Phase 2 | - | Not started |
| Phase 3 | - | Not started |
| Phase 4 | - | Not started |
| Phase 5 | - | Not started |
| Phase 6 | - | Not started |
| Phase 7 | - | Not started |
| Phase 8 | - | Not started |
| Phase 9 | - | Not started |
