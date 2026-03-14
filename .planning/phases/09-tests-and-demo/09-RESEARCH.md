# Phase 9: Tests and Demo - Research

**Researched:** 2026-03-14
**Domain:** pytest testing, FastAPI integration testing, pgvector retrieval quality validation, demo scripting
**Confidence:** HIGH

---

## Summary

Phase 9 is entirely a test and demo authoring phase — no new production source code is written. All implementation modules exist (phases 0-8 are complete). The work is: fill in empty stub files (test fixtures, integration tests, retrieval quality script, demo script), extend coverage of already-passing unit tests where gaps exist, and produce a single stakeholder-runnable `run_demo.py`.

The project already has a mature pytest infrastructure in `pyproject.toml` with markers (`unit`, `integration`, `e2e`, `requires_api`, `requires_db`), `pytest-cov`, `pytest-asyncio`, and `anyio`. The unit test suite is substantially complete — 38+ tests across phases 1-8 already pass. The integration test files (`tests/integration/test_full_pipeline.py`, `test_acc_integration.py`, `test_knowledge_retrieval.py`) and fixture files (`tests/fixtures/*.json`) are empty stubs. `scripts/run_demo.py` and `scripts/test_retrieval_quality.py` are also empty stubs.

The additional context for this phase specifies that unit tests may keep mocks, but integration tests marked `@pytest.mark.integration` MUST use real API connections (no mocking). This is the most important architectural constraint for planning.

**Primary recommendation:** Treat Phase 9 as four parallel work streams: (1) fill JSON fixtures, (2) write real-connection integration tests, (3) build `run_demo.py` trace script, (4) build `test_retrieval_quality.py` recall validator. All work streams can be planned as independent tasks within a single wave.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TEST-01 | Unit tests: normalizer, router, policy_engine, signal_generator, confidence_scorer, retrieval | Already substantially implemented across `tests/unit/`; gaps need identification and filling to reach 80%+ coverage |
| TEST-02 | Integration tests: full pipeline (webhook -> proposal), ACC integration, knowledge retrieval | Empty stubs in `tests/integration/`; require real API credentials from `.env.example` |
| TEST-03 | Test fixtures: sample_transcript.json, sample_acc_event.json, expected_proposal.json | Empty files in `tests/fixtures/`; must match the demo window-substitution scenario exactly |
| TEST-04 | Demo script (run_demo.py): triggers full window-material-substitution pipeline end-to-end | Empty stub at `scripts/run_demo.py`; must print step-by-step trace |
| TEST-05 | Retrieval quality validation script: tests 20+ queries against seeded knowledge folder | Empty stub at `scripts/test_retrieval_quality.py`; reports recall scores |
</phase_requirements>

---

## Standard Stack

### Core (already in pyproject.toml — no new installs needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | >=8.0.0 | Test runner | Project standard, all existing tests use it |
| pytest-cov | >=4.1.0 | Coverage reporting | Already configured in `[tool.coverage.run]` |
| pytest-asyncio | >=0.23.0 | Async test support | Used by async FastAPI route tests |
| httpx | >=0.26.0 | FastAPI TestClient transport | Already imported in existing tests |
| pytest-mock | >=3.12.0 | MagicMock integration | Used throughout existing tests |

### Supporting (already available, no install needed)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| fastapi.testclient | FastAPI built-in | ASGI test client | Integration tests for webhook endpoints |
| unittest.mock | stdlib | Mocking | Unit tests (keep existing pattern) |
| anyio | transitive | Async backend parametrization | Async integration tests |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pytest markers for integration split | separate test directories | Markers already configured in pyproject.toml — use them |
| httpx.AsyncClient | TestClient (sync) | AsyncClient needed for true async integration; TestClient wraps sync for most cases |

**Installation:** No new packages required. All test dependencies are in `pyproject.toml[dev]`.

---

## Architecture Patterns

### Existing Test Structure (must be maintained)

