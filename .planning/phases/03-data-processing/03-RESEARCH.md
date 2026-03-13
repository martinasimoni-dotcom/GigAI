# Phase 3: Data Processing - Research

**Researched:** 2026-03-13
**Domain:** LLM-based event normalization, scope filtering, event routing, Pub/Sub publishing
**Confidence:** HIGH (all findings verified from source files in the repo)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **Normalization Prompt (PROC-01):** File `config/prompts/normalization.txt`. Extract: `material` dict with `original`/`new`, `location`, `quantity` (int), `people` (list of {name, role}), `deadlines` (list), `change_type`, `summary` (one sentence), `confidence` (0-100 int). Output valid JSON matching NormalizedEvent Pydantic schema. Include full NormalizedEvent JSON schema in prompt. Include few-shot example with aluminum-to-wood demo scenario.
- **Normalizer Module (PROC-02):** File `src/system/data_processing/normalizer.py`. Function `normalize_event(raw_event: RawEvent) -> NormalizedEvent`. Calls `call_haiku(prompt, system)`. Validates with Pydantic. If confidence < 70 sets `review_required=True` and logs warning (does NOT reject). Retry up to 3 times with exponential backoff (tenacity) on Pydantic validation failures. Add `review_required: bool = False` and `confidence: int = Field(ge=0, le=100, default=50)` fields to NormalizedEvent.
- **Scope Filter (PROC-03):** File `src/system/data_processing/scope_filter.py`. Function `filter_event(event: NormalizedEvent, project_scope: dict) -> FilterResult`. FilterResult Pydantic model: `passed: bool`, `reason: str`, `escalate_immediately: bool`, `alert_pm: bool`. Rejects if location out of scope. Sets `escalate_immediately=True` if cost > $50K. Returns FilterResult, never raises.
- **Routing Prompt (PROC-04):** File `config/prompts/routing.txt`. Classify into: `material_change`, `schedule_update`, `rfi_request`, `other`. Output JSON: `event_type: str`, `confidence: int`. Include all event types with descriptions.
- **Router Module (PROC-05):** File `src/system/data_processing/router.py`. Function `route_event(event: NormalizedEvent) -> RoutedEvent`. RoutedEvent: `event: NormalizedEvent`, `event_type: str`, `config: EventTypeConfig`, `config_path: str`. Calls `call_haiku`. Loads YAML from `config/event_types/{event_type}.yaml`. Validates with EventTypeConfig. Falls back to `other` if classification fails or config not found. Publishes to normalized-events Pub/Sub topic using `settings.pubsub_topic_normalized_events`.
- **Event Type Config Stubs:** `config/event_types/material_change.yaml`, `schedule_update.yaml`, `rfi_request.yaml`. All must validate against EventTypeConfig.
- **Package init files:** `src/system/__init__.py` and `src/system/data_processing/__init__.py` (already exist as empty stubs).
- **Settings Addition:** `PUBSUB_TOPIC_NORMALIZED_EVENTS` already present in settings.py and .env.example — no action needed.
- **Models:** Pydantic v2 only. `field_validator` + `@classmethod`. `ConfigDict`. No v1 `@validator`.
- **No OpenAI, no spaCy. Haiku model is `claude-haiku-4-5-20251001`.**

### Claude's Discretion

- Exact Haiku prompt wording (few-shot examples, JSON schema formatting)
- tenacity retry configuration for Pydantic validation failures
- FilterResult model location (inline in scope_filter.py)
- RoutedEvent model location (inline in router.py)
- Logging format for rejected/flagged events

### Deferred Ideas (OUT OF SCOPE)

- Full material_change.yaml config (rules, signal types, enrichment queries) — Phase 5
- Pub/Sub subscription setup for normalized-events — Phase 5+
- Async Pub/Sub publishing — Phase 7
- Multi-project scope isolation — v2
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PROC-01 | Haiku normalization prompt: extract material, location, quantity, people, deadlines, change_type, summary → valid JSON matching NormalizedEvent schema | call_haiku() supports output_schema for guaranteed JSON; prompt pattern documented below |
| PROC-02 | Normalizer module: calls Haiku, validates output with Pydantic, flags extraction confidence <70% for manual review | NormalizedEvent missing review_required and confidence fields — must add; tenacity already imported in claude.py |
| PROC-03 | Scope filter: validates event against ACC project scope, rejects out-of-scope changes, escalates cost >$50K immediately | FilterResult inline Pydantic model; project_scope dict structure documented below |
| PROC-04 | Haiku routing prompt: classify event into known event_type string mapping to a YAML config | Routing output schema documented; event_type values map directly to YAML filenames |
| PROC-05 | Router module: calls Haiku for classification, loads matching config from config/event_types/, publishes to normalized-events topic | publish pattern from pubsub.py; settings.pubsub_topic_normalized_events already set; EventTypeConfig fields documented |
</phase_requirements>

