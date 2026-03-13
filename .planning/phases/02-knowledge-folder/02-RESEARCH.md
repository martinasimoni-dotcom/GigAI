# Phase 2: Knowledge Folder — Research

**Researched:** 2026-03-13
**Domain:** Knowledge content authoring + pgvector seed pipeline
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Glossary File (KF-01)**
- File: `knowledge_folder/glossary/demo_project.md`
- Must cover: element types (windows, doors, walls, floors, ceilings), materials (aluminum, wood, glass, steel, concrete, gypsum board), locations (building floors 1-5, zones: north/south/east/west wing, specific areas: lobby, mechanical room, units 301-312)
- Demo building: 5-story mixed-use building, "Harbor View Tower", 312 units
- Format: Markdown with clear sections for element types, materials, locations, abbreviations

**Team Directory (KF-02)**
- File: `knowledge_folder/team_directory/demo_project.json`
- Must have 6-8 team members: Project Manager (Sarah Chen), Procurement Officer (Mike Torres), Lead Architect (James Park), Structural Engineer (Lisa Wong), Site Superintendent (Carlos Rivera), Supplier Contact (Jane Miller at AlumaCraft), Owner Representative (Robert Hayes)
- Each entry: name, role, email, phone, responsibilities (list), area_of_authority
- JSON format with array of team member objects

**Rules File (KF-03)**
- File: `knowledge_folder/rules/demo_project.yaml`
- Must have 15-20 rules covering: material change approval thresholds (<$5K = PM, $5K-$50K = PM + Owner, >$50K = immediate escalation), change order requirements (structural changes need architect sign-off), lead time rules (>10 window units = 6-week lead time), notification rules, schedule impact rules (critical path changes = owner notification within 24h), quality/substitution rules
- YAML format with rule_id, description, condition, action, stakeholders, priority fields

**Historical Patterns (KF-04)**
- File: `knowledge_folder/historical_patterns/demo_project.json`
- Must have 10-15 past material change events
- Each entry: event_id, date, material_original, material_new, location, quantity, reason, outcome, cost_impact, schedule_impact_days, pm_decision (accepted/rejected), lessons_learned
- Include variety: accepted (good outcome), rejected, cost overruns, schedule impacts
- Include at least 3 window-related changes to support the demo scenario

**Seed Script (KF-05)**
- File: `scripts/seed_knowledge_folder.py`
- Must: load+chunk each file, embed via `embed_batch(texts, input_type="document")`, store in `knowledge_chunks` table, use existing `src/shared/db/postgres.py` and `src/shared/llm/voyage.py`, be idempotent, print progress
- Run as: `python scripts/seed_knowledge_folder.py`

**Chunking strategy (locked):**
- Glossary: split by `##` section headings, keep header + content together
- Team directory: one chunk per person (JSON serialized as readable text)
- Rules: one chunk per rule entry
- Historical patterns: one chunk per past event

**Embedding model:** `voyage-3`, 1024 dimensions, already in `voyage.py`
**DB table:** `knowledge_chunks` — already created in Phase 0 migrations
**No OpenAI, no spaCy. All secrets in .env. Pydantic v2.**

### Claude's Discretion
- Chunk size limits (target ~500-800 tokens per chunk)
- Exact metadata schema for knowledge_chunks
- Error handling and retry logic in seed script
- Whether to use batch embedding or individual calls (batch is more efficient)

### Deferred Ideas (OUT OF SCOPE)
- Multi-project knowledge folder support — v2
- Real ACC project data import — Phase 4+ (uses ACC API)
- Knowledge folder versioning/updates — v2
- Automated re-seeding on file changes — v2
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| KF-01 | Glossary file: element types, materials, locations for demo building (demo_project.md) | Content schema and markdown section structure documented below |
| KF-02 | Team directory: 6-8 team members with roles, contacts, responsibilities (demo_project.json) | JSON object schema documented; chunking as readable text per person |
| KF-03 | Rules file: 15-20 rules covering material change approvals, thresholds, escalations (demo_project.yaml) | YAML rule schema documented; all required rule categories specified |
| KF-04 | Historical patterns: 10-15 past material change events with outcomes (demo_project.json) | Event object schema documented; at least 3 window events required for demo scenario |
| KF-05 | Seed script: chunk, embed via Voyage-3, store in pgvector (seed_knowledge_folder.py) | `embed_and_store()` signature confirmed; table schema confirmed; batch size confirmed; idempotency strategy documented |
</phase_requirements>