```
tests/
├── conftest.py              # Shared fixtures: mock_anthropic_client, mock_voyage_client, mock_db_conn, test_env, mock_pubsub_publisher
├── unit/                    # Mocked unit tests — all use IMPL_AVAILABLE guard + lazy imports
│   ├── test_normalizer.py   # COMPLETE (3 tests)
│   ├── test_router.py       # COMPLETE (3 tests)
│   ├── test_policy_engine.py
│   ├── test_signal_generator.py  # COMPLETE (11 tests)
│   ├── test_confidence_scorer.py # COMPLETE (7 tests)
│   └── test_retrieval.py    # COMPLETE (9 tests)
├── integration/             # EMPTY STUBS — Phase 9 fills these
│   ├── test_full_pipeline.py     # Real API: POST /webhooks/fireflies -> /api/proposals
│   ├── test_acc_integration.py   # Real ACC API calls
│   └── test_knowledge_retrieval.py  # Real pgvector queries
├── output/                  # COMPLETE (executor, gateway, notification, feedback tests)
├── api/                     # COMPLETE (routes, middleware tests)
└── fixtures/                # EMPTY STUBS — Phase 9 fills these
    ├── sample_transcript.json    # Fireflies demo payload (window substitution)
    ├── sample_acc_event.json     # ACC demo payload
    └── expected_proposal.json    # Expected proposal shape for pipeline test
scripts/
├── run_demo.py              # EMPTY STUB — Phase 9 fills
└── test_retrieval_quality.py    # EMPTY STUB — Phase 9 fills
```

### Pattern 1: IMPL_AVAILABLE Guard (project-established pattern)

**What:** Guards against collection-time failures when implementation files don't exist yet. Uses `Path.exists() + stat().st_size > 10`.
**When to use:** All new unit test files. NOT needed for integration tests (implementations already exist).
**Example:**
```python
# Source: established in tests/unit/test_confidence_scorer.py
_IMPL_PATH = Path(__file__).parent.parent.parent / "src/system/..."
IMPL_AVAILABLE = _IMPL_PATH.exists() and _IMPL_PATH.stat().st_size > 10
```

### Pattern 2: settings singleton isolation (project-established pattern)

**What:** Modules that transitively import `config.settings` must be evicted from `sys.modules` and env vars set before each test.
**When to use:** Any test importing from `src.system.*` or `src.input.*` or `src.output.*`.
**Example:**
```python
# Source: established in tests/unit/test_normalizer.py
@pytest.fixture(autouse=True)
def _setup_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("VOYAGE_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    for mod in ["src.system.data_processing.normalizer", "config.settings"]:
        sys.modules.pop(mod, None)
```

### Pattern 3: Integration tests use real connections (Phase 9 specific)

**What:** `@pytest.mark.integration` tests do NOT use mocks — they connect to actual PostgreSQL, Voyage API, Anthropic API, etc. They require `.env` to be populated with real credentials.
**When to use:** `tests/integration/` only.
**Example:**
```python
# Source: derived from project additional_context and pyproject.toml markers
import pytest

@pytest.mark.integration
@pytest.mark.requires_db
@pytest.mark.requires_api
def test_full_pipeline_returns_proposal():
    """POST sample_transcript.json to /webhooks/fireflies, poll /api/proposals, verify match."""
    ...
```

### Pattern 4: anyio_backend fixture for asyncio-only tests (project-established)

**What:** Prevents anyio from parametrizing over trio when trio is not installed.
**When to use:** Any async test file using anyio.
**Example:**
```python
# Source: established in tests/unit/test_main.py pattern
@pytest.fixture(params=["asyncio"])
def anyio_backend():
    return "asyncio"
```

### Pattern 5: FastAPI TestClient for webhook integration tests

**What:** Use `fastapi.testclient.TestClient` to send HTTP requests against the real `src.main.app` (with only Pub/Sub mocked for unit tests; real connections for integration tests).
**When to use:** `test_full_pipeline.py` uses real FastAPI app.
**Example:**
```python
# Source: established in tests/api/test_routes.py
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)
response = client.post("/webhooks/fireflies", json=fixture_data)
```