---

## Summary

Phase 3 builds the first three processing steps in the GigAI pipeline: normalization (RawEvent → NormalizedEvent via Haiku), scope filtering (NormalizedEvent → FilterResult), and routing (NormalizedEvent → RoutedEvent + Pub/Sub publish). All three steps are already scaffolded as empty stub files. The entire foundation layer (models, LLM clients, settings, Pub/Sub) is complete and can be used directly.

The critical finding is that `NormalizedEvent` in `events.py` is missing two required fields (`review_required` and `confidence`) that the normalization logic depends on. These must be added before the normalizer can be implemented. All other models (`RawEvent`, `EventTypeConfig`) are complete and correct. The `call_haiku()` function already supports `output_schema` for guaranteed structured JSON output, making structured extraction reliable.

`PUBSUB_TOPIC_NORMALIZED_EVENTS` is already in `settings.py` (line 29: `pubsub_topic_normalized_events: str = "normalized-events"`) and in `.env.example` — no settings changes are needed. The publish pattern to use is a direct parallel of `publish_event()` in `src/input/pubsub.py`.

**Primary recommendation:** Implement in order — (1) add fields to NormalizedEvent, (2) normalizer, (3) scope filter, (4) router with Pub/Sub publish, (5) YAML stubs, (6) prompts. Tests follow the `patch.object(module, '_client', mock)` pattern established in test_claude_client.py.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| anthropic | >=0.40.0 | Haiku LLM calls via `call_haiku()` | Already in requirements; call_haiku() verified |
| pydantic v2 | >=2.0 | Model validation for NormalizedEvent, FilterResult, RoutedEvent, EventTypeConfig | Project-wide standard; ConfigDict + field_validator pattern enforced |
| tenacity | (already installed, used in claude.py) | Retry with exponential backoff on Pydantic validation failure | Already imported in claude.py; use same import |
| pyyaml | (already installed, used in tests) | Load event type YAML configs | yaml.safe_load() for YAML parsing |
| google-cloud-pubsub | (already installed) | Publish NormalizedEvent to normalized-events topic | Already used in pubsub.py |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json | stdlib | Parse Haiku JSON responses, serialize events for Pub/Sub | Always |
| logging | stdlib | Structured log dicts for rejected/flagged events | Always |
| pathlib | stdlib | Resolve YAML config file paths relative to project root | In router for YAML loading |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| output_schema in call_haiku | System prompt JSON instruction only | output_schema guarantees JSON; system prompt alone can produce markdown preamble |
| tenacity in normalizer | manual try/except loop | tenacity already in project; consistent with claude.py retry pattern |

**Installation:** No new packages required. All dependencies already present.

---

## Architecture Patterns

### Recommended Project Structure

All new files fit into the existing scaffold:

```
src/system/data_processing/
├── __init__.py          # exists (empty)
├── normalizer.py        # exists (empty) — PROC-02
├── scope_filter.py      # exists (empty) — PROC-03
└── router.py            # exists (empty) — PROC-05

config/
├── prompts/
│   ├── normalization.txt  # exists (empty) — PROC-01
│   └── routing.txt        # exists (empty) — PROC-04
└── event_types/
    ├── material_change.yaml  # exists (empty) — stub
    ├── schedule_update.yaml  # exists (empty) — stub
    └── rfi_request.yaml      # exists (empty) — stub
```

### Pattern 1: Haiku Call with Structured Output

`call_haiku()` signature (verified from `src/shared/llm/claude.py`):

```python
def call_haiku(
    prompt: str,
    system: str,
    output_schema: dict | None = None,
    max_tokens: int = 4096,
) -> str:
```

