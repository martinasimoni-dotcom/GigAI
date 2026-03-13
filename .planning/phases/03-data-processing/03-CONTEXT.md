# Phase 3: Data Processing — Context

**Gathered:** 2026-03-12
**Status:** Ready for planning
**Source:** PRD Express Path (CLAUDE_PLAN.md)

<domain>
## Phase Boundary

Phase 3 delivers the first three steps of the SYSTEM pipeline — transforming raw Pub/Sub events into structured, validated, routed normalized events:

1. **Normalization** (PROC-01, PROC-02): Haiku 4.5 extracts structured fields from raw event payloads. Outputs a valid NormalizedEvent. Flags low-confidence extractions (<70%) for manual review rather than rejecting.
2. **Scope Filter** (PROC-03): Validates the event against the ACC project scope. Rejects out-of-scope events. Immediately escalates events with estimated cost >$50K.
3. **Routing** (PROC-04, PROC-05): Haiku 4.5 classifies the event type. Loads the matching YAML config from `config/event_types/`. Publishes to normalized-events Pub/Sub topic.

Also delivers:
- `config/prompts/normalization.txt` — Haiku normalization prompt
- `config/prompts/routing.txt` — Haiku routing prompt
- Stub event type configs: `config/event_types/schedule_update.yaml`, `config/event_types/rfi_request.yaml`
- Full event type config: `config/event_types/material_change.yaml` (Phase 5 completes this — Phase 3 creates a working stub)
</domain>

<decisions>
## Implementation Decisions

### Normalization Prompt (PROC-01)
- File: `config/prompts/normalization.txt`
- Must instruct Haiku to extract: `material` (dict with `original` and `new`), `location`, `quantity` (int), `people` (list of {name, role}), `deadlines` (list), `change_type`, `summary` (one sentence), `confidence` (0-100 integer)
- Output must be valid JSON matching the NormalizedEvent Pydantic schema
- Prompt must include the full NormalizedEvent JSON schema so Haiku knows the exact output format
- Include few-shot example with the demo scenario (aluminum → wood windows)

### Normalizer Module (PROC-02)
- File: `src/system/data_processing/normalizer.py`
- Function: `normalize_event(raw_event: RawEvent) -> NormalizedEvent`
- Calls `call_haiku(prompt, system)` from `src/shared/llm/claude.py`
- Validates output with Pydantic NormalizedEvent
- If `confidence < 70`: sets `review_required=True` on the event and logs warning (does NOT reject)
- If Pydantic validation fails: retry up to 3 times with exponential backoff (tenacity)
- The NormalizedEvent model needs a `review_required: bool = False` field (add if missing)
- Also needs `confidence: int = Field(ge=0, le=100, default=50)` field

### Scope Filter (PROC-03)
- File: `src/system/data_processing/scope_filter.py`
- Function: `filter_event(event: NormalizedEvent, project_scope: dict) -> FilterResult`
- FilterResult: Pydantic model with `passed: bool`, `reason: str`, `escalate_immediately: bool`, `alert_pm: bool`
- Rejects event if location is out of scope (not matching known project locations)
- Sets `escalate_immediately=True` if estimated cost >$50K (check event metadata/payload)
- Returns FilterResult — does NOT raise exceptions
- Project scope comes from ACC project data (in Phase 3: use a simple dict with known locations)

### Routing Prompt (PROC-04)
- File: `config/prompts/routing.txt`
- Must instruct Haiku to classify the event into one of: `material_change`, `schedule_update`, `rfi_request`, `other`
- Input: the normalized event JSON
- Output: JSON with `event_type: str` and `confidence: int`
- Include all known event types with descriptions

### Router Module (PROC-05)
- File: `src/system/data_processing/router.py`
- Function: `route_event(event: NormalizedEvent) -> RoutedEvent`
- RoutedEvent: Pydantic model with `event: NormalizedEvent`, `event_type: str`, `config: EventTypeConfig`, `config_path: str`
- Calls `call_haiku(prompt, system)` with routing prompt
- Loads matching config YAML from `config/event_types/{event_type}.yaml`
- Validates loaded YAML against `EventTypeConfig` Pydantic schema
- Falls back to `other` if classification fails or config not found
- Publishes to normalized-events Pub/Sub topic: create a second topic `PUBSUB_TOPIC_NORMALIZED_EVENTS`

### Event Type Config Stubs (DOM-02 partial)
- `config/event_types/material_change.yaml` — working stub with basic fields (Phase 5 completes it)
- `config/event_types/schedule_update.yaml` — stub
- `config/event_types/rfi_request.yaml` — stub
- All must validate against EventTypeConfig Pydantic schema

### Package Structure
- `src/system/__init__.py`
- `src/system/data_processing/__init__.py`

### Settings Addition
- Add `PUBSUB_TOPIC_NORMALIZED_EVENTS` to settings.py and .env.example

### Claude's Discretion
- Exact Haiku prompt wording (few-shot examples, JSON schema formatting)
- tenacity retry configuration for Pydantic validation failures
- FilterResult model location (inline in scope_filter.py)
- RoutedEvent model location (inline in router.py)
- Logging format for rejected/flagged events
</decisions>

<specifics>
## Specific Requirements

- Haiku model: `claude-haiku-4-5-20251001` (already in claude.py)
- Sonnet model: `claude-sonnet-4-20250514` (for proposals — not used in Phase 3)
- NormalizedEvent already defined in `src/shared/models/events.py` — check if it needs `review_required` and `confidence` fields
- EventTypeConfig already defined in `src/shared/models/config.py`
- Demo scenario: "change third-floor windows from aluminum to wood, 12 units" → `event_type="material_change"`, `material.original="aluminum"`, `material.new="wood"`, `location="3rd floor"`, `quantity=12`
- All secrets in .env
- No OpenAI, no spaCy
- Pydantic v2 for all models
</specifics>

<deferred>
## Deferred Ideas

- Full material_change.yaml config (rules, signal types, enrichment queries) — Phase 5
- Pub/Sub subscription setup for normalized-events — Phase 5+
- Async Pub/Sub publishing — Phase 7
- Multi-project scope isolation — v2
</deferred>

---

*Phase: 03-data-processing*
*Context gathered: 2026-03-12 via PRD Express Path*