### Anti-Patterns to Avoid

- **Using try/except ImportError as IMPL_AVAILABLE guard:** The project uses `Path.exists() + stat().st_size > 10` — `try/except` fails when `config.settings` raises `ValidationError` at import time (not `ImportError`).
- **Module-level imports of settings-dependent modules in test files:** Always lazy-import inside test functions; settings singleton triggers at module load in Python 3.11+.
- **String-based `patch("src.module.attr")` when sys.modules is popped between tests:** Use `patch.object(module, 'attr')` to avoid module identity mismatch.
- **Using `asyncio.run()` in async test functions:** pytest-asyncio manages the event loop — only use `asyncio.run()` in sync helper functions (as seen in `test_executors.py`).
- **Hardcoding expected proposal fields without reading the actual Proposal model:** The `Proposal` model in `src/shared/models/proposals.py` defines the exact shape — `expected_proposal.json` must match it.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Coverage measurement | Custom coverage counter | `pytest-cov --cov=src --cov-report=term-missing` | Already configured in `[tool.coverage.run]` |
| Integration test HTTP client | Custom requests wrapper | `fastapi.testclient.TestClient` or `httpx.AsyncClient` | ASGI-native, handles lifespan events |
| Async test execution | `asyncio.run()` wrappers | `@pytest.mark.anyio` or `@pytest.mark.asyncio` | pytest-asyncio manages loop lifecycle |
| Knowledge folder query evaluation | Custom similarity scorer | pgvector `<=>` operator + Voyage-3 `input_type="query"` | Already implemented in `vector_store.search()` |
| Demo scenario orchestration | Full Pub/Sub roundtrip | Direct Python module calls in sequence | Pub/Sub is async; demo script calls pipeline modules directly for deterministic output |

**Key insight:** The demo script (`run_demo.py`) should NOT try to go through Pub/Sub — it should call pipeline modules directly (`normalize_event()`, `route_event()`, `enrich_event()`, `process_event()`, `generate_proposal()`, `score_proposal()`) in sequence. Pub/Sub is for production async delivery; the demo needs synchronous, traceable execution.

---

## Common Pitfalls

### Pitfall 1: Integration tests requiring real DB with empty knowledge_chunks table

**What goes wrong:** `test_knowledge_retrieval.py` queries pgvector but the database was seeded with no data — all recall scores are 0.
**Why it happens:** Integration tests assume the seed script has been run against the test DB.
**How to avoid:** Integration tests must have a prerequisite note (or autouse fixture) that verifies at least one row exists in `knowledge_chunks` before running — skip with clear message if DB is empty.
**Warning signs:** All recall scores return 0; integration tests pass trivially with wrong assertions.

### Pitfall 2: expected_proposal.json shape mismatch with Proposal model

**What goes wrong:** The fixture contains fields that don't match `src/shared/models/proposals.py` — pipeline test fails with Pydantic ValidationError or comparison fails on field names.
**Why it happens:** Proposal model has specific fields (`proposal_id`, `event_id`, `alert`, `actions`, `confidence_score`, `recommendation`, `created_at`). The fixture must use these exact field names.
**How to avoid:** Generate `expected_proposal.json` from `Proposal.model_json_schema()` or by constructing a real `Proposal` object and calling `.model_dump()`.
**Warning signs:** `KeyError` or `ValidationError` when loading fixture.

### Pitfall 3: sample_transcript.json missing keys required by fireflies webhook

**What goes wrong:** POST to `/webhooks/fireflies` returns 400 because `_REQUIRED_KEYS = {"transcript", "meeting", "meetingId", "id"}` — at least one must be present.
**Why it happens:** Looking at `src/input/webhooks/fireflies.py`, validation checks `_REQUIRED_KEYS.intersection(body.keys())` — needs at least one of those four keys.
**How to avoid:** `sample_transcript.json` must include `"meetingId"`, `"transcript"`, and `"meeting"` keys at minimum.
**Warning signs:** 400 status code from POST to `/webhooks/fireflies` during integration test.