---

## Summary

Phase 2 has two distinct deliverables: (1) authoring four domain content files with specific fictional data for Harbor View Tower, and (2) a seed script that ingests those files into the `knowledge_chunks` pgvector table.

All infrastructure is already in place. The `knowledge_chunks` table exists with the exact schema `(id UUID, content TEXT, embedding vector(1024), source TEXT, metadata JSONB)`. The `embed_and_store()` function in `vector_store.py` is ready to use — it accepts a list of text strings plus a `source` string, handles `embed_batch()` internally, and executes a bulk INSERT via `execute_values`. The four knowledge files are empty stubs at their correct paths.

The seed script's primary concerns are: (a) correct chunking per file type, (b) idempotency via `DELETE FROM knowledge_chunks WHERE source = ?` before inserting, (c) batching the Voyage-3 calls in groups of 128 or fewer, and (d) Pydantic v2 for any internal data models. Content quality for the four files must directly support the demo scenario: Aluminum → Wood window substitution, 3rd Floor, Units 301-312, 12 units.

**Primary recommendation:** Use `embed_and_store()` from `vector_store.py` as the single insertion point — it already handles batching, `execute_values`, and connection lifecycle. The seed script only needs to own file loading, chunking, and idempotency DELETE.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyYAML | >=6.0 (in requirements) | Parse `demo_project.yaml` | Already in project, standard YAML library |
| json (stdlib) | 3.11 | Parse JSON knowledge files | No additional dependency needed |
| pathlib (stdlib) | 3.11 | Resolve knowledge folder paths | Cleaner than os.path, already used in project |
| pydantic | >=2.0 (in requirements) | Validate chunk metadata model | Project-wide Pydantic v2 requirement |
| psycopg2 + pgvector | in requirements | Execute DELETE (idempotency) | Already handles per-connection register_vector |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| textwrap (stdlib) | 3.11 | Normalizing whitespace in chunks | Before embedding to prevent embedding noise |
| re (stdlib) | 3.11 | Split markdown by `##` headings | Simple regex split, no need for markdown parser |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| regex `##` split | `mistune` or `markdown-it-py` | Overkill for simple section splitting; neither is in requirements |
| `embed_and_store()` directly | Manual `embed_batch()` + INSERT loop | More code, same result; `embed_and_store()` already handles `execute_values` bulk insert |
| DELETE + re-insert idempotency | `ON CONFLICT DO UPDATE` upsert | `knowledge_chunks` has no unique business key to conflict on; DELETE is simpler |

**Installation:**
No new packages required — all dependencies are already in `requirements.txt` / `pyproject.toml`.

---

## Architecture Patterns

### Recommended Project Structure

The files at their correct paths (all currently empty stubs):

```
knowledge_folder/
├── glossary/
│   └── demo_project.md          # KF-01: section-per-chunk
├── team_directory/
│   └── demo_project.json        # KF-02: one chunk per person
├── rules/
│   └── demo_project.yaml        # KF-03: one chunk per rule
└── historical_patterns/
    └── demo_project.json        # KF-04: one chunk per event

scripts/
└── seed_knowledge_folder.py     # KF-05: chunking + embedding + storage

tests/unit/
└── test_seed_knowledge_folder.py  # chunking logic unit tests (Wave 0 gap)
```

### Pattern 1: `embed_and_store()` Is the Single Insertion Primitive

**What:** `vector_store.embed_and_store(texts, source, metadata)` handles `embed_batch()` + `execute_values` INSERT in one call. It accepts `metadata` as a single dict applied uniformly to all chunks.

**Critical finding:** The current `embed_and_store()` signature applies ONE metadata dict to ALL chunks in the batch. Since each chunk needs distinct metadata (e.g., different `section_name`, `person_name`, `rule_id`, `event_id`), the seed script MUST call `embed_and_store()` once per logical chunk group sharing the same metadata, OR call it with individual single-item lists per chunk.

