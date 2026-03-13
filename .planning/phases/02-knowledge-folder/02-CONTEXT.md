# Phase 2: Knowledge Folder — Context

**Gathered:** 2026-03-12
**Status:** Ready for planning
**Source:** PRD Express Path (CLAUDE_PLAN.md)

<domain>
## Phase Boundary

Phase 2 delivers all project domain knowledge content and the seed script to load it into pgvector:

- `knowledge_folder/glossary/demo_project.md` — element types, materials, locations for the demo building
- `knowledge_folder/team_directory/demo_project.json` — 6-8 team members with roles, contacts, responsibilities
- `knowledge_folder/rules/demo_project.yaml` — 15-20 rules covering material change approvals, thresholds, escalations
- `knowledge_folder/historical_patterns/demo_project.json` — 10-15 past material change events with outcomes
- `scripts/seed_knowledge_folder.py` — chunks all knowledge files, embeds via Voyage-3, stores in pgvector knowledge_chunks table

Demo scenario: Window material substitution — Aluminum → Wood, 3rd Floor, 12 Units.
</domain>

<decisions>
## Implementation Decisions

### Glossary File (KF-01)
- File: `knowledge_folder/glossary/demo_project.md`
- Must cover: element types (windows, doors, walls, floors, ceilings), materials (aluminum, wood, glass, steel, concrete, gypsum board), locations (building floors 1-5, zones: north/south/east/west wing, specific areas: lobby, mechanical room, units 301-312)
- Demo building: 5-story mixed-use building, "Harbor View Tower", 312 units
- Format: Markdown with clear sections for element types, materials, locations, abbreviations

### Team Directory (KF-02)
- File: `knowledge_folder/team_directory/demo_project.json`
- Must have 6-8 team members covering: Project Manager (Sarah Chen), Procurement Officer (Mike Torres), Lead Architect (James Park), Structural Engineer (Lisa Wong), Site Superintendent (Carlos Rivera), Supplier Contact (Jane Miller at AlumaCraft), Owner Representative (Robert Hayes)
- Each entry: name, role, email, phone, responsibilities (list), area_of_authority
- JSON format with array of team member objects

### Rules File (KF-03)
- File: `knowledge_folder/rules/demo_project.yaml`
- Must have 15-20 rules covering:
  - Material change approval thresholds: <$5K = PM approval, $5K-$50K = PM + Owner, >$50K = immediate escalation
  - Change order requirements: any structural material change needs architect sign-off
  - Lead time rules: window orders >10 units need 6-week lead time
  - Notification rules: who gets notified for what change types
  - Schedule impact rules: changes affecting critical path need owner notification within 24h
  - Quality/substitution rules: all substitutions must meet or exceed original spec
- YAML format with rule_id, description, condition, action, stakeholders, priority fields

### Historical Patterns (KF-04)
- File: `knowledge_folder/historical_patterns/demo_project.json`
- Must have 10-15 past material change events
- Each entry: event_id, date, material_original, material_new, location, quantity, reason, outcome, cost_impact, schedule_impact_days, pm_decision (accepted/rejected), lessons_learned
- Should include variety: some accepted (good outcome), some rejected, some with cost overruns, some with schedule impacts
- Include at least 3 window-related changes to support the demo scenario retrieval

### Seed Script (KF-05)
- File: `scripts/seed_knowledge_folder.py`
- Must:
  1. Load and chunk each knowledge file (glossary.md → paragraphs, team.json → one chunk per member, rules.yaml → one chunk per rule, history.json → one chunk per event)
  2. Embed each chunk via Voyage-3 using `embed_batch(texts, input_type="document")`
  3. Store in `knowledge_chunks` table (id, content, embedding vector(1024), source, metadata jsonb)
  4. Use the existing `src/shared/db/postgres.py` and `src/shared/llm/voyage.py` modules
  5. Be idempotent (clear existing chunks for this project before inserting, or use upsert)
  6. Print progress: chunks loaded, embedded, stored
- Run as: `python scripts/seed_knowledge_folder.py`

### Chunking Strategy
- Glossary: split by `##` section headings, keep section header + content together
- Team directory: one chunk per person (JSON serialized as readable text)
- Rules: one chunk per rule entry
- Historical patterns: one chunk per past event
- All chunks include source filename and type in metadata

### Claude's Discretion
- Chunk size limits (target ~500-800 tokens per chunk)
- Exact metadata schema for knowledge_chunks
- Error handling and retry logic in seed script
- Whether to use batch embedding or individual calls (batch is more efficient)
</decisions>

<specifics>
## Specific Requirements

- Demo scenario: Aluminum → Wood window substitution, 3rd Floor (Units 301-312), 12 units
- Harbor View Tower: 5-story building, mixed-use
- Vector embedding: `voyage-3`, 1024 dimensions (already in vector_store.py)
- DB table: `knowledge_chunks` (id, content text, embedding vector(1024), source text, metadata jsonb) — already created in Phase 0 SQL migrations
- Use `embed_batch(texts, input_type="document")` for storage embeddings
- No OpenAI, no spaCy
- All secrets in .env
- Pydantic v2 for any data validation in seed script
</specifics>

<deferred>
## Deferred Ideas

- Multi-project knowledge folder support — v2
- Real ACC project data import — Phase 4+ (uses ACC API)
- Knowledge folder versioning/updates — v2
- Automated re-seeding on file changes — v2
</deferred>

---

*Phase: 02-knowledge-folder*
*Context gathered: 2026-03-12 via PRD Express Path*