### Pitfall 4: run_demo.py importing settings at module level

**What goes wrong:** Demo script fails immediately with `ValidationError` if env vars aren't set before any imports.
**Why it happens:** `config.settings` singleton triggers at import time.
**How to avoid:** `run_demo.py` must load `.env` via `python-dotenv` (`load_dotenv()`) BEFORE any `src.*` imports. Put all `src.*` imports after `load_dotenv()`.
**Warning signs:** `pydantic_settings.ValidationError` on first line of demo output.

### Pitfall 5: Confidence score discrepancy from demo scenario numbers

**What goes wrong:** `run_demo.py` prints a confidence score that doesn't match the expected 86%.
**Why it happens:** The confidence formula requires `confidence=60` in the NormalizedEvent (not 85 or 95) to produce ~85.5 (`±3` tolerance per STATE.md decision log: "Demo scenario confidence=60 not 95").
**How to avoid:** Demo script must construct the demo NormalizedEvent with `confidence=60` and use historical matches with similarities `[0.92, 0.88, 0.90]` to produce the documented 85.5 score.
**Warning signs:** Demo prints "96% confidence" or "72% confidence" instead of "~86%".

### Pitfall 6: Integration test timeout on full pipeline (5 minute budget)

**What goes wrong:** The pipeline integration test waits for a Pub/Sub message to propagate but there's no consumer running — the test times out.
**Why it happens:** In production, a Pub/Sub subscriber processes messages. In integration tests, there's no subscriber.
**How to avoid:** The pipeline integration test should POST to `/webhooks/fireflies` to validate ingestion, then call the pipeline modules directly (not via Pub/Sub) to simulate the full processing path and check the proposal endpoint. OR, mark this as a manual-only end-to-end test.
**Warning signs:** `TimeoutError` after 5 minutes.

### Pitfall 7: 80% coverage target requiring specific modules

**What goes wrong:** pytest-cov reports 70% because output/notification modules lack unit tests.
**Why it happens:** `tests/output/` tests exist but some code paths (error branches, fallback paths) have no coverage.
**How to avoid:** Run `pytest --cov=src --cov-report=term-missing` during planning to identify which lines are uncovered before writing new tests. Focus new unit tests on uncovered lines, not on re-testing already-covered paths.
**Warning signs:** Coverage report shows specific files at <70% — `src/output/notifications/` is likely lowest.

### Pitfall 8: test_retrieval_quality.py requiring live pgvector + Voyage API

**What goes wrong:** The retrieval quality script fails in CI because no real Voyage API key or DB is available.
**Why it happens:** `vector_store.search()` calls `embed_text()` which calls the real Voyage API.
**How to avoid:** The retrieval quality script is a development-time validation tool, not a pytest test. It lives in `scripts/` not `tests/`. It should use `python-dotenv` to load credentials and clearly document that it requires a seeded DB. Success criteria "at least 18/20 queries" applies to manual runs only.
**Warning signs:** Retrieval quality script is accidentally imported by pytest and causes API errors during automated test runs.

---

## Code Examples

Verified patterns from existing codebase:

### Fireflies fixture format (from webhook validation code)

```python
# Source: src/input/webhooks/fireflies.py — _REQUIRED_KEYS = {"transcript", "meeting", "meetingId", "id"}
# sample_transcript.json must contain at least one of these keys
{
    "meetingId": "meeting-demo-001",
    "id": "transcript-demo-001",
    "meeting": {
        "title": "Construction Site Coordination — 3rd Floor Windows",
        "date": "2026-03-14T09:00:00Z"
    },
    "transcript": "We need to change the third-floor windows from aluminum to wood, 12 units W-301 to W-312.",
    "attendees": [
        {"name": "John Smith", "role": "Project Manager"},
        {"name": "Jane Doe", "role": "Supplier Contact"}
    ]
}
```

### Expected proposal fixture (from Proposal model fields)