**Confirmed signature (from `vector_store.py`):**
```python
def embed_and_store(
    texts: list[str],
    source: str,
    metadata: dict | None = None,
) -> int:
```

The `metadata` dict is stored identically for every row in the batch. For per-chunk metadata, the pattern is:

```python
# Correct: call per chunk with distinct metadata
for chunk_text, chunk_meta in zip(texts, metadatas):
    embed_and_store([chunk_text], source=source, metadata=chunk_meta)
```

Or batch items that share the same metadata (e.g., all chunks from the same source file with source-level metadata only).

**Decision for seed script:** Use per-chunk calls to `embed_and_store()` to preserve distinct metadata per chunk. Voyage-3's 128-item batch limit is handled internally by `embed_batch()` — since `embed_and_store()` calls `embed_batch()` directly, single-item calls are fine for correctness; batching optimization is available if needed.

### Pattern 2: Idempotency via Source-Scoped DELETE

**What:** Before inserting, delete all existing rows with matching `source` values for the project.

**Why not upsert:** The `knowledge_chunks` table has no unique business key (only `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`). There is no natural key to `ON CONFLICT` against.

**Implementation:**
```python
# Requires direct postgres.py access — not covered by embed_and_store()
from src.shared.db.postgres import get_connection, release_connection

SOURCES = [
    "knowledge_folder/glossary/demo_project.md",
    "knowledge_folder/team_directory/demo_project.json",
    "knowledge_folder/rules/demo_project.yaml",
    "knowledge_folder/historical_patterns/demo_project.json",
]

conn = get_connection()
try:
    with conn.cursor() as cur:
        for source in SOURCES:
            cur.execute("DELETE FROM knowledge_chunks WHERE source = %s", (source,))
    conn.commit()
finally:
    release_connection(conn)
```

### Pattern 3: Markdown Section Chunking (`##` split)

**What:** Split glossary markdown on `##` headings using regex. Keep heading + body together per chunk.

```python
import re

def chunk_markdown_by_sections(text: str) -> list[tuple[str, str]]:
    """
    Returns list of (section_heading, full_section_text) tuples.
    Splits on ## headings (H2). Skips content before the first ##.
    """
    # Pattern: split on lines starting with ##
    pattern = r"(?m)^(?=## )"
    parts = re.split(pattern, text)
    chunks = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # Extract heading for metadata
        lines = part.splitlines()
        heading = lines[0].lstrip("#").strip() if lines else "unknown"
        chunks.append((heading, part))
    return chunks
```

### Pattern 4: JSON Array Chunking (Team + Historical)

**What:** Parse JSON array, iterate items, serialize each as readable text for embedding.

```python
import json

def chunk_team_directory(path: str) -> list[tuple[dict, str]]:
    """Returns list of (metadata_dict, text_for_embedding) per member."""
    with open(path) as f:
        members = json.load(f)
    chunks = []
    for member in members:
        # Serialize as human-readable text (improves embedding quality)
        text = (
            f"Name: {member['name']}\n"
            f"Role: {member['role']}\n"
            f"Email: {member['email']}\n"
            f"Phone: {member['phone']}\n"
            f"Responsibilities: {', '.join(member['responsibilities'])}\n"
            f"Area of Authority: {member['area_of_authority']}"
        )
        meta = {
            "type": "team_member",
            "name": member["name"],
            "role": member["role"],
        }
        chunks.append((meta, text))
    return chunks
```

### Pattern 5: YAML Rules Chunking

```python
import yaml

def chunk_rules(path: str) -> list[tuple[dict, str]]:
    """Returns list of (metadata_dict, text_for_embedding) per rule."""
    with open(path) as f:
        data = yaml.safe_load(f)
    rules = data.get("rules", data)  # handle top-level key or bare list
    chunks = []
    for rule in rules:
        text = (
            f"Rule ID: {rule['rule_id']}\n"
            f"Description: {rule['description']}\n"
            f"Condition: {rule['condition']}\n"
            f"Action: {rule['action']}\n"
            f"Stakeholders: {', '.join(rule.get('stakeholders', []))}\n"
            f"Priority: {rule.get('priority', 'normal')}"
        )
        meta = {
            "type": "rule",
            "rule_id": rule["rule_id"],
            "priority": rule.get("priority", "normal"),
        }
        chunks.append((meta, text))
    return chunks
```