Two valid approaches for JSON extraction. The `output_schema` approach is more reliable:

```python
# Approach A: output_schema (RECOMMENDED — guarantees JSON)
# Source: src/shared/llm/claude.py lines 74-110
from src.shared.llm.claude import call_haiku

NORMALIZED_EVENT_SCHEMA = {
    "type": "object",
    "properties": {
        "event_id": {"type": "string"},
        "source": {"type": "string"},
        "event_type": {"type": "string"},
        "material_original": {"type": ["string", "null"]},
        "material_new": {"type": ["string", "null"]},
        "location": {"type": ["string", "null"]},
        "quantity": {"type": ["integer", "null"]},
        "people": {"type": "array", "items": {"type": "object"}},
        "deadlines": {"type": "array"},
        "summary": {"type": "string"},
        "confidence": {"type": "integer"},
        "review_required": {"type": "boolean"},
    },
    "required": ["event_id", "source", "event_type", "summary", "confidence"],
}

raw_json = call_haiku(
    prompt=user_prompt,
    system="You are a structured data extractor. Respond ONLY with valid JSON.",
    output_schema=NORMALIZED_EVENT_SCHEMA,
)
data = json.loads(raw_json)
event = NormalizedEvent(**data)
```

```python
# Approach B: System prompt only (fallback if output_schema not used)
# system prompt must say: "Respond ONLY with valid JSON matching the schema below."
# Then wrap parse in try/except + retry
```

### Pattern 2: NormalizedEvent Model Extension

`NormalizedEvent` (verified from `src/shared/models/events.py`) is missing two fields that MUST be added:

```python
# Add to NormalizedEvent in src/shared/models/events.py
# Source: events.py — model has extra="forbid" so these MUST be in the model
review_required: bool = False
confidence: int = Field(ge=0, le=100, default=50)
```

The model has `extra="forbid"` — any field Haiku returns that is NOT in the Pydantic schema will raise `ValidationError`. The `output_schema` passed to `call_haiku` must match the NormalizedEvent fields exactly. Fields `material` (dict) from the prompt must be FLATTENED to `material_original` and `material_new` because the Pydantic model uses flat fields, not a nested dict.

### Pattern 3: Scope Filter and FilterResult

FilterResult is a Pydantic model defined inline in `scope_filter.py`:

```python
from pydantic import BaseModel, ConfigDict

class FilterResult(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    passed: bool
    reason: str
    escalate_immediately: bool = False
    alert_pm: bool = False

def filter_event(event: NormalizedEvent, project_scope: dict) -> FilterResult:
    # project_scope expected structure:
    # {
    #     "locations": ["3rd floor", "third floor", "floor 3", ...],
    #     "project_id": "demo_project",
    # }
    # Cost threshold for escalation is hardcoded at $50K (not in scope dict)
    ...
```

The `project_scope` dict in Phase 3 is a simple in-code dict with known locations. Cost estimation: check `event.raw_payload` or a `cost_estimate` key if present. If no cost field exists in NormalizedEvent, the filter can check the raw_payload from the originating RawEvent — but since `filter_event` only receives `NormalizedEvent`, the cost check should use a pattern like `event.metadata` or skip cost escalation if no cost data is present. **Decision needed at plan time:** Where does cost come from? NormalizedEvent has no cost field. Resolution: add an optional `estimated_cost: Optional[float] = None` to NormalizedEvent, or check `event.raw_payload` — but NormalizedEvent has no `raw_payload`. The scope filter can set `escalate_immediately=True` only when the change_type or a cost signal is detectable. For Phase 3, the simplest approach: add `estimated_cost: Optional[float] = None` to NormalizedEvent (this also needs to be in the normalization prompt).

### Pattern 4: Router and YAML Loading

```python
# Source: config/settings.py line 29; src/input/pubsub.py pattern
from pathlib import Path
import yaml
from config.settings import settings
from src.shared.models.config import EventTypeConfig

CONFIG_DIR = Path(__file__).parent.parent.parent.parent / "config" / "event_types"

def route_event(event: NormalizedEvent) -> RoutedEvent:
    # 1. Call Haiku with routing prompt
    # 2. Parse event_type from JSON response
    # 3. Load YAML: config_path = CONFIG_DIR / f"{event_type}.yaml"
    # 4. Validate with EventTypeConfig(**yaml_data)
    # 5. Fall back to "other" if YAML missing or parse fails
    # 6. Publish NormalizedEvent to normalized-events topic
    ...
```

