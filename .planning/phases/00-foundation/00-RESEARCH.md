# Phase 0: Foundation - Research

**Researched:** 2026-03-12
**Domain:** Python infrastructure — PostgreSQL/pgvector, Anthropic SDK, Voyage AI SDK, Pydantic v2
**Confidence:** HIGH (all major findings verified against official documentation)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Package Setup (FOUND-01)**
- `requirements.txt` must list: anthropic, voyageai, psycopg2-binary, pgvector, pydantic>=2.0, fastapi, uvicorn, python-dotenv, langchain, langchain-anthropic, google-cloud-pubsub, google-auth, PyYAML, python-dateutil
- `pyproject.toml` must define project metadata and test config
- `.env.example` must list all required env vars: ANTHROPIC_API_KEY, VOYAGE_API_KEY, DATABASE_URL, GOOGLE_CLOUD_PROJECT, PUBSUB_TOPIC_RAW_EVENTS, ACC_CLIENT_ID, ACC_CLIENT_SECRET, FIREFLIES_API_KEY, GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET

**Database Layer (FOUND-02, FOUND-03)**
- `src/shared/db/postgres.py`: sync connection pool using psycopg2, query helpers (execute, fetch_one, fetch_all, execute_many)
- `src/shared/db/vector_store.py`: embed text via Voyage-3, store vectors in pgvector, cosine similarity search returning top-k results
- Vector dimension: 1024 (Voyage-3 output)
- Connection string from DATABASE_URL env var

**LLM Clients (FOUND-04, FOUND-05)**
- `src/shared/llm/claude.py`: two client functions — `call_sonnet(prompt, system)` using `claude-sonnet-4-20250514` and `call_haiku(prompt, system)` using `claude-haiku-4-5-20251001`
- Both must support structured output (JSON mode) for pipeline use
- `src/shared/llm/voyage.py`: `embed_text(text)` and `embed_batch(texts)` using `voyage-3` model
- Use `anthropic` Python SDK, `voyageai` Python SDK — NO OpenAI

**Data Models (FOUND-06, FOUND-07, FOUND-08)**
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

**SQL Schema (FOUND-09)**
- `001_create_tables.sql`: events, proposals, actions, feedback, past_changes tables + enable pgvector extension + knowledge_chunks table (id, content, embedding vector(1024), source, metadata)
- `002_create_indexes.sql`: HNSW index on knowledge_chunks.embedding, HNSW index on past_changes embedding column (if added), standard B-tree indexes on FK columns and status columns

**Config Settings (FOUND-10)**
- `config/settings.py`: Pydantic BaseSettings class loading all env vars with types and defaults
- Must fail fast if required vars (ANTHROPIC_API_KEY, VOYAGE_API_KEY, DATABASE_URL) are missing

**Exact model strings**
- `claude-sonnet-4-20250514`
- `claude-haiku-4-5-20251001`
- `voyage-3`
- Vector column: `vector(1024)`

### Claude's Discretion
- Error handling patterns (custom exceptions vs stdlib)
- Logging setup (use Python stdlib logging with JSON formatter)
- Async vs sync for DB pool (use sync psycopg2 for simplicity in Phase 0; FastAPI async wrappers deferred to Phase 7)

### Deferred Ideas (OUT OF SCOPE)
- Cloud Run Dockerfile — Phase 7+
- Pub/Sub infrastructure setup (setup.sh) — Phase 1
- Async DB pool migration — Phase 7
- Multi-project scope isolation — v2
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FOUND-01 | Python project scaffold: requirements.txt, pyproject.toml, .env.example | Scaffold already exists on disk; needs version updates and OpenAI removal |
| FOUND-02 | PostgreSQL connection pool with query helpers (postgres.py) | psycopg2 ThreadedConnectionPool pattern documented; register_vector must be called per-connection via configure callback |
| FOUND-03 | pgvector integration: embed + retrieve operations (vector_store.py) | pgvector Python package patterns, cosine similarity query syntax, HNSW index SQL confirmed |
| FOUND-04 | Claude Sonnet 4 and Haiku 4.5 client wrappers (claude.py) | Both model strings confirmed valid; structured output via output_config parameter confirmed; system prompt parameter confirmed |
| FOUND-05 | Voyage-3 embedding client (voyage.py) | voyageai.Client().embed() with model="voyage-3" confirmed; returns EmbeddingsObject with .embeddings list |
| FOUND-06 | Pydantic v2 models: RawEvent, NormalizedEvent (events.py) | ConfigDict, field_validator, model_validator patterns confirmed for Pydantic v2 |
| FOUND-07 | Pydantic v2 models: Proposal, Action, Signal (proposals.py) | Literal types, Optional fields, nested model patterns confirmed |
| FOUND-08 | Pydantic v2 model: EventTypeConfig (config.py) | BaseModel with list fields and bool fields confirmed |
| FOUND-09 | SQL migration files: 001_create_tables.sql, 002_create_indexes.sql (HNSW) | CREATE INDEX USING hnsw with vector_cosine_ops, m=16, ef_construction=64 syntax confirmed |
| FOUND-10 | App settings loader from environment variables (settings.py) | pydantic-settings BaseSettings with SettingsConfigDict confirmed; fail-fast on missing required fields confirmed |
</phase_requirements>