### Anti-Patterns to Avoid

- **Passing all chunks as one `embed_and_store()` call with a shared metadata dict:** Each chunk needs distinct `rule_id`, `section_name`, etc. The current `embed_and_store()` applies one metadata to all rows.
- **Importing `vector_store` at module level before env vars are set:** Follow the `sys.modules.pop` + autouse fixture pattern from `test_vector_store.py`.
- **Using `yaml.load()` without `Loader=yaml.SafeLoader`:** Always `yaml.safe_load()` — project uses PyYAML and has no custom constructors.
- **Not calling `register_vector(conn)` on each connection:** Already handled by `get_connection()` in `postgres.py`, but if the seed script opens raw psycopg2 connections directly, this would fail.
- **JSON text as raw serialized object:** For embedding quality, serialize JSON items as human-readable prose sentences, not `json.dumps()` output.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Embedding + DB insert | Custom embed-then-insert loop | `embed_and_store()` in `vector_store.py` | Already handles `execute_values`, connection pool, `register_vector`, logging |
| DB connection management | Direct `psycopg2.connect()` | `get_connection()` / `release_connection()` in `postgres.py` | Per-connection `register_vector()` and pool management already implemented |
| YAML parsing | Custom key=value parser | `yaml.safe_load()` | Handles multi-line strings, nested lists, all YAML edge cases |
| JSON parsing | String manipulation | `json.load()` | Handles encoding, escaping, nesting |
| Batch size management | Manual chunking of texts list | Pass directly to `embed_batch()` | `voyage.py` docstring confirms 128-item limit; single-item calls per chunk are well within limits |

**Key insight:** The entire embedding + storage pipeline is already written. The seed script is a data transformation script — its only unique logic is file reading, format-specific chunking, and the idempotency DELETE.

---

## Common Pitfalls

### Pitfall 1: embed_and_store() Shares Metadata Across All Texts in the Call

**What goes wrong:** Caller passes 20 rule chunks in one `embed_and_store(texts=all_rules, ...)` call with a metadata dict like `{"type": "rule"}`. Every stored row gets the same metadata — no `rule_id` differentiation. Later retrieval filtering is impossible.

**Why it happens:** The signature `metadata: dict | None = None` stores one dict per row, not one per text. This is by design for the common case of "all these chunks share source-level metadata."

**How to avoid:** Call `embed_and_store([single_chunk_text], source=..., metadata=per_chunk_dict)` in a loop. Performance cost is minimal — Voyage-3 API overhead for single-item calls adds negligible latency for a one-time seed script.

**Warning signs:** All rows for a given source having identical metadata in the DB.

### Pitfall 2: Voyage-3 Rate Limits Under Rapid Successive Calls

**What goes wrong:** Seeding ~50-60 chunks with individual `embed_and_store()` calls could trigger Voyage-3 rate limits if called in a tight loop.

**Why it happens:** Voyage-3 free tier limits: 3 RPM on the free tier; paid tiers are much higher. The `embed_batch()` in `voyage.py` confirms "up to 128 per call."

**How to avoid:** Either (a) use a single `embed_batch()` call for all same-type chunks and then do direct DB inserts with individual metadata rows, or (b) add a small `time.sleep(0.1)` between calls as a defensive measure. Since this is a seed script (one-time, not latency-sensitive), approach (a) is cleaner.

**Alternative approach for KF-05 (recommended):** Collect `(text, metadata)` pairs from all chunkers, call `embed_batch(all_texts)` once, then bulk-INSERT with per-row metadata directly via `execute_values`. This uses the DB primitives from `postgres.py` directly rather than `embed_and_store()`.

### Pitfall 3: Markdown Chunks Too Large for Target Token Budget

**What goes wrong:** A glossary section like "## Materials" could be 600+ words, approaching or exceeding the 500-800 token target.

**Why it happens:** Splitting only on `##` H2 headings produces chunks of highly variable size.