```python
# Source: src/shared/models/proposals.py — Proposal fields
# expected_proposal.json must match these field names
{
    "proposal_id": "prop-demo-001",
    "event_id": "evt-demo-001",
    "alert": {
        "title": "Material Substitution: Aluminum to Wood Windows",
        "description": "12 units on 3rd floor (W-301 to W-312)",
        "severity": "medium"
    },
    "actions": [
        {"action_type": "email", "action_data": {"to": "jane@premiumwood.com", "subject": "Window Order"}},
        {"action_type": "task", "action_data": {"title": "Procurement approval", "assignee": "mike@site.com"}},
        {"action_type": "calendar", "action_data": {"summary": "Material review meeting"}},
        {"action_type": "drawing", "action_data": {"drawing_number": "A-301", "annotation_text": "Wood substitution"}}
    ],
    "confidence_score": 0.855,
    "recommendation": "accept"
}
```

### Integration test pattern with real FastAPI app

```python
# Source: derived from tests/api/test_routes.py pattern
import pytest
from fastapi.testclient import TestClient

@pytest.mark.integration
@pytest.mark.requires_db
@pytest.mark.requires_api
class TestFullPipeline:
    def test_webhook_to_proposal(self, tmp_path):
        """POST sample_transcript.json to /webhooks/fireflies — validates ingestion path."""
        import json
        from pathlib import Path
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from src.main import app

        fixture_path = Path(__file__).parent.parent / "fixtures" / "sample_transcript.json"
        payload = json.loads(fixture_path.read_text())

        # Mock Pub/Sub publish only — all other pipeline is real
        with patch("src.input.pubsub.publish_event", return_value="msg-integration-001"):
            client = TestClient(app)
            response = client.post("/webhooks/fireflies", json=payload)

        assert response.status_code == 200
        assert response.json()["status"] == "ok"
```

### Demo script pattern (synchronous pipeline trace)

```python
# Source: derived from pipeline module signatures across phases 3-6
# run_demo.py calls modules directly — does NOT go through Pub/Sub

from dotenv import load_dotenv
load_dotenv()  # MUST be before any src.* imports

from src.shared.models.events import RawEvent
from src.system.data_processing.normalizer import normalize_event
from src.system.data_processing.router import route_event
from src.system.context.enrichment import enrich_event
from src.system.domain_processing.processor import process_event
from src.system.decision_intelligence.proposal_generator import generate_proposal
from src.system.decision_intelligence.confidence_scorer import score_proposal

print("[1/6] Event captured: Fireflies transcript received")
raw = RawEvent(event_id="demo-001", source="fireflies", raw_payload={...})

print("[2/6] Normalizing...")
normalized = normalize_event(raw)
print(f"      material: {normalized.material_original} -> {normalized.material_new}")
# ... continue for each step
```

### Retrieval quality validation pattern

