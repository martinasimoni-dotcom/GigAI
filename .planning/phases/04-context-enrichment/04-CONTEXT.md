# Phase 4: Context Enrichment — Context

**Gathered:** 2026-03-13
**Status:** Ready for planning
**Source:** PRD Express Path (CLAUDE_PLAN.md)

<domain>
## Phase Boundary

Phase 4 delivers the two context-building steps of the SYSTEM pipeline:

1. **Context Enrichment** (CTX-01): Fetches floor plan and project data from the ACC API, then retrieves relevant knowledge chunks (supplier info, glossary, rules) via Voyage-3 + pgvector semantic search. Outputs an enriched event object with all context needed for domain processing.

2. **Historical Retrieval** (CTX-02): Performs semantic search on the pgvector `knowledge_chunks` table to find the top 5 past events most similar to the current event. Returns matches with outcome and success rate.

Also delivers:
- `src/system/context/__init__.py`
- Package is consumed by domain processing (Phase 5) and decision intelligence (Phase 6)
</domain>

<decisions>
## Implementation Decisions

### Context Enrichment Module (CTX-01)
- File: `src/system/context/enrichment.py`
- Function: `enrich_event(event: NormalizedEvent, project_id: str) -> EnrichedEvent`
- EnrichedEvent: Pydantic model containing the original NormalizedEvent plus:
  - `knowledge_chunks: list[dict]` — top knowledge chunks from pgvector (glossary, rules, supplier)
  - `acc_floor_plan: dict` — floor plan data from ACC API (stub for now — return mock data if ACC not configured)
  - `supplier_info: dict | None` — supplier/pricing info retrieved from knowledge folder
  - `relevant_rules: list[str]` — rule chunk texts retrieved from semantic search
- Uses `src/shared/db/vector_store.py` `search()` for retrieval (input_type="query")
- Uses `src/shared/config/settings.py` for ACC credentials
- ACC API: call real endpoint if `ACC_TOKEN` is set; otherwise return a plausible stub (unit IDs W-301 through W-312 for demo 3rd floor scenario)
- Must retrieve: supplier info for the new material, relevant rules, glossary terms for location and material
- Search queries: derive from event fields (e.g., query = `f"{event.material_new} supplier pricing"`, `f"{event.location} floor plan units"`)
- top_k = 5 for each search query

### Historical Retrieval Module (CTX-02)
- File: `src/system/context/historical.py`
- Function: `retrieve_historical(event: NormalizedEvent, top_k: int = 5) -> list[HistoricalMatch]`
- HistoricalMatch: Pydantic model with `content: str`, `source: str`, `metadata: dict`, `similarity: float`, `outcome: str | None`, `success_rate: float | None`
- Uses `src/shared/db/vector_store.py` `search()` with a query derived from the event summary and material fields
- Extracts `outcome` and `success_rate` from the chunk's metadata if present
- Returns top 5 matches sorted by similarity (descending)
- Query construction: `f"{event.change_type} {event.material_original} to {event.material_new} {event.location}"`

### EnrichedEvent Model
- File: inline in `enrichment.py` OR in `src/shared/models/events.py` — prefer inline in enrichment.py to keep models close to their consumers
- Inherits from / contains NormalizedEvent
- Pydantic v2

### Package Structure
- `src/system/context/__init__.py` — must exist

### Settings
- No new settings needed for Phase 4 (uses existing `DATABASE_URL`, `VOYAGE_API_KEY`, ACC settings)

### Claude's Discretion
- Exact query strings for pgvector search
- How to stub ACC floor plan data (return a realistic-looking dict with unit IDs)
- Whether EnrichedEvent contains NormalizedEvent by composition or inheritance
- Logging format for retrieved chunks
- Whether to run multiple search queries in parallel or sequentially

</decisions>

<specifics>
## Specific Requirements

- Demo scenario: aluminum → wood window substitution, 3rd Floor (Units W-301 to W-312), 12 units
- `search()` function in `src/shared/db/vector_store.py` signature: check actual file before calling
- Voyage-3 model: `voyage-3`, 1024-dim — already implemented in `src/shared/llm/voyage.py`
- pgvector table: `knowledge_chunks` (id, content text, embedding vector(1024), source text, metadata jsonb)
- No OpenAI, no spaCy, Pydantic v2 for all models
- All secrets in .env
- CTX-01 success: given "third floor windows" event → returns W-301 to W-312 unit IDs from mock ACC data
- CTX-02 success: returns at least 3 historical matches with outcome/success_rate for demo scenario

</specifics>

<deferred>
## Deferred Ideas

- Real ACC API integration for floor plans (live token) — Phase 4+ / when ACC token available
- Async pgvector search — Phase 7
- Multi-project knowledge isolation — v2
- Cache enrichment results per event ID — v2
</deferred>

---

*Phase: 04-context-enrichment*
*Context gathered: 2026-03-13 via PRD Express Path*