---

## Summary

Phase 0 establishes every contract that downstream phases depend on. Nothing in this phase calls external APIs at runtime — it only defines clients, models, schema, and configuration infrastructure. Because `pyproject.toml` and `requirements.txt` already exist on disk (from a prior scaffolding step), the planner should treat them as requiring update/verification rather than creation from scratch.

The five most critical technical areas are: (1) psycopg2 + pgvector integration requires `register_vector` to be called on each pooled connection, not globally once; (2) structured output from Claude is now generally available via the `output_config` parameter — no beta headers needed; (3) `claude-sonnet-4-20250514` is a legacy snapshot that remains valid but is no longer the latest Sonnet; (4) Voyage-3's `embed()` returns an `EmbeddingsObject`, not a raw list; and (5) Pydantic v2 `BaseSettings` requires the separate `pydantic-settings` package.

**Primary recommendation:** Follow the implementation order exactly as given in CLAUDE_PLAN.md Phase 0 steps 1-10. Each step depends on the previous — models cannot be tested without settings, vector_store cannot be tested without postgres, etc.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| anthropic | >=0.18.1 (0.18.1 in existing requirements) | Claude API client | Official Anthropic SDK; only supported path to claude-sonnet-4-20250514 and claude-haiku-4-5-20251001 |
| voyageai | >=0.2.1 | Voyage-3 embedding client | Official Voyage AI Python SDK; required by project constraint |
| psycopg2-binary | >=2.9.9 | PostgreSQL sync adapter | Synchronous DB as decided; binary wheels avoid libpq build |
| pgvector | >=0.2.4 | pgvector type registration + numpy integration | Provides register_vector() and numpy array ↔ vector(N) conversion |
| pydantic | >=2.6.0 | Data models and validation | v2 is locked; v1 syntax will fail |
| pydantic-settings | >=2.1.0 | BaseSettings from env vars | Moved out of core pydantic in v2; separate install required |
| python-dotenv | >=1.0.0 | Load .env files | Populates os.environ before settings load |
| PyYAML | >=6.0.1 | Parse event_type configs and rules | Required for config/event_types/*.yaml in later phases |
| python-dateutil | >=2.8.2 | Date parsing in models | Required for temporal fields in NormalizedEvent |
| tenacity | >=8.2.3 | Retry logic | Used in LLM client wrappers for 3-attempt exponential backoff |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | >=1.26.3 | Vector array representation | pgvector Python client converts numpy arrays to vector type |
| structlog / python-json-logger | >=24.1.0 / >=2.0.7 | Structured JSON logging | Either works; pick one and apply consistently |
| python-jose | >=3.3.0 | JWT (Phase 7 middleware) | Declared in pyproject.toml; not used in Phase 0 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| psycopg2 sync | asyncpg | asyncpg is faster but requires async FastAPI wrappers; deferred to Phase 7 per decision |
| ThreadedConnectionPool | psycopg2-pool third-party | Third-party pool adds dependency; stdlib pool sufficient for Phase 0 |
| voyageai direct | LangChain VoyageAI wrapper | LangChain adds abstraction cost; direct SDK is simpler and is the locked decision |

**Installation (minimal Phase 0 set):**
```bash
pip install anthropic voyageai psycopg2-binary pgvector pydantic>=2.0 pydantic-settings python-dotenv PyYAML python-dateutil tenacity numpy
```

---

## Architecture Patterns

### Recommended Project Structure (Phase 0 files only)
```
gigai/
├── requirements.txt              # Update: remove openai, pin correct versions
├── pyproject.toml                # Update: Python >=3.11, bump anthropic version
├── .env.example                  # List all 10 required env vars
├── config/
│   └── settings.py               # FOUND-10: BaseSettings subclass
├── src/
│   └── shared/
│       ├── db/
│       │   ├── postgres.py       # FOUND-02: ThreadedConnectionPool + query helpers
│       │   └── vector_store.py   # FOUND-03: embed + cosine search
│       ├── llm/
│       │   ├── claude.py         # FOUND-04: call_sonnet + call_haiku
│       │   └── voyage.py         # FOUND-05: embed_text + embed_batch
│       └── models/
│           ├── events.py         # FOUND-06: RawEvent, NormalizedEvent
│           ├── proposals.py      # FOUND-07: Proposal, Action, Signal
│           └── config.py         # FOUND-08: EventTypeConfig
└── infra/
    └── sql/
        ├── 001_create_tables.sql # FOUND-09
        └── 002_create_indexes.sql # FOUND-09
```

### Pattern 1: psycopg2 ThreadedConnectionPool with register_vector per-connection

**What:** Create a module-level pool at startup; call `register_vector` on every connection when the pool creates it, not just once globally.

**When to use:** Every db operation in the sync codebase.

**Critical gotcha:** `register_vector` must be invoked on each individual connection object. With a connection pool, you cannot call it once on a single connection and expect it to apply to others in the pool. The recommended pattern calls it inside a connection factory or wrapper.

```python
# Source: pgvector-python GitHub issue #100 (maintainer recommendation)
import psycopg2
import psycopg2.pool
from pgvector.psycopg2 import register_vector

_pool: psycopg2.pool.ThreadedConnectionPool | None = None

def get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=settings.database_url,
        )
    return _pool

def get_connection():
    conn = get_pool().getconn()
    register_vector(conn)   # must call on each connection from pool
    return conn

def release_connection(conn):
    get_pool().putconn(conn)
```

### Pattern 2: pgvector cosine similarity search

**What:** Embed a query with Voyage-3, then use the `<=>` cosine distance operator to find top-k neighbours.

**When to use:** `vector_store.py` `search(query_text, top_k)` method.

```python
# Source: pgvector-python README + pgvector GitHub (confirmed)
# After register_vector(conn):
cur.execute(
    """
    SELECT id, content, source, metadata,
           1 - (embedding <=> %s::vector) AS similarity
    FROM knowledge_chunks
    ORDER BY embedding <=> %s::vector
    LIMIT %s
    """,
    (embedding, embedding, top_k)
)
```

Note: Pass the embedding as a Python list or numpy array; pgvector's register_vector teaches psycopg2 how to adapt it.

### Pattern 3: Anthropic SDK — messages.create with system prompt

**What:** Standard messages call with a system prompt; add `output_config` for guaranteed JSON output.

**When to use:** Both `call_sonnet` and `call_haiku` wrappers.

```python
# Source: Anthropic official docs (platform.claude.com/docs/en/build-with-claude/structured-outputs)
import anthropic

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

def call_sonnet(prompt: str, system: str, output_schema: dict | None = None) -> str:
    kwargs = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 8192,
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
    }
    if output_schema:
        kwargs["output_config"] = {
            "format": {
                "type": "json_schema",
                "schema": output_schema,
            }
        }
    response = client.messages.create(**kwargs)
    return response.content[0].text
```

**Note on structured outputs:** As of 2025-11-13, structured outputs are GA on `claude-sonnet-4-20250514`, `claude-haiku-4-5-20251001`, and newer models. No beta header is required — use `output_config` parameter directly. The output is in `response.content[0].text` as a JSON string.

**Alternative simpler JSON approach:** For cases where a full JSON schema is not needed, instruct the model in the system prompt to "respond ONLY with valid JSON" and parse `response.content[0].text`. This is lower overhead and works well for Haiku normalisation calls.

### Pattern 4: Voyage AI embed()

**What:** Call `voyageai.Client().embed()` with `model="voyage-3"` and specify `input_type`.

**When to use:** All embedding operations.

```python
# Source: Voyage AI official docs (docs.voyageai.com/docs/embeddings)
import voyageai

_client = voyageai.Client()  # reads VOYAGE_API_KEY from env

def embed_text(text: str) -> list[float]:
    result = _client.embed(
        texts=[text],
        model="voyage-3",
        input_type="query",   # use "query" for search queries
    )
    return result.embeddings[0]

def embed_batch(texts: list[str]) -> list[list[float]]:
    result = _client.embed(
        texts=texts,
        model="voyage-3",
        input_type="document",  # use "document" for knowledge chunks
    )
    return result.embeddings
```

**Return type:** `result.embeddings` is `list[list[float]]` — a list of 1024-float vectors for voyage-3. `result.total_tokens` gives token count for monitoring.

**input_type distinction:** Use `"document"` when storing knowledge chunks, `"query"` when embedding a search query. This asymmetry improves retrieval quality.

### Pattern 5: Pydantic v2 models

**What:** Use `ConfigDict`, `field_validator`, `model_validator` from `pydantic` (v2 API — NOT the deprecated v1 `@validator`).

```python
# Source: Pydantic v2 official docs (docs.pydantic.dev/latest)
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

class RawEvent(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    event_id: str
    source: Literal["fireflies", "acc", "gmail", "calendar"]
    raw_payload: dict
    received_at: datetime = Field(default_factory=datetime.utcnow)

class NormalizedEvent(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    event_id: str
    source: Literal["fireflies", "acc", "gmail", "calendar"]
    event_type: str
    material_original: Optional[str] = None
    material_new: Optional[str] = None
    location: Optional[str] = None
    quantity: Optional[int] = None
    people: list[dict] = Field(default_factory=list)  # [{name, role}]
    deadlines: list[datetime] = Field(default_factory=list)
    summary: str
    extracted_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("summary")
    @classmethod
    def summary_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("summary must not be empty")
        return v
```

### Pattern 6: Pydantic v2 BaseSettings

**What:** `config/settings.py` loads all env vars. Required fields (no default) cause an immediate `ValidationError` at startup if missing.

```python
# Source: pydantic-settings official docs (docs.pydantic.dev/latest/concepts/pydantic_settings/)
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Required — no default → fails fast if missing
    anthropic_api_key: str
    voyage_api_key: str
    database_url: str

    # Optional with defaults
    google_cloud_project: str = ""
    pubsub_topic_raw_events: str = "raw-events"
    acc_client_id: str = ""
    acc_client_secret: str = ""
    fireflies_api_key: str = ""
    gmail_client_id: str = ""
    gmail_client_secret: str = ""

settings = Settings()  # instantiate once at module level → fail fast
```

### Anti-Patterns to Avoid

- **Calling `register_vector` once globally:** It must be called per-connection. With a pool, call it every time you get a connection. Forgetting this causes `psycopg2.ProgrammingError` when inserting/querying vectors.
- **Using Pydantic v1 `@validator`:** Replaced by `@field_validator` in v2. Using v1 syntax with Pydantic 2.x raises `PydanticUserError` with an inscrutable message.
- **Using `BaseSettings` from `pydantic` directly:** In Pydantic v2, `BaseSettings` was removed from the core package. Import from `pydantic_settings` instead.
- **Hardcoding model strings as variables that are "easy to change":** The model strings `claude-sonnet-4-20250514` and `claude-haiku-4-5-20251001` are snapshot identifiers. Define them as module-level constants, not function arguments with defaults.
- **Passing embeddings as plain Python lists without register_vector:** Without `register_vector`, psycopg2 does not know how to adapt a Python list to the PostgreSQL `vector` type. The insert will fail or send the wrong type.
- **Storing embeddings before enabling pgvector extension:** `CREATE EXTENSION IF NOT EXISTS vector` must be the first statement in `001_create_tables.sql`.
- **Using `openai` package anywhere:** The existing `requirements.txt` (line 25) includes `openai==1.12.0`. This MUST be removed per project constraints.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retry logic with exponential backoff | Custom while/sleep retry | `tenacity.retry` with `wait_exponential` | Handles jitter, max attempts, specific exception types |
| JSON schema validation from Pydantic model | Manual schema dict | `model.model_json_schema()` | Pydantic v2 generates the exact JSON Schema dict needed for `output_config` |
| Connection pool management | Custom list of connections | `psycopg2.pool.ThreadedConnectionPool` | Handles thread safety, min/max connections, timeout |
| Environment variable type coercion | `os.getenv()` + manual casting | Pydantic BaseSettings | Handles str→int, str→bool, missing required vars, .env loading |
| Vector similarity search | Custom Python distance calculation | pgvector `<=>` operator | Runs in PostgreSQL, uses HNSW index, orders of magnitude faster at scale |

**Key insight:** Every "simple utility" in this list hides significant edge cases. Tenacity alone handles 15+ failure modes that a naive retry loop misses.

---

## Common Pitfalls

### Pitfall 1: register_vector Not Called Per-Connection
**What goes wrong:** Vector INSERT and SELECT queries fail with `psycopg2.ProgrammingError: can't adapt type 'list'` or return wrong data types.
**Why it happens:** `register_vector` registers a psycopg2 type adapter on a specific connection object. Pool connections are separate objects.
**How to avoid:** Call `register_vector(conn)` immediately after `pool.getconn()`. Consider a context manager that wraps getconn/putconn and always registers.
**Warning signs:** Works in a single-connection test script, fails when using the pool.

### Pitfall 2: pgvector Extension Not Enabled Before Schema Creation
**What goes wrong:** `001_create_tables.sql` fails with `ERROR: type "vector" does not exist`.
**Why it happens:** pgvector extension must be installed on the PostgreSQL server AND enabled per database before any `vector(N)` column type can be used.
**How to avoid:** First line of `001_create_tables.sql` must be `CREATE EXTENSION IF NOT EXISTS vector;`.
**Warning signs:** Runs fine on a dev machine with pgvector installed, fails on a fresh database.

### Pitfall 3: Pydantic v1 vs v2 Syntax Mixing
**What goes wrong:** `PydanticUserError: `@validator` is no longer supported` or silent behavioural differences.
**Why it happens:** The project requires Pydantic >=2.0 but if any `@validator` (v1 syntax) appears, it raises an error. If pydantic<2.0 is accidentally installed, it silently uses different validation semantics.
**How to avoid:** Use exclusively v2 API: `@field_validator`, `@model_validator`, `ConfigDict`, `model_config`. Pin `pydantic>=2.6.0` in requirements.txt.
**Warning signs:** `from pydantic import validator` import succeeds but raises deprecation warnings.

### Pitfall 4: voyageai.Client() Returns EmbeddingsObject, Not List
**What goes wrong:** `TypeError: float object is not subscriptable` when code treats `result` as a list.
**Why it happens:** `client.embed()` returns an `EmbeddingsObject` with a `.embeddings` attribute, not a bare list.
**How to avoid:** Always access `result.embeddings[0]` for single text, `result.embeddings` for batch. Never use `result[0]`.
**Warning signs:** Works after adding `.embeddings` but forgot for one call path.

### Pitfall 5: HNSW Index Build Timing (Not a Blocker for Phase 0)
**What goes wrong:** Performance degradation if HNSW index is built before any data is loaded.
**Why it happens:** HNSW indexes build incrementally as data is inserted (unlike IVFFlat which requires pre-loaded data to build well). Building on an empty table is fine — the index grows as rows are added.
**How to avoid:** For Phase 0, create the HNSW index in `002_create_indexes.sql` as specified. No special ordering needed.
**Warning signs:** This is a non-issue for HNSW; it would only matter if IVFFlat were used instead.

### Pitfall 6: Existing requirements.txt Contains openai
**What goes wrong:** `openai` package in the existing `requirements.txt` (line 25) violates the hard constraint "No OpenAI anywhere."
**Why it happens:** Scaffolding was generated before the constraint was enforced.
**How to avoid:** Remove `openai==1.12.0` from `requirements.txt` and from `pyproject.toml` dependencies (it is not currently in pyproject.toml dependencies, only in requirements.txt).
**Warning signs:** Any `import openai` in the codebase.

### Pitfall 7: claude-sonnet-4-20250514 Is a Legacy Snapshot
**What goes wrong:** No runtime error — the model still works. But awareness is needed.
**Why it happens:** The project locked to `claude-sonnet-4-20250514` as the snapshot identifier. Per Anthropic's model page (March 2026), this is now listed under "Legacy models" alongside the newer `claude-sonnet-4-6`.
**How to avoid:** Use the exact model string `claude-sonnet-4-20250514` as required by CONTEXT.md. Do not "upgrade" to `claude-sonnet-4-6` without explicit decision from the user. The snapshot string guarantees consistent behaviour.
**Warning signs:** None at runtime — it just means you are not on the newest model.

---

## Code Examples

Verified patterns from official sources:

### HNSW Index Creation SQL
```sql
-- Source: pgvector GitHub (github.com/pgvector/pgvector), confirmed 2026-03
-- Enable extension first (must be before any vector column)
CREATE EXTENSION IF NOT EXISTS vector;

-- HNSW index for cosine similarity on 1024-dim vectors
-- m=16 (default, good balance), ef_construction=64 (default, good recall)
CREATE INDEX knowledge_chunks_embedding_hnsw_idx
    ON knowledge_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

### Full tables schema (001_create_tables.sql skeleton)
```sql
-- Source: PRD Section 6.3 + CONTEXT.md FOUND-09 decisions
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS events (
    event_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type  TEXT NOT NULL,
    source      TEXT NOT NULL,
    raw_data    JSONB,
    normalized_data JSONB,
    enriched_data   JSONB,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS proposals (
    proposal_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id        UUID REFERENCES events(event_id),
    alert           JSONB NOT NULL,
    actions         JSONB NOT NULL,
    confidence_score FLOAT NOT NULL CHECK (confidence_score BETWEEN 0 AND 1),
    status          TEXT NOT NULL DEFAULT 'pending',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS actions (
    action_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id UUID REFERENCES proposals(proposal_id),
    action_type TEXT NOT NULL,
    action_data JSONB NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',
    executed_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS feedback (
    feedback_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id         UUID REFERENCES proposals(proposal_id),
    decision            TEXT NOT NULL,
    rejection_reason    TEXT,
    confidence_at_decision FLOAT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS past_changes (
    change_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    change_type     TEXT NOT NULL,
    material_from   TEXT,
    material_to     TEXT,
    location        TEXT,
    cost            FLOAT,
    outcome         TEXT,
    confidence      FLOAT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content     TEXT NOT NULL,
    embedding   vector(1024) NOT NULL,
    source      TEXT NOT NULL,
    metadata    JSONB DEFAULT '{}'
);
```

### Confidence score formula (embed in models layer)
```python
# Source: PRD Section 4.5 + CONTEXT.md specifics
def calculate_confidence(
    data_clarity: float,        # 0.0 - 1.0: all required fields present and clear
    historical_match: float,    # 0.0 - 1.0: similar past changes exist and succeeded
    cost_acceptable: float,     # 0.0 - 1.0: cost within threshold (1.0 if < $50K)
    no_red_flags: float,        # 0.0 - 1.0: no structural/safety/regulatory concerns
) -> float:
    score = (
        data_clarity * 0.30
        + historical_match * 0.25
        + cost_acceptable * 0.25
        + no_red_flags * 0.20
    )
    return round(min(max(score, 0.0), 1.0), 4)
```

### Pydantic v2 Proposal model with Literal status
```python
# Source: Pydantic v2 official docs
from datetime import datetime
from typing import Literal, Optional
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field

class Action(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    action_id: str = Field(default_factory=lambda: str(uuid4()))
    action_type: Literal["email", "task", "calendar", "drawing"]
    action_data: dict
    status: Literal["pending", "executed", "failed"] = "pending"
    executed_at: Optional[datetime] = None

class Proposal(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    proposal_id: str = Field(default_factory=lambda: str(uuid4()))
    event_id: str
    alert: dict
    actions: list[Action] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0)
    recommendation: Literal["accept", "review", "reject"]
    status: Literal["pending", "accepted", "rejected"] = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@validator` in Pydantic | `@field_validator` + `@model_validator` | Pydantic v2.0 (2023) | Old syntax raises error in v2; never use for new code |
| `BaseSettings` from `pydantic` | `BaseSettings` from `pydantic_settings` | Pydantic v2.0 (2023) | Separate package install required |
| `beta` header for structured outputs | `output_config` parameter in messages.create | Nov 2025 (GA) | No beta header needed; output_config is stable API |
| `@validator(pre=True)` pattern | `@field_validator(mode='before')` | Pydantic v2.0 (2023) | Different decorator signature entirely |
| IVFFlat for vector indexes | HNSW preferred for query performance | pgvector 0.5.0+ | HNSW does not require pre-loaded data; better recall/speed tradeoff |
| `from pgvector.psycopg2 import register_vector` called once | Called per-connection (especially with pools) | pgvector-python maintainer guidance | Pool connections are separate objects; registration does not propagate |

**Deprecated/outdated in the existing scaffold:**
- `openai==1.12.0` in requirements.txt: MUST be removed (project constraint violation)
- `asyncpg==0.29.0` in requirements.txt: keep for future Phase 7 but unused in Phase 0
- `anthropic>=0.18.1` in requirements.txt: still valid, but structured output (`output_config`) requires a newer version — confirm version supports `output_config` before implementing FOUND-04

---

## Open Questions

1. **anthropic SDK version required for output_config**
   - What we know: Structured outputs GA'd November 2025; `output_config` is the stable parameter
   - What's unclear: The pinned version `anthropic==0.18.1` in requirements.txt predates November 2025. The minimum SDK version that supports `output_config` is not confirmed from the sources reviewed.
   - Recommendation: During implementation of FOUND-04, test `output_config` with the installed version. If it raises `TypeError: unexpected keyword argument`, update the pin to `anthropic>=0.40.0` (or whatever current is). Fallback: use system prompt JSON instruction instead of `output_config` — it works with any SDK version.

2. **voyageai SDK version required for current API**
   - What we know: `voyageai==0.2.1` is pinned; the Voyage AI Python library is at the `voyageai-python` GitHub repo
   - What's unclear: Whether 0.2.1 supports `voyage-3` and the current `embed()` signature shown in the docs
   - Recommendation: During FOUND-05 implementation, verify `voyageai.Client().embed(texts=["test"], model="voyage-3")` works. If the Client() interface is different (some older versions used `voyageai.get_embedding()`), update the pin.

3. **PostgreSQL version and pgvector extension availability**
   - What we know: Target is PostgreSQL 15; pgvector HNSW was added in pgvector 0.5.0
   - What's unclear: Whether the dev environment has pgvector installed on the PostgreSQL server
   - Recommendation: Add `SELECT extversion FROM pg_extension WHERE extname = 'vector';` as a health check. If it returns nothing, `CREATE EXTENSION vector` will fail. Document in README that pgvector must be installed on the server before running migrations.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | `pyproject.toml` — `[tool.pytest.ini_options]` already configured |
| Quick run command | `pytest tests/unit/ -x -q` |
| Full suite command | `pytest tests/ --cov=src --cov-report=term-missing` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FOUND-01 | requirements.txt lists all required packages, no openai | unit (file check) | `pytest tests/unit/test_scaffold.py -x` | Wave 0 |
| FOUND-02 | postgres.py get_connection() returns valid conn; execute/fetch helpers work | unit (mock pool) | `pytest tests/unit/test_postgres.py -x` | Wave 0 |
| FOUND-03 | vector_store.py embed_and_store + search returns top-k results | unit (mock embed + mock DB) | `pytest tests/unit/test_vector_store.py -x` | Wave 0 |
| FOUND-04 | call_sonnet and call_haiku return string responses | unit (mock anthropic client) | `pytest tests/unit/test_claude.py -x` | Wave 0 |
| FOUND-05 | embed_text returns list[float] of length 1024; embed_batch returns correct count | unit (mock voyageai client) | `pytest tests/unit/test_voyage.py -x` | Wave 0 |
| FOUND-06 | RawEvent and NormalizedEvent instantiate with valid data; reject invalid source | unit (model instantiation) | `pytest tests/unit/test_models_events.py -x` | Wave 0 |
| FOUND-07 | Proposal, Action, Signal instantiate; confidence_score 0-1 enforced | unit (model instantiation) | `pytest tests/unit/test_models_proposals.py -x` | Wave 0 |
| FOUND-08 | EventTypeConfig instantiates; list fields default to empty list | unit (model instantiation) | `pytest tests/unit/test_models_config.py -x` | Wave 0 |
| FOUND-09 | SQL files parseable; HNSW index SQL contains vector_cosine_ops | unit (file parse/string check) | `pytest tests/unit/test_sql_migrations.py -x` | Wave 0 |
| FOUND-10 | Settings raises ValidationError if ANTHROPIC_API_KEY missing; loads from .env | unit (mock env) | `pytest tests/unit/test_settings.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/unit/ -x -q --no-cov`
- **Per wave merge:** `pytest tests/unit/ --cov=src --cov-report=term-missing`
- **Phase gate:** Full unit suite green before moving to Phase 1

### Wave 0 Gaps
All test files are missing. The `tests/` directory exists but is empty. Required before implementation begins:

- [ ] `tests/conftest.py` — shared fixtures: mock anthropic client, mock voyageai client, mock psycopg2 pool, test .env values
- [ ] `tests/unit/test_scaffold.py` — validates FOUND-01: checks requirements.txt contents, no openai, all required packages present
- [ ] `tests/unit/test_postgres.py` — validates FOUND-02: uses mock psycopg2, tests execute/fetch_one/fetch_all/execute_many
- [ ] `tests/unit/test_vector_store.py` — validates FOUND-03: mocks embed_batch + mock DB cursor, tests store + search
- [ ] `tests/unit/test_claude.py` — validates FOUND-04: mocks anthropic.Anthropic(), tests call_sonnet and call_haiku return str
- [ ] `tests/unit/test_voyage.py` — validates FOUND-05: mocks voyageai.Client(), tests embed_text returns list[float] len 1024
- [ ] `tests/unit/test_models_events.py` — validates FOUND-06: Pydantic model instantiation, field validation, invalid source rejection
- [ ] `tests/unit/test_models_proposals.py` — validates FOUND-07: confidence_score bounds, status literals, Action nesting
- [ ] `tests/unit/test_models_config.py` — validates FOUND-08: EventTypeConfig default values
- [ ] `tests/unit/test_sql_migrations.py` — validates FOUND-09: SQL files exist, parseable, contain expected DDL
- [ ] `tests/unit/test_settings.py` — validates FOUND-10: missing required env var raises pydantic ValidationError

**Framework already configured:** `pyproject.toml` has full pytest, coverage, and marker config. No Wave 0 framework install needed.

---

## Sources

### Primary (HIGH confidence)
- Anthropic official model docs (platform.claude.com/docs/en/about-claude/models/overview) — confirmed both model strings, confirmed they are valid (claude-sonnet-4-20250514 listed as legacy; claude-haiku-4-5-20251001 listed as current)
- Anthropic structured outputs docs (platform.claude.com/docs/en/build-with-claude/structured-outputs) — confirmed output_config parameter, GA status, supported models
- Voyage AI embeddings docs (docs.voyageai.com/docs/embeddings) — confirmed embed() signature, EmbeddingsObject return type, voyage-3 specs (1024 dims, 32K context)
- Pydantic v2 settings docs (docs.pydantic.dev/latest/concepts/pydantic_settings/) — confirmed pydantic-settings package, SettingsConfigDict, fail-fast on missing required fields
- pgvector-python GitHub issue #100 — maintainer recommendation for register_vector with connection pools

### Secondary (MEDIUM confidence)
- pgvector GitHub (github.com/pgvector/pgvector) + Crunchy Data blog — HNSW index syntax, m=16 ef_construction=64 defaults, vector_cosine_ops operator
- psycopg2 official docs (psycopg.org/docs/pool.html) — ThreadedConnectionPool API
- pgvector PyPI + pgvector-python README — psycopg2 integration patterns

### Tertiary (LOW confidence)
- Inworld.ai and TypingMind model pages — cited as secondary confirmation for model string validity (verified against Anthropic official docs, upgraded to HIGH)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified against official docs or project's own existing scaffold
- Architecture: HIGH — patterns verified against official sources (anthropic docs, pgvector maintainer, pydantic docs)
- Pitfalls: HIGH for items 1-4 (verified via official docs/maintainer issues), MEDIUM for item 5 (inferred from pgvector docs), HIGH for item 6 (direct file inspection)
- SQL schema: HIGH — directly from PRD Section 6.3 + CONTEXT.md decisions

**Research date:** 2026-03-12
**Valid until:** 2026-04-12 (30 days — stack is stable; only risk is anthropic SDK version compatibility with output_config)

**Key finding not in CONTEXT.md:** The existing `requirements.txt` at the project root includes `openai==1.12.0` on line 25. This violates the hard constraint "No OpenAI anywhere." The planner must include a task to remove this line.

**Key finding on model status:** `claude-sonnet-4-20250514` is listed under "Legacy models" on the Anthropic docs page as of March 2026 (the newer snapshot is `claude-sonnet-4-6`). However, the model string remains valid and functional, and the project has explicitly locked to this string. Use it exactly as specified.