```python
# Source: derived from vector_store.search() signature in src/shared/db/vector_store.py
# scripts/test_retrieval_quality.py

from dotenv import load_dotenv
load_dotenv()

from src.shared.db.vector_store import search

QUERIES = [
    {"query": "wood frame supplier pricing", "expected_source": "knowledge_folder/team_directory"},
    {"query": "material change approval threshold", "expected_source": "knowledge_folder/rules"},
    {"query": "past aluminum to wood window change", "expected_source": "knowledge_folder/historical_patterns"},
    # ... 20+ queries total
]

passed = 0
for item in QUERIES:
    results = search(item["query"], top_k=1)
    if results and results[0]["source"] == item["expected_source"]:
        passed += 1

recall = passed / len(QUERIES)
print(f"Recall: {passed}/{len(QUERIES)} = {recall:.1%}")
assert recall >= 0.90, f"Recall below 90%: {recall:.1%}"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `try/except ImportError` for test guards | `Path.exists() + stat().st_size > 10` | Phase 3 (STATE.md decision log) | Prevents `ValidationError` at collection time |
| String-based `patch("mod.attr")` | `patch.object(module, 'attr')` | Phase 1 (STATE.md decision log) | Module identity stable when sys.modules is popped |
| `datetime.utcnow()` | `datetime.now(timezone.utc)` | Phase 1 (STATE.md decision log) | RFC3339 compliance for Calendar API |
| `@validator` (Pydantic v1) | `@field_validator + @classmethod` (Pydantic v2) | Phase 0 (STATE.md decision log) | PydanticUserError if v1 decorators used |

**Deprecated/outdated in this project:**
- `anyio` parametrizing over `trio`: Project uses `anyio_backend` fixture to restrict to asyncio only — trio is not installed.
- `openai` package: Banned. `anthropic>=0.40.0` only.
- `pytest.mark.skipif(not IMPL_AVAILABLE)` at module level: Used for some tests; the inline `if not IMPL_AVAILABLE: pytest.skip()` pattern is also valid (used in `test_confidence_scorer.py`).

---

## Open Questions

1. **Full pipeline integration test — Pub/Sub consumer**
   - What we know: The integration test must call `POST /webhooks/fireflies` and eventually verify a proposal is generated. Pub/Sub messages are not consumed automatically in tests.
   - What's unclear: Should the pipeline integration test mock Pub/Sub and call normalizer/router/etc. directly in sequence, or should it spin up a real Pub/Sub emulator?
   - Recommendation: Mock Pub/Sub's `publish_event` to return a message ID, then call the processing pipeline directly with the fixture payload. Document this as "pipeline integration test" (not a full end-to-end deployment test). The 5-minute budget in success criteria suggests direct pipeline calls, not async Pub/Sub propagation.

2. **Coverage baseline for 80% target**
   - What we know: Many unit tests exist and pass. The exact current coverage is unknown without running `pytest --cov`.
   - What's unclear: Which specific modules are below 80%? `src/output/notifications/`, `src/output/feedback/`, and `src/api/middleware.py` are candidates.
   - Recommendation: First task in Phase 9 Wave 0 should be running `pytest --cov=src --cov-report=term-missing` to identify gaps before writing new tests.

3. **ACC integration test scope**
   - What we know: `test_acc_integration.py` is an empty stub. ACC API requires real `ACC_CLIENT_ID`, `ACC_CLIENT_SECRET`, `ACC_PROJECT_ID`.
   - What's unclear: Should ACC integration tests hit real ACC or use the stub/mock client in `src/shared/clients/acc.py`? The additional context says "must use real connections."
   - Recommendation: Mark ACC integration tests `@pytest.mark.requires_api` and document that they require real ACC credentials. Provide a skip condition if `ACC_CLIENT_ID` is not set. Test `create_issue()`, `get_floor_plan()`, and `create_drawing_markup()` with real calls.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/unit/ -x -q` |
| Full suite command | `pytest tests/ --cov=src --cov-report=term-missing -q` |
| Integration only | `pytest tests/integration/ -m integration -v` |
| Coverage threshold | `pytest tests/unit/ --cov=src --cov-fail-under=80` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TEST-01 | normalizer, router, policy_engine, signal_generator, confidence_scorer, retrieval unit tests | unit | `pytest tests/unit/test_normalizer.py tests/unit/test_router.py tests/unit/test_policy_engine.py tests/unit/test_signal_generator.py tests/unit/test_confidence_scorer.py tests/unit/test_retrieval.py -v` | Partial — files exist, some may need additional coverage tests |
| TEST-01 | 80%+ code coverage gate | coverage | `pytest tests/unit/ --cov=src --cov-fail-under=80` | Config exists in pyproject.toml |
| TEST-02 | Full pipeline webhook to proposal | integration | `pytest tests/integration/test_full_pipeline.py -m integration -v` | Empty stub — Wave 0 gap |
| TEST-02 | ACC API integration | integration | `pytest tests/integration/test_acc_integration.py -m integration -v` | Empty stub — Wave 0 gap |
| TEST-02 | Knowledge retrieval integration | integration | `pytest tests/integration/test_knowledge_retrieval.py -m integration -v` | Empty stub — Wave 0 gap |
| TEST-03 | Fixture files present and valid JSON | unit (fixture validation) | `pytest tests/unit/test_fixtures.py` (new) | Does not exist — Wave 0 gap |
| TEST-04 | Demo script runs without error | smoke | `python scripts/run_demo.py` (manual) | Empty stub — Wave 0 gap |
| TEST-05 | Retrieval quality 18/20+ | manual | `python scripts/test_retrieval_quality.py` | Empty stub — Wave 0 gap |