**How to avoid:** After splitting on `##`, check character count. If a section exceeds ~3000 characters (rough proxy for 800 tokens), split further by `###` sub-headings or by blank-line-separated paragraphs. For the demo glossary (author-controlled), design the content to stay within section size targets.

**Warning signs:** Single chunk text length > 3000 characters.

### Pitfall 4: sys.modules.pop Missing Parent Package in Tests

**What goes wrong:** Tests for the seed script that mock `vector_store` fail because the parent module cache returns the old object.

**Why it happens:** Documented in `STATE.md`: "sys.modules.pop must include PACKAGE module — also pop the parent package."

**How to avoid:** In test autouse fixture, pop both `src.shared.db.vector_store` and `src.shared.db` (the package), following the exact pattern in `test_vector_store.py`.

### Pitfall 5: YAML Top-Level Structure Assumption

**What goes wrong:** Rule chunker assumes `yaml.safe_load()` returns a list directly, but if the YAML file uses a top-level key `rules:` the loader returns a dict.

**How to avoid:** Use `data.get("rules", data) if isinstance(data, dict) else data` — handle both bare list and keyed dict formats.

---

## Code Examples

Verified patterns from existing project source:

### Confirmed embed_and_store() Signature
```python
# Source: src/shared/db/vector_store.py (read directly)
def embed_and_store(
    texts: list[str],
    source: str,
    metadata: dict | None = None,
) -> int:
    """Returns the number of chunks stored."""
    # Calls embed_batch(texts, input_type="document") internally
    # Uses execute_values for bulk INSERT into knowledge_chunks
```

### Confirmed knowledge_chunks Table Schema
```sql
-- Source: infra/sql/001_create_tables.sql (read directly)
CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content     TEXT NOT NULL,
    embedding   vector(1024) NOT NULL,
    source      TEXT NOT NULL,
    metadata    JSONB NOT NULL DEFAULT '{}'
);
```
No `project_id` column — idempotency must use `source` text matching.

### Confirmed Voyage-3 Batch Limit
```python
# Source: src/shared/llm/voyage.py (read directly)
def embed_batch(texts: list[str], input_type: str = "document") -> list[list[float]]:
    """
    Embed multiple text strings using Voyage-3.
    Args:
        texts: List of texts to embed. Voyage-3 supports up to 128 per call.
    """
```
**Batch size: 128 max.** For ~50-60 total knowledge chunks, a single `embed_batch()` call is safe.

### Idempotency DELETE Pattern
```python
# Source: postgres.py pattern + knowledge_chunks schema analysis
conn = get_connection()
try:
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM knowledge_chunks WHERE source = ANY(%s)",
            ([
                "knowledge_folder/glossary/demo_project.md",
                "knowledge_folder/team_directory/demo_project.json",
                "knowledge_folder/rules/demo_project.yaml",
                "knowledge_folder/historical_patterns/demo_project.json",
            ],)
        )
    conn.commit()
finally:
    release_connection(conn)
```

### Metadata Schema Recommendation (Claude's Discretion)

Each chunk's metadata JSONB should include:

```python
# Glossary chunk
{
    "type": "glossary",
    "section": "Element Types",      # from ## heading
    "project": "harbor_view_tower",
    "file": "demo_project.md"
}

# Team member chunk
{
    "type": "team_member",
    "name": "Sarah Chen",
    "role": "Project Manager",
    "project": "harbor_view_tower"
}

# Rule chunk
{
    "type": "rule",
    "rule_id": "RULE-001",
    "priority": "high",
    "project": "harbor_view_tower"
}

# Historical event chunk
{
    "type": "historical_event",
    "event_id": "EVT-001",
    "material_original": "aluminum",
    "material_new": "wood",
    "pm_decision": "accepted",
    "project": "harbor_view_tower"
}
```

Including `material_original`, `material_new`, and `pm_decision` in historical event metadata enables future filtering in CTX-02's retrieval module without re-parsing the content text.

### Preferred Seed Script Architecture (Single embed_batch)