EventTypeConfig fields (verified from `src/shared/models/config.py`):

```python
class EventTypeConfig(BaseModel):
    event_type: str                                    # required
    rules_file: str                                    # required
    allowed_signals: list[str] = Field(default_factory=list)
    enrichment_queries: list[str] = Field(default_factory=list)
    time_analysis_enabled: bool = False
```

Minimal valid YAML stub that satisfies EventTypeConfig:

```yaml
event_type: material_change
rules_file: knowledge_folder/rules/demo_project.yaml
allowed_signals: []
enrichment_queries: []
time_analysis_enabled: false
```

### Pattern 5: Pub/Sub Publish for NormalizedEvent

The router must publish the NormalizedEvent to the normalized-events topic. Replicate the `publish_event()` pattern from `src/input/pubsub.py`:

```python
# Source: src/input/pubsub.py lines 31-57
import json
from google.cloud import pubsub_v1
from config.settings import settings

def _publish_normalized_event(event: NormalizedEvent) -> str:
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(
        settings.google_cloud_project,
        settings.pubsub_topic_normalized_events,  # "normalized-events"
    )
    payload = event.model_dump(mode="json")
    data = json.dumps(payload).encode("utf-8")
    future = publisher.publish(topic_path, data, event_type=event.event_type)
    return future.result()  # blocks; raises GoogleAPICallError on failure
```

`settings.pubsub_topic_normalized_events` is already defined in `config/settings.py` line 29 — no modification needed.

### Pattern 6: Tenacity Retry in Normalizer

```python
# Source: src/shared/llm/claude.py lines 28-32 (same pattern)
from tenacity import retry, stop_after_attempt, wait_exponential

# For Pydantic validation failures (not network errors — Haiku retry is in call_haiku itself)
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def _extract_with_retry(prompt: str, system: str, raw_event: RawEvent) -> NormalizedEvent:
    raw_json = call_haiku(prompt, system)
    data = json.loads(raw_json)
    data["event_id"] = raw_event.event_id
    data["source"] = raw_event.source
    return NormalizedEvent(**data)  # raises ValidationError if schema mismatch
```

### Anti-Patterns to Avoid

- **Nested `material` dict in normalization output:** The prompt example shows `material.original` and `material.new` but NormalizedEvent uses `material_original` and `material_new` (flat). Instruct Haiku to use the flat field names in output. OR flatten in the normalizer after parsing. Document this explicitly in the prompt.
- **Importing config.settings at module level in test files:** Must use the autouse fixture + `sys.modules.pop("config.settings", None)` pattern before lazy import. See `tests/unit/test_knowledge_folder.py` lines 26-43.
- **Calling `NormalizedEvent.model_dump(mode="json")` without `mode="json"`:** Will produce Python datetime objects, not ISO strings — breaks JSON serialization for Pub/Sub publish.
- **Using `extra="forbid"` without matching the output_schema exactly:** NormalizedEvent has `extra="forbid"`. Any extra key from Haiku (e.g. a `material` dict key) raises ValidationError.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retry on transient errors | Manual loop + sleep | tenacity (already imported in claude.py) | Handles backoff math, reraise, attempt counting |
| JSON validation from LLM | Manual schema check | Pydantic NormalizedEvent(**data) | Full type coercion + validator methods |
| Guaranteed JSON from LLM | Prompt engineering alone | output_schema in call_haiku | Eliminates markdown preamble, code fences |
| YAML parsing + validation | Custom parser | yaml.safe_load() + EventTypeConfig(**data) | Two-line validated config loading |

**Key insight:** The LLM JSON extraction loop (call → parse → validate → retry) is a well-known pattern. The combination of `output_schema` (for guaranteed JSON) + Pydantic validation (for schema correctness) + tenacity retry (for transient failures) is the correct three-layer defense.

---

## Common Pitfalls

### Pitfall 1: NormalizedEvent `extra="forbid"` With Haiku Output Mismatch