### Sampling Rate
- **Per task commit:** `pytest tests/unit/ -x -q`
- **Per wave merge:** `pytest tests/ --cov=src --cov-report=term-missing -q`
- **Phase gate:** `pytest tests/unit/ --cov=src --cov-fail-under=80` green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/fixtures/sample_transcript.json` — must have at least one of `{transcript, meeting, meetingId, id}` keys; covers TEST-03
- [ ] `tests/fixtures/sample_acc_event.json` — ACC webhook payload; covers TEST-03
- [ ] `tests/fixtures/expected_proposal.json` — proposal shape matching `Proposal` Pydantic model; covers TEST-03
- [ ] `tests/integration/test_full_pipeline.py` — pipeline integration test with real FastAPI app; covers TEST-02
- [ ] `tests/integration/test_acc_integration.py` — real ACC API calls; covers TEST-02
- [ ] `tests/integration/test_knowledge_retrieval.py` — real pgvector queries; covers TEST-02
- [ ] `scripts/run_demo.py` — step-by-step trace of window-substitution scenario; covers TEST-04
- [ ] `scripts/test_retrieval_quality.py` — 20+ query recall validation; covers TEST-05
- [ ] Coverage gap analysis (run `pytest --cov` first to identify actual gaps before writing new unit tests for TEST-01)

---

## Sources

### Primary (HIGH confidence)

- Direct codebase inspection: `tests/conftest.py`, `tests/unit/test_normalizer.py`, `tests/unit/test_signal_generator.py`, `tests/unit/test_confidence_scorer.py`, `tests/unit/test_retrieval.py`, `tests/unit/test_router.py` — established test patterns
- `pyproject.toml` `[tool.pytest.ini_options]` and `[tool.coverage.run]` — confirmed framework, markers, coverage config
- `tests/api/test_routes.py`, `tests/output/test_executors.py` — FastAPI TestClient pattern, AsyncMock usage
- `src/input/webhooks/fireflies.py` — `_REQUIRED_KEYS` validation; determines fixture requirements
- `src/shared/models/events.py`, `src/shared/models/proposals.py` — exact field names for fixtures
- `src/system/decision_intelligence/confidence_scorer.py` — demo scenario must produce confidence=60 -> score=85.5
- `.planning/STATE.md` decision log — all project-specific patterns (IMPL_AVAILABLE guard, sys.modules.pop, anyio_backend fixture, patch.object, demo confidence=60)

### Secondary (MEDIUM confidence)

- `scripts/run_demo.py` stub (empty) + `scripts/test_retrieval_quality.py` stub (empty) — confirmed as stubs needing implementation
- `tests/integration/*.py` stubs (empty) — confirmed gap requiring Phase 9 work
- `tests/fixtures/*.json` stubs (empty) — confirmed gap requiring Phase 9 work

### Tertiary (LOW confidence — no external verification performed)

- None. All findings verified directly from project files.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all tools already in pyproject.toml; no new dependencies needed
- Architecture: HIGH — patterns directly inspected from 35+ existing test files; no inference
- Pitfalls: HIGH — derived from STATE.md decision log (documented lessons learned from phases 0-8) + direct code inspection
- Fixtures: HIGH — fixture shape verified against actual Pydantic models and webhook validation code
- Demo script approach: HIGH — Pub/Sub async constraint confirmed by architecture review; direct module call pattern is the only reliable approach

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stable — all frameworks are established project dependencies)