```python
# High-level pattern — avoids per-chunk Voyage API calls
all_texts = []
all_metas = []
all_sources = []

# Collect from all chunkers
for text, meta in chunk_glossary(glossary_path):
    all_texts.append(text)
    all_metas.append(meta)
    all_sources.append("knowledge_folder/glossary/demo_project.md")

# ... repeat for team, rules, history

# Single batch embedding call (all chunks < 128 limit)
embeddings = embed_batch(all_texts, input_type="document")

# Bulk insert with per-row metadata
conn = get_connection()
try:
    rows = [
        (text, emb, src, json.dumps(meta))
        for text, emb, src, meta in zip(all_texts, embeddings, all_sources, all_metas)
    ]
    with conn.cursor() as cur:
        execute_values(
            cur,
            "INSERT INTO knowledge_chunks (content, embedding, source, metadata) VALUES %s",
            rows,
        )
    conn.commit()
finally:
    release_connection(conn)
```

This approach: one Voyage API call, one DB transaction, per-row distinct metadata.

---

## Content Requirements for Demo Scenario

The content files must contain specific data that makes the Aluminum → Wood, 3rd Floor, 12 Units scenario work end-to-end in later phases.

### Glossary (KF-01) Required Sections

| Section (## heading) | Required Content |
|---------------------|-----------------|
| ## Element Types | Windows (W prefix), Doors (D prefix), walls, floors, ceilings — with unit numbering scheme W-301 through W-312 |
| ## Materials | Aluminum frames (standard spec), Wood frames (spec equivalent), glass, steel, concrete, gypsum board — with performance comparison for substitution scenario |
| ## Locations | Floor plan: 5 floors, 4 wings (N/S/E/W), units 301-312 on 3rd floor north wing specifically |
| ## Abbreviations | W = Window, D = Door, PM = Project Manager, CO = Change Order, RFI = Request for Information |
| ## Harbor View Tower | Building overview: 5 stories, 312 units, mixed-use, year built, general contractor |

### Historical Patterns (KF-04) Required Events

At least 3 window-related events are required. Recommended distribution:

| Event | Type | Decision | Purpose |
|-------|------|----------|---------|
| EVT-001 | Aluminum → Wood windows, 5th floor, 8 units | accepted | Direct precedent for demo |
| EVT-002 | Aluminum → Vinyl windows, 2nd floor, 15 units | rejected (spec mismatch) | Negative precedent |
| EVT-003 | Wood → Aluminum windows, 1st floor, 6 units | accepted | Reverse precedent |
| EVT-004 to EVT-015 | Other material changes (doors, flooring, etc.) | varied | Variety for retrieval |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `yaml.load()` bare | `yaml.safe_load()` | PyYAML 5.1 (2019) | Security: `yaml.load()` executes arbitrary Python |
| openai embeddings | voyageai (voyage-3) | Project decision | No `openai` package; voyageai returns `EmbeddingsObject`, not list |
| Pydantic v1 `@validator` | Pydantic v2 `@field_validator + @classmethod` | Project decision | `@validator` raises `PydanticUserError` in v2 |
| Global `register_vector()` | Per-connection `register_vector(conn)` | Project decision | Global registration fails with ThreadedConnectionPool |

---

## Open Questions

1. **Chunk count vs. Voyage-3 batch limit**
   - What we know: voyage-3 supports up to 128 texts per `embed_batch()` call; target is ~50-60 chunks total
   - What's unclear: Exact chunk count depends on authored content size (especially number of glossary `##` sections)
   - Recommendation: Design glossary with 6-8 `##` sections. Total chunks: ~8 (glossary) + 7 (team) + 18 (rules) + 12 (history) = ~45. Well within 128 limit.

2. **Seed script entry point — `python scripts/seed_knowledge_folder.py` path resolution**
   - What we know: `pyproject.toml` sets `package-dir = {"" = "."}` (root is package base). Scripts import `src.shared.*`
   - What's unclear: Whether running from repo root resolves imports correctly without `PYTHONPATH` set
   - Recommendation: Add `sys.path.insert(0, str(Path(__file__).parent.parent))` at top of seed script for standalone execution. Follow pattern from existing scripts.

3. **`test_retrieval_quality.py` dependency**
   - What we know: `scripts/test_retrieval_quality.py` already exists as a stub (TEST-05); it tests 20+ queries against the seeded knowledge folder
   - What's unclear: Whether Phase 2 should stub this file or leave it for Phase 9
   - Recommendation: Leave for Phase 9; Phase 2 only needs unit tests for chunking logic.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | `pyproject.toml` → `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/unit/test_seed_knowledge_folder.py -x -q` |
| Full suite command | `pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| KF-01 | Glossary file has correct sections and demo content | manual review | N/A — content validation | N/A |
| KF-02 | Team directory has 6-8 members with required fields | unit | `pytest tests/unit/test_seed_knowledge_folder.py::test_chunk_team_directory -x` | Wave 0 gap |
| KF-03 | Rules file has 15-20 rules with required fields | unit | `pytest tests/unit/test_seed_knowledge_folder.py::test_chunk_rules -x` | Wave 0 gap |
| KF-04 | Historical patterns has 10-15 events with required fields | unit | `pytest tests/unit/test_seed_knowledge_folder.py::test_chunk_historical_patterns -x` | Wave 0 gap |
| KF-05 | Seed script chunks correctly, calls embed_and_store, is idempotent | unit | `pytest tests/unit/test_seed_knowledge_folder.py -x` | Wave 0 gap |
| KF-05 | Markdown section chunking splits on `##` headings | unit | `pytest tests/unit/test_seed_knowledge_folder.py::test_chunk_markdown_by_sections -x` | Wave 0 gap |

### Sampling Rate
- **Per task commit:** `pytest tests/unit/test_seed_knowledge_folder.py -x -q`
- **Per wave merge:** `pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/test_seed_knowledge_folder.py` — covers KF-02 through KF-05 chunking logic
  - `test_chunk_markdown_by_sections` — verifies split on `##`, returns (heading, text) pairs
  - `test_chunk_team_directory` — verifies one chunk per member, required fields present
  - `test_chunk_rules` — verifies one chunk per rule, `rule_id` in metadata
  - `test_chunk_historical_patterns` — verifies one chunk per event, `event_id` in metadata
  - `test_seed_calls_delete_before_insert` — verifies idempotency DELETE runs before INSERT
  - `test_seed_calls_embed_batch_with_document_type` — verifies `input_type="document"`
- [ ] Existing `tests/conftest.py` shared fixtures (`mock_db_conn`, `mock_voyage_client`) are sufficient — no new conftest entries needed

*(KF-01 glossary content correctness is validated manually by reviewing the authored file — no automated test can verify "the content is domain-accurate.")*

---

## Sources

### Primary (HIGH confidence)
- `src/shared/db/vector_store.py` — confirmed `embed_and_store()` signature, metadata behavior, INSERT query
- `src/shared/llm/voyage.py` — confirmed `embed_batch()` signature, 128-item limit documented in docstring
- `infra/sql/001_create_tables.sql` — confirmed `knowledge_chunks` schema (id, content, embedding vector(1024), source, metadata JSONB)
- `infra/sql/002_create_indexes.sql` — confirmed HNSW index on `knowledge_chunks.embedding`
- `src/shared/db/postgres.py` — confirmed connection pool pattern, `register_vector` per-connection
- `.planning/phases/02-knowledge-folder/02-CONTEXT.md` — locked decisions verbatim
- `.planning/STATE.md` — accumulated architectural decisions and known pitfalls

### Secondary (MEDIUM confidence)
- `pyproject.toml` — confirmed `PyYAML>=6.0` and `pydantic>=2.0` in project dependencies
- `tests/unit/test_vector_store.py` — confirmed test isolation pattern with `sys.modules.pop` + autouse fixture
- `tests/conftest.py` — confirmed shared fixtures available (`mock_db_conn`, `mock_voyage_client`)

### Tertiary (LOW confidence)
- Voyage-3 rate limits: free tier 3 RPM — not verified from official docs, cited as risk mitigation

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in requirements.txt, no new dependencies
- Architecture: HIGH — `embed_and_store()` and table schema read directly from source
- Pitfalls: HIGH — metadata-per-row pitfall confirmed by reading `vector_store.py` implementation; test isolation pitfalls confirmed from `STATE.md` accumulated decisions
- Content requirements: HIGH — locked in `02-CONTEXT.md` by user

**Research date:** 2026-03-13
**Valid until:** 2026-04-13 (30 days — stable stack, no fast-moving dependencies)