**What goes wrong:** Haiku returns a JSON key that does not exist in NormalizedEvent (e.g., `material` dict, `change_description`, `extracted_fields`). Pydantic raises `ValidationError` immediately.

**Why it happens:** Prompts that show nested structure (e.g., `"material": {"original": "...", "new": "..."}`) cause Haiku to produce nested output. NormalizedEvent has flat fields `material_original`/`material_new`.

**How to avoid:** The normalization prompt MUST use flat field names matching the Pydantic model exactly. Explicitly list every allowed output key. Alternatively, flatten `material.original` → `material_original` in the normalizer before constructing NormalizedEvent.

**Warning signs:** ValidationError mentioning "Extra inputs are not permitted" or "material".

### Pitfall 2: Confidence Field Not Added Before Normalizer

**What goes wrong:** `normalize_event()` tries to set `event.confidence = haiku_confidence` but NormalizedEvent has no `confidence` field. AttributeError or Pydantic ignores it (silently, if extra="allow"). With `extra="forbid"`, ValidationError.

**Why it happens:** NormalizedEvent in `events.py` (current state) has no `confidence` or `review_required` field. These MUST be added before any normalizer code runs.

**How to avoid:** Wave 0 task adds these fields first. Tests against the updated model confirm presence.

**Warning signs:** `ValidationError: Extra inputs are not permitted [confidence]`.

### Pitfall 3: sys.modules Isolation for Settings-Dependent Tests

**What goes wrong:** Tests importing modules that transitively import `config.settings` fail at collection time with `ValidationError` (missing env vars) or use stale module state from a previous test.

**Why it happens:** `config/settings.py` line 43: `settings = Settings()` runs at module import time. If env vars aren't set before the module is first imported, Settings() raises ValidationError immediately.

**How to avoid:** Use the established autouse fixture pattern:

```python
@pytest.fixture(autouse=True)
def _setup_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("VOYAGE_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    for mod in [
        "src.system.data_processing.normalizer",
        "src.system.data_processing.scope_filter",
        "src.system.data_processing.router",
        "src.system.data_processing",
        "config.settings",
    ]:
        sys.modules.pop(mod, None)
```

**Warning signs:** `pydantic_settings.env_settings.SettingsError` or `ValidationError` at test collection time.

### Pitfall 4: Calling `patch("src.system.data_processing.normalizer.call_haiku")` After Module Load

**What goes wrong:** String-based patch misses the already-imported module reference. call_haiku executes for real, hitting the Anthropic API.

**Why it happens:** Module was cached in sys.modules before the patch string path was resolved. See STATE.md: "patch.object for test isolation: When sys.modules is popped between tests, use patch.object(module, 'attr')".

**How to avoid:**
```python
# Correct pattern (from test_claude_client.py, conftest.py):
from src.system.data_processing import normalizer
with patch.object(normalizer, "call_haiku", return_value='{"event_id": ...}'):
    result = normalizer.normalize_event(raw_event)
```

### Pitfall 5: Hardcoding Config Path as Relative String

**What goes wrong:** `open("config/event_types/material_change.yaml")` fails when tests run from a different working directory.

**Why it happens:** `pytest` is usually run from project root but can be run from subdirectories.

**How to avoid:** Use `Path(__file__).parent` anchoring:
```python
CONFIG_DIR = Path(__file__).parent.parent.parent.parent / "config" / "event_types"
```
Or pass config_dir as a parameter to `route_event` for testability.

### Pitfall 6: Deadlines Parsing — Haiku Returns Strings, Not datetimes

**What goes wrong:** NormalizedEvent.deadlines is `list[datetime]`. Haiku returns ISO strings. `NormalizedEvent(deadlines=["2026-04-01"])` will work with Pydantic v2 coercion, but `NormalizedEvent(deadlines=[{"date": "2026-04-01"}])` raises ValidationError.

**Why it happens:** Haiku may produce structured objects for deadline entries if the prompt describes them as objects.

**How to avoid:** Prompt must instruct: `"deadlines": ["ISO 8601 date string", ...]`. Pydantic v2 coerces ISO strings to datetime automatically.

---

## Code Examples

Verified patterns from source files:

### call_haiku with output_schema

