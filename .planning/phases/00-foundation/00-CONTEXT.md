# Phase 0: Foundation — Context

**Gathered:** 2026-03-12
**Status:** Ready for planning
**Source:** PRD Express Path (CLAUDE_PLAN.md + PRD.md)

<domain>
## Phase Boundary

Phase 0 delivers all foundational infrastructure that every subsequent phase depends on:
- Python package setup (requirements.txt, pyproject.toml, .env.example)
- Shared database layer: PostgreSQL connection pool + pgvector operations
- Shared LLM clients: Claude Sonnet 4 + Haiku 4.5 wrappers, Voyage-3 embedding client
- All Pydantic v2 data models: RawEvent, NormalizedEvent, Proposal, Action, Signal, EventTypeConfig
- SQL schema + HNSW index migrations
- App settings/config loader

Nothing in Phase 0 calls external APIs at runtime — it only defines the contracts and clients.
</domain>

<decisions>
## Implementation Decisions

### Package Setup (FOUND-01)
- `requirements.txt` must list: anthropic, voyageai, psycopg2-binary, pgvector, pydantic>=2.0, fastapi, uvicorn, python-dotenv, langchain, langchain-anthropic, google-cloud-pubsub, google-auth, PyYAML, python-dateutil
- `pyproject.toml` must define project metadata and test config
- `.env.example` must list all required env vars: ANTHROPIC_API_KEY, VOYAGE_API_KEY, DATABASE_URL, GOOGLE_CLOUD_PROJECT, PUBSUB_TOPIC_RAW_EVENTS, ACC_CLIENT_ID, ACC_CLIENT_SECRET, FIREFLIES_API_KEY, GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET

### Database Layer (FOUND-02, FOUND-03)
- `src/shared/db/postgres.py`: async connection pool using psycopg2, query helpers (execute, fetch_one, fetch_all, execute_many)
- `src/shared/db/vector_store.py`: embed text via Voyage-3, store vectors in pgvector, cosine similarity search returning top-k results
- Vector dimension: 1024 (Voyage-3 output)
- Connection string from DATABASE_URL env var

### LLM Clients (FOUND-04, FOUND-05)
- `src/shared/llm/claude.py`: two client functions — `call_sonnet(prompt, system)` using `claude-sonnet-4-20250514` and `call_haiku(prompt, system)` using `claude-haiku-4-5-20251001`
- Both must support structured output (JSON mode) for pipeline use
- `src/shared/llm/voyage.py`: `embed_text(text)` and `embed_batch(texts)` using `voyage-3` model
- Use `anthropic` Python SDK, `voyageai` Python SDK — NO OpenAI

### Data Models (FOUND-06, FOUND-07, FOUND-08)
- `src/shared/models/events.py`:
  - `RawEvent`: event_id, source (fireflies|acc|gmail|calendar), raw_payload (dict), received_at
  - `NormalizedEvent`: event_id, source, event_type, material (original + new), location, quantity, people (list of name+role), deadlines (list), summary (str), extracted_at
- `src/shared/models/proposals.py`:
  - `Signal`: signal_type (str), priority (int), payload (dict), timestamp
  - `Action`: action_id, action_type (email|task|calendar|drawing), action_data (dict), status (pending|executed|failed), executed_at (optional)
  - `Proposal`: proposal_id, event_id, alert (dict), actions (list[Action]), confidence_score (float 0-1), recommendation (accept|review|reject), status (pending|accepted|rejected), created_at
- `src/shared/models/config.py`:
  - `EventTypeConfig`: event_type (str), rules_file (str), allowed_signals (list[str]), enrichment_queries (list[str]), time_analysis_enabled (bool)
- All models use Pydantic v2 with field validators where needed

### SQL Schema (FOUND-09)
Per PRD Section 6.3:
- `001_create_tables.sql`: events, proposals, actions, feedback, past_changes tables + enable pgvector extension + knowledge_chunks table (id, content, embedding vector(1024), source, metadata)
- `002_create_indexes.sql`: HNSW index on knowledge_chunks.embedding, HNSW index on past_changes embedding column (if added), standard B-tree indexes on FK columns and status columns

### Config Settings (FOUND-10)
- `config/settings.py`: Pydantic BaseSettings class loading all env vars with types and defaults
- Must fail fast if required vars (ANTHROPIC_API_KEY, VOYAGE_API_KEY, DATABASE_URL) are missing

### Claude's Discretion
- Error handling patterns (custom exceptions vs stdlib)
- Logging setup (use Python stdlib logging with JSON formatter)
- Async vs sync for DB pool (use sync psycopg2 for simplicity in Phase 0; FastAPI async wrappers can be added in Phase 7)
</decisions>

<specifics>
## Specific Requirements

- Model strings EXACTLY: `claude-sonnet-4-20250514`, `claude-haiku-4-5-20251001`, `voyage-3`
- Vector column type: `vector(1024)` (pgvector)
- Pydantic v2 — NOT v1 syntax
- All secrets in .env — never hardcoded
- No OpenAI, no spaCy, no model training
- PRD confidence score formula (to be embedded in models layer): data_clarity×0.30 + historical_match×0.25 + cost_acceptable×0.25 + no_red_flags×0.20
- Tables from PRD: events, proposals, actions, feedback, past_changes (+ knowledge_chunks for RAG)
</specifics>

<deferred>
## Deferred Ideas

- Cloud Run Dockerfile — Phase 7+
- Pub/Sub infrastructure setup (setup.sh) — Phase 1
- Async DB pool migration — Phase 7
- Multi-project scope isolation — v2
</deferred>

---

*Phase: 00-foundation*
*Context gathered: 2026-03-12 via PRD Express Path*