```python
# Source: src/shared/llm/claude.py lines 74-110
from src.shared.llm.claude import call_haiku
import json

raw_json = call_haiku(
    prompt="Extract structured data from: ...",
    system="Respond ONLY with valid JSON.",
    output_schema={"type": "object", "properties": {...}, "required": [...]},
)
data = json.loads(raw_json)
```

### NormalizedEvent construction (after adding fields)

```python
# Source: src/shared/models/events.py (with new fields added)
from src.shared.models.events import NormalizedEvent

event = NormalizedEvent(
    event_id="evt-001",
    source="acc",
    event_type="material_change",
    material_original="aluminum",
    material_new="wood",
    location="3rd floor",
    quantity=12,
    people=[{"name": "John Smith", "role": "Project Manager"}],
    deadlines=[],
    summary="Change 12 third-floor windows from aluminum to wood.",
    confidence=85,
    review_required=False,
)
```

### EventTypeConfig YAML loading

```python
# Source: src/shared/models/config.py
import yaml
from src.shared.models.config import EventTypeConfig
from pathlib import Path

config_path = Path("config/event_types/material_change.yaml")
with open(config_path) as f:
    data = yaml.safe_load(f)
config = EventTypeConfig(**data)
# config.event_type == "material_change"
# config.rules_file == "knowledge_folder/rules/demo_project.yaml"
```

### Minimal valid YAML stub (all three event types follow same pattern)

```yaml
# config/event_types/material_change.yaml
event_type: material_change
rules_file: knowledge_folder/rules/demo_project.yaml
allowed_signals: []
enrichment_queries: []
time_analysis_enabled: false
```

### Test isolation pattern for normalizer

```python
# Source: tests/unit/test_claude_client.py pattern + test_knowledge_folder.py autouse
import sys
from unittest.mock import patch
import pytest
from src.shared.models.events import RawEvent

@pytest.fixture(autouse=True)
def _setup_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("VOYAGE_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    for mod in [
        "src.system.data_processing.normalizer",
        "src.system.data_processing",
        "config.settings",
    ]:
        sys.modules.pop(mod, None)

def test_normalize_event_returns_normalized_event():
    from src.system.data_processing import normalizer
    haiku_response = '{"event_id":"e1","source":"acc","event_type":"material_change","material_original":"aluminum","material_new":"wood","location":"3rd floor","quantity":12,"people":[],"deadlines":[],"summary":"Change windows from aluminum to wood.","confidence":85,"review_required":false}'
    with patch.object(normalizer, "call_haiku", return_value=haiku_response):
        from src.shared.models.events import RawEvent
        raw = RawEvent(event_id="e1", source="acc", raw_payload={"text": "change windows"})
        result = normalizer.normalize_event(raw)
    assert result.event_type == "material_change"
    assert result.confidence == 85
    assert result.review_required is False
```

### Publish NormalizedEvent to Pub/Sub

```python
# Source: src/input/pubsub.py pattern
import json
from google.cloud import pubsub_v1
from config.settings import settings

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(
    settings.google_cloud_project,
    settings.pubsub_topic_normalized_events,  # already "normalized-events"
)
payload = event.model_dump(mode="json")  # mode="json" converts datetime → ISO string
data = json.dumps(payload).encode("utf-8")
future = publisher.publish(topic_path, data, event_type=event.event_type)
message_id = future.result()
```

---

## Key Findings From Source Inspection

### Q1: Does NormalizedEvent already have `review_required` and `confidence` fields?

**NO.** Verified from `src/shared/models/events.py` (lines 20-40). Current fields are: `event_id`, `source`, `event_type`, `material_original`, `material_new`, `location`, `quantity`, `people`, `deadlines`, `summary`, `extracted_at`. Both `review_required` and `confidence` are MISSING and must be added as the first task of this phase.

### Q2: What is the exact signature of `call_haiku()` — does it support `output_schema`?

**YES.** Verified from `src/shared/llm/claude.py` lines 74-110. Signature:
```
call_haiku(prompt: str, system: str, output_schema: dict | None = None, max_tokens: int = 4096) -> str
```
When `output_schema` is provided, it passes `output_config = {"format": {"type": "json_schema", "schema": output_schema}}` to `_client.messages.create()`. The docstring explicitly states: "For JSON extraction tasks, instruct: 'Respond ONLY with valid JSON matching the schema below.'"

### Q3: How should the normalization prompt get reliable JSON output from Haiku?

Use `output_schema` in `call_haiku()` for guaranteed JSON. The system prompt should say "Respond ONLY with valid JSON matching the schema below." The prompt body (`normalization.txt`) should: (1) state the task, (2) include the NormalizedEvent JSON schema (with flat field names), (3) provide the demo few-shot example. The output_schema enforces structure; the few-shot example teaches field semantics.

### Q4: What YAML fields does EventTypeConfig require?

Verified from `src/shared/models/config.py`. Required fields: `event_type: str`, `rules_file: str`. Optional with defaults: `allowed_signals: list[str] = []`, `enrichment_queries: list[str] = []`, `time_analysis_enabled: bool = False`. A minimal valid stub needs only `event_type` and `rules_file`.

### Q5: How should the scope filter determine if a location is in-scope?

`project_scope: dict` is passed as a parameter. Phase 3 uses a simple dict. Recommended structure:
```python
{
    "locations": ["3rd floor", "third floor", "floor 3", "lobby", "basement"],
    "project_id": "demo_project",
}
```
Filter logic: `event.location.lower()` in `[loc.lower() for loc in project_scope.get("locations", [])]`. Return `FilterResult(passed=False, reason="Location not in project scope")` if no match. For cost > $50K: NormalizedEvent has no cost field currently — set `escalate_immediately` based on whether `estimated_cost` field (if added) exceeds 50000, or leave cost escalation as always-False for Phase 3.

### Q6: Where should PUBSUB_TOPIC_NORMALIZED_EVENTS be added in settings?

**Already exists.** Verified from `config/settings.py` line 29: `pubsub_topic_normalized_events: str = "normalized-events"`. Also in `.env.example` line 9: `PUBSUB_TOPIC_NORMALIZED_EVENTS=normalized-events`. No changes needed.

### Q7: What test isolation pattern is needed for Haiku calls (mock call_haiku)?

Use `patch.object(module, "call_haiku", return_value=json_string)` — NOT string-based `patch("src.system...")`. Pattern established in `tests/unit/test_claude_client.py` (lines 14-19) using `patch.object(claude, "_client", mock_anthropic_client)`. For normalizer tests: lazy import the module after autouse fixture sets env vars and pops sys.modules, then `patch.object(normalizer, "call_haiku", return_value=...)`.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Prompt-only JSON extraction | `output_schema` in messages.create | Nov 2025 (GA) | Eliminates markdown wrappers, guarantees parse-able JSON |
| `@validator` (Pydantic v1) | `@field_validator` + `@classmethod` (Pydantic v2) | Project decision | All validators in this codebase use v2 API |

**Deprecated/outdated:**
- `@validator` decorator: Raises `PydanticUserError` in this project (v2 only enforced). Use `@field_validator` + `@classmethod`.
- `datetime.utcnow()`: Used in current events.py but is deprecated in Python 3.12+. New fields should use `datetime.now(timezone.utc)` (per STATE.md Calendar decision). Existing `extracted_at` field uses `utcnow()` — leave as-is; new fields should use UTC-aware datetime if added.

---

## Open Questions

1. **Estimated cost field in NormalizedEvent**
   - What we know: Scope filter must escalate cost > $50K. NormalizedEvent has no cost field.
   - What's unclear: Should `estimated_cost: Optional[float] = None` be added to NormalizedEvent? Or is cost escalation deferred to Phase 5?
   - Recommendation: Add `estimated_cost: Optional[float] = None` to NormalizedEvent in the same Wave 0 task that adds `confidence` and `review_required`. Instruct Haiku to extract it in the normalization prompt. Keep it Optional — most events won't have explicit cost data.

2. **Config path resolution in router.py**
   - What we know: Router needs to load `config/event_types/{event_type}.yaml`. Path must be absolute for tests.
   - What's unclear: Should the CONFIG_DIR be a module-level constant using `Path(__file__).parent` or should it be passed as a parameter?
   - Recommendation: Use `Path(__file__).resolve().parent.parent.parent.parent / "config" / "event_types"` as a module-level constant. Also accept an optional `config_dir` parameter in `route_event()` for test overrides.

3. **`other` event type fallback — does `other.yaml` need to exist?**
   - What we know: Router falls back to `other` if classification fails or YAML not found.
   - What's unclear: Should `config/event_types/other.yaml` be created? Or should RoutedEvent handle `config=None` when `event_type="other"`?
   - Recommendation: Create `config/event_types/other.yaml` with minimal fields so `EventTypeConfig` validation always succeeds. RoutedEvent.config should never be None.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing, tests/ directory with conftest.py) |
| Config file | none detected (pytest runs from project root) |
| Quick run command | `pytest tests/unit/test_normalizer.py tests/unit/test_router.py -x -q` |
| Full suite command | `pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PROC-01 | normalization.txt produces valid JSON schema instruction | unit (prompt content) | `pytest tests/unit/test_normalizer.py -x -q` | ❌ Wave 0 |
| PROC-02 | normalize_event() returns NormalizedEvent with correct fields | unit | `pytest tests/unit/test_normalizer.py -x -q` | ❌ Wave 0 (empty) |
| PROC-02 | confidence < 70 sets review_required=True | unit | `pytest tests/unit/test_normalizer.py -x -q` | ❌ Wave 0 |
| PROC-02 | Pydantic failure retries up to 3 times | unit | `pytest tests/unit/test_normalizer.py -x -q` | ❌ Wave 0 |
| PROC-03 | filter_event() rejects out-of-scope location | unit | `pytest tests/unit/test_normalizer.py -x -q` | ❌ Wave 0 |
| PROC-03 | filter_event() escalates cost > $50K | unit | `pytest tests/unit/test_normalizer.py -x -q` | ❌ Wave 0 |
| PROC-04 | routing.txt produces event_type + confidence output | unit (prompt content) | `pytest tests/unit/test_router.py -x -q` | ❌ Wave 0 |
| PROC-05 | route_event() returns RoutedEvent with loaded config | unit | `pytest tests/unit/test_router.py -x -q` | ❌ Wave 0 (empty) |
| PROC-05 | route_event() falls back to "other" when YAML missing | unit | `pytest tests/unit/test_router.py -x -q` | ❌ Wave 0 |
| PROC-05 | route_event() publishes to normalized-events topic | unit | `pytest tests/unit/test_router.py -x -q` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/unit/test_normalizer.py tests/unit/test_router.py -x -q`
- **Per wave merge:** `pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/unit/test_normalizer.py` — covers PROC-01, PROC-02 (file exists but is empty)
- [ ] `tests/unit/test_router.py` — covers PROC-04, PROC-05 (file exists but is empty)
- [ ] No dedicated test file for scope filter — tests for PROC-03 can live in `tests/unit/test_normalizer.py` or a new `tests/unit/test_scope_filter.py`
- [ ] `src/shared/models/events.py` needs `review_required` and `confidence` fields before any test importing NormalizedEvent will work with the new schema

---

## Sources

### Primary (HIGH confidence)
- `src/shared/llm/claude.py` — call_haiku() full signature, output_schema behavior, retry behavior verified
- `src/shared/models/events.py` — NormalizedEvent fields verified (missing review_required and confidence confirmed)
- `src/shared/models/config.py` — EventTypeConfig fields and required fields verified
- `config/settings.py` — pubsub_topic_normalized_events already present confirmed
- `.env.example` — PUBSUB_TOPIC_NORMALIZED_EVENTS entry confirmed
- `tests/unit/test_claude_client.py` — patch.object pattern for Haiku mocking verified
- `tests/unit/test_knowledge_folder.py` — autouse fixture + sys.modules.pop pattern verified
- `tests/conftest.py` — mock_anthropic_client fixture structure verified
- `src/input/pubsub.py` — publish_event() pattern for NormalizedEvent publishing

### Secondary (MEDIUM confidence)
- STATE.md accumulated decisions — project-wide patterns and anti-patterns

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified present in codebase; no new dependencies needed
- Architecture: HIGH — all patterns verified from actual source files
- Pitfalls: HIGH — derived from STATE.md documented lessons and source code inspection
- Model fields: HIGH — directly read from events.py and config.py
- Settings: HIGH — directly read from settings.py and .env.example

**Research date:** 2026-03-13
**Valid until:** 2026-04-13 (stable Python/Pydantic/Anthropic stack)
