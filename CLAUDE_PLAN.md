# CLAUDE.md — GigAI Implementation Guide

## What Is GigAI

GigAI is an event-driven coordination automation system for construction project managers. It monitors project activity (meeting transcripts, emails, ACC updates, calendar changes), processes events through an AI pipeline, generates coordination proposals, and executes approved actions via external APIs.

**Demo scenario:** Window material substitution — Aluminum → Wood, 3rd Floor, 12 Units.

## Architecture Overview

The system follows a strict INPUT → SYSTEM → OUTPUT pipeline:

```
INPUT (Data Ingestion)
├── Fireflies webhook (meeting transcripts)
├── ACC API webhook (project changes)
├── Gmail API polling (emails)
├── Calendar API polling (calendar events)
└── All events → Google Cloud Pub/Sub

SYSTEM (Processing Pipeline)
├── Data Processing (steps 1-3)
│   ├── Event Normalization — Haiku 4.5 parses raw → structured JSON
│   ├── Security & Scope Filter — validates against project scope
│   └── Event Routing — Haiku classifies type → loads config set
├── Context (steps 4-5)
│   ├── Context Enrichment — ACC API + knowledge folder retrieval
│   └── Historical Retrieval — pgvector semantic search for past events
├── Domain Processing (steps 6-8) — SAME CODE, CONFIG-DRIVEN BEHAVIOR
│   ├── Time Analysis — scheduling/temporal reasoning per event config
│   ├── Policy/Rules Engine — loads rule set per event type from YAML
│   └── Signal Generation — outputs signals from allowed set per type
└── Decision Intelligence (steps 9-10)
    ├── Proposal Generation — Claude Sonnet 4 structured output
    └── Confidence Scoring — weighted heuristic, >80% threshold

OUTPUT (Execution)
├── Proposal Builder — formats for PM review
├── PM Decision — accept/reject in dashboard
├── Action Gateway — routes to API executors
│   ├── ACC API — RFIs, tasks, issues, markups, documents
│   ├── Gmail API — stakeholder notifications
│   ├── Calendar API — schedule updates
│   └── Document APIs — ACC markup, review requests
├── Notifications — dashboard (primary), ACC notif (secondary), email (fallback)
└── Feedback & Learning — logs decisions, embeds as historical patterns
```

## Technology Stack

| Component | Technology | Notes |
|-----------|-----------|-------|
| Runtime | Python 3.11 + FastAPI | Async-native |
| LLM (heavy) | Claude Sonnet 4 (`claude-sonnet-4-20250514`) | Proposals, action generation |
| LLM (light) | Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) | Normalization, routing |
| Embeddings | Voyage-3 (`voyage-3`) | 1024-dim, Anthropic ecosystem |
| Database | PostgreSQL 15 + pgvector | Structured + vector storage |
| Event Bus | Google Cloud Pub/Sub | At-least-once delivery |
| Compute | Google Cloud Functions (2nd gen) | Event-triggered |
| API Server | FastAPI on Cloud Run | Dashboard API |
| Dashboard | React + Vite + Tailwind | SPA |
| Validation | Pydantic v2 | Schema enforcement |
| Orchestration | LangChain | Retrieval chains |

## Critical Design Rules

1. **Event routing is LLM-classified, config-driven.** Haiku classifies the event type. The classification loads a configuration set (rules, signal types, enrichment queries). The pipeline code is the same for all events — only the config changes behavior.

2. **No fine-tuned models.** All intelligence comes from Claude + knowledge folder RAG. No spaCy, no Phi-3, no training steps.

3. **No Claude Vision.** Floor plan annotation is NOT done via vision LLM. Drawing markups go through ACC's markup API.

4. **Human-in-the-loop.** Every proposal requires PM approval before execution. High confidence (>80%) = auto-propose to PM. Low confidence = flag for human decision. Nothing executes without approval.

5. **Knowledge folder is the domain grounding.** The knowledge_folder/ directory contains all project-specific context. Claude receives relevant chunks in its prompt via RAG retrieval. Without this context, proposals will be generic and wrong.

6. **All actions execute via external APIs.** GigAI does not modify ACC UI, does not store project data permanently (only coordination state), does not replace ACC.

## File Structure

```
gigai/
├── CLAUDE.md                          # THIS FILE — read first
├── README.md                          # Setup and run instructions
├── PRD.md                             # Full product requirements
├── requirements.txt                   # Python dependencies
├── .env.example                       # Environment variables template
├── pyproject.toml                     # Python project config
│
├── src/
│   ├── main.py                        # FastAPI app entrypoint
│   ├── __init__.py
│   │
│   ├── input/                         # INPUT LAYER
│   │   ├── __init__.py
│   │   ├── webhooks/
│   │   │   ├── __init__.py
│   │   │   ├── fireflies.py           # POST /webhooks/fireflies
│   │   │   └── acc.py                 # POST /webhooks/acc
│   │   └── connectors/
│   │       ├── __init__.py
│   │       ├── gmail.py               # Gmail API polling
│   │       └── calendar.py            # Calendar API polling
│   │
│   ├── system/                        # SYSTEM LAYER
│   │   ├── __init__.py
│   │   ├── data_processing/
│   │   │   ├── __init__.py
│   │   │   ├── normalizer.py          # Step 1: Haiku LLM parsing → structured JSON
│   │   │   ├── scope_filter.py        # Step 2: Security & scope validation
│   │   │   └── router.py              # Step 3: Haiku classification → config loader
│   │   ├── context/
│   │   │   ├── __init__.py
│   │   │   ├── enrichment.py          # Step 4: ACC API + knowledge folder retrieval
│   │   │   └── historical.py          # Step 5: pgvector past event retrieval
│   │   ├── domain_processing/
│   │   │   ├── __init__.py
│   │   │   ├── processor.py           # Steps 6-8: Main processor (config-driven)
│   │   │   ├── time_analysis.py       # Step 6: Temporal reasoning
│   │   │   ├── policy_engine.py       # Step 7: YAML rule evaluation
│   │   │   └── signal_generator.py    # Step 8: Typed signal output
│   │   └── decision_intelligence/
│   │       ├── __init__.py
│   │       ├── proposal_generator.py  # Step 9: Claude Sonnet 4 proposal
│   │       └── confidence_scorer.py   # Step 10: Weighted heuristic
│   │
│   ├── output/                        # OUTPUT LAYER
│   │   ├── __init__.py
│   │   ├── proposal_builder/
│   │   │   ├── __init__.py
│   │   │   └── builder.py             # Format proposals for PM
│   │   ├── action_gateway/
│   │   │   ├── __init__.py
│   │   │   ├── gateway.py             # Route approved actions to executors
│   │   │   ├── acc_executor.py        # ACC API: RFIs, tasks, issues, markups
│   │   │   ├── gmail_executor.py      # Gmail API: stakeholder emails
│   │   │   ├── calendar_executor.py   # Calendar API: schedule events
│   │   │   └── document_executor.py   # ACC Document API: markups, reviews
│   │   ├── notifications/
│   │   │   ├── __init__.py
│   │   │   ├── dashboard_notifier.py  # Primary: real-time to dashboard
│   │   │   ├── acc_notifier.py        # Secondary: ACC notifications
│   │   │   └── email_notifier.py      # Fallback: email alerts
│   │   └── feedback/
│   │       ├── __init__.py
│   │       └── feedback_loop.py       # Log decisions, embed as patterns
│   │
│   ├── shared/                        # SHARED UTILITIES
│   │   ├── __init__.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── events.py              # NormalizedEvent, RawEvent Pydantic models
│   │   │   ├── proposals.py           # Proposal, Action, Signal models
│   │   │   └── config.py              # EventTypeConfig model
│   │   ├── llm/
│   │   │   ├── __init__.py
│   │   │   ├── claude.py              # Claude Sonnet 4 + Haiku 4.5 clients
│   │   │   └── voyage.py              # Voyage-3 embedding client
│   │   └── db/
│   │       ├── __init__.py
│   │       ├── postgres.py            # PostgreSQL connection + queries
│   │       └── vector_store.py        # pgvector operations
│   │
│   └── api/                           # API ENDPOINTS
│       ├── __init__.py
│       ├── routes.py                  # All FastAPI routes
│       └── middleware.py              # Auth, CORS, error handling
│
├── knowledge_folder/                  # DOMAIN CONTEXT (per project)
│   ├── glossary/
│   │   └── demo_project.md            # Element types, materials, locations
│   ├── team_directory/
│   │   └── demo_project.json          # Team members, roles, contacts
│   ├── rules/
│   │   └── demo_project.yaml          # Approval thresholds, policies
│   └── historical_patterns/
│       └── demo_project.json          # Past changes, PM decisions
│
├── config/
│   ├── settings.py                    # App settings (env vars)
│   ├── event_types/
│   │   ├── material_change.yaml       # Full config for demo
│   │   ├── schedule_update.yaml       # Stub config
│   │   └── rfi_request.yaml           # Stub config
│   └── prompts/
│       ├── normalization.txt          # Haiku normalization prompt
│       ├── routing.txt                # Haiku routing prompt
│       └── proposal.txt               # Sonnet 4 proposal prompt
│
├── tests/
│   ├── conftest.py                    # Shared fixtures
│   ├── unit/
│   │   ├── test_normalizer.py
│   │   ├── test_router.py
│   │   ├── test_policy_engine.py
│   │   ├── test_signal_generator.py
│   │   ├── test_confidence_scorer.py
│   │   └── test_retrieval.py
│   ├── integration/
│   │   ├── test_full_pipeline.py      # End-to-end: webhook → proposal
│   │   ├── test_acc_integration.py
│   │   └── test_knowledge_retrieval.py
│   └── fixtures/
│       ├── sample_transcript.json     # Fireflies demo transcript
│       ├── sample_acc_event.json      # ACC webhook payload
│       └── expected_proposal.json     # Expected output for demo
│
├── scripts/
│   ├── seed_knowledge_folder.py       # Load knowledge folder into pgvector
│   ├── seed_demo_data.py             # Seed ACC + DB for demo
│   ├── run_demo.py                   # Trigger full demo pipeline
│   └── test_retrieval_quality.py     # Validate retrieval on 20+ queries
│
├── infra/
│   ├── sql/
│   │   ├── 001_create_tables.sql      # Core schema
│   │   └── 002_create_indexes.sql     # pgvector HNSW indexes
│   ├── pubsub/
│   │   └── setup.sh                   # Create topics + subscriptions
│   └── cloud_run/
│       ├── Dockerfile                 # FastAPI container
│       └── cloudbuild.yaml            # Cloud Build config
│
└── dashboard/                         # REACT SPA
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    ├── index.html
    ├── public/
    └── src/
        ├── App.jsx                    # Main app with proposal feed
        ├── main.jsx                   # Entry point
        ├── components/
        │   ├── ProposalCard.jsx       # Single proposal with accept/reject
        │   ├── ProposalFeed.jsx       # Real-time proposal list
        │   ├── ConfidenceIndicator.jsx
        │   ├── ActionPreview.jsx      # Preview actions before approval
        │   └── AuditLog.jsx           # Decision history
        ├── hooks/
        │   ├── useProposals.js        # Fetch + poll proposals
        │   └── useActions.js          # Execute approve/reject
        └── utils/
            └── api.js                 # API client
```

## Implementation Order

Follow this exact sequence. Each phase depends on the previous.

### Phase 0: Foundation
1. Set up `requirements.txt`, `pyproject.toml`, `.env.example`
2. Implement `src/shared/db/postgres.py` — connection pool, query helpers
3. Implement `src/shared/db/vector_store.py` — pgvector embed + retrieve
4. Implement `src/shared/llm/claude.py` — Sonnet 4 + Haiku 4.5 client wrappers
5. Implement `src/shared/llm/voyage.py` — Voyage-3 embedding client
6. Implement `src/shared/models/events.py` — RawEvent, NormalizedEvent Pydantic models
7. Implement `src/shared/models/proposals.py` — Proposal, Action, Signal models
8. Implement `src/shared/models/config.py` — EventTypeConfig model
9. Create `infra/sql/001_create_tables.sql` and `002_create_indexes.sql`
10. Implement `config/settings.py` — load env vars

### Phase 1: Input Layer
1. Implement `src/input/webhooks/fireflies.py` — FastAPI POST endpoint, validate, publish to Pub/Sub
2. Implement `src/input/webhooks/acc.py` — FastAPI POST endpoint for ACC webhooks
3. Implement `src/input/connectors/gmail.py` — polling function
4. Implement `src/input/connectors/calendar.py` — polling function
5. Wire all into `src/main.py`

### Phase 2: Knowledge Folder
1. Write `knowledge_folder/glossary/demo_project.md` — all element types, materials, locations for the demo building
2. Write `knowledge_folder/team_directory/demo_project.json` — 6-8 team members
3. Write `knowledge_folder/rules/demo_project.yaml` — 15-20 rules for material changes
4. Write `knowledge_folder/historical_patterns/demo_project.json` — 10-15 past events
5. Implement `scripts/seed_knowledge_folder.py` — chunk, embed, store in pgvector

### Phase 3: Data Processing
1. Write `config/prompts/normalization.txt` — Haiku prompt for raw → structured
2. Write `config/prompts/routing.txt` — Haiku prompt for event classification
3. Implement `src/system/data_processing/normalizer.py` — calls Haiku, validates with Pydantic
4. Implement `src/system/data_processing/scope_filter.py` — checks against ACC project scope
5. Implement `src/system/data_processing/router.py` — calls Haiku for classification, loads matching config from `config/event_types/`

### Phase 4: Context
1. Implement `src/system/context/enrichment.py` — ACC API calls + knowledge chunk retrieval via Voyage-3 + pgvector
2. Implement `src/system/context/historical.py` — semantic search for similar past events

### Phase 5: Domain Processing
1. Write `config/event_types/material_change.yaml` — full config (rules, signal types, enrichment queries)
2. Write `config/event_types/schedule_update.yaml` — stub
3. Write `config/event_types/rfi_request.yaml` — stub
4. Implement `src/system/domain_processing/time_analysis.py` — dateutil + ACC schedule cross-ref
5. Implement `src/system/domain_processing/policy_engine.py` — load YAML rules, evaluate
6. Implement `src/system/domain_processing/signal_generator.py` — output typed signals per config
7. Implement `src/system/domain_processing/processor.py` — orchestrator that runs all three with loaded config

### Phase 6: Decision Intelligence
1. Write `config/prompts/proposal.txt` — Sonnet 4 prompt with structured output schema
2. Implement `src/system/decision_intelligence/proposal_generator.py` — Sonnet 4 call with context + signals
3. Implement `src/system/decision_intelligence/confidence_scorer.py` — weighted formula

### Phase 7: Output
1. Implement `src/output/proposal_builder/builder.py` — format proposals for dashboard
2. Implement `src/output/action_gateway/gateway.py` — route approved actions
3. Implement `src/output/action_gateway/acc_executor.py` — ACC API calls (RFIs, tasks, issues, markups)
4. Implement `src/output/action_gateway/gmail_executor.py` — send emails
5. Implement `src/output/action_gateway/calendar_executor.py` — create events
6. Implement `src/output/action_gateway/document_executor.py` — ACC markup API
7. Implement `src/output/notifications/dashboard_notifier.py`
8. Implement `src/output/notifications/acc_notifier.py`
9. Implement `src/output/notifications/email_notifier.py`
10. Implement `src/output/feedback/feedback_loop.py` — log + embed decisions
11. Implement `src/api/routes.py` — all REST endpoints
12. Implement `src/api/middleware.py` — auth, CORS

### Phase 8: Dashboard
1. Set up React + Vite + Tailwind in `dashboard/`
2. Implement `dashboard/src/utils/api.js`
3. Implement all components: ProposalCard, ProposalFeed, ConfidenceIndicator, ActionPreview, AuditLog
4. Implement hooks: useProposals, useActions
5. Wire into App.jsx

### Phase 9: Tests & Demo
1. Write all unit tests
2. Write integration tests
3. Create test fixtures (sample_transcript.json, expected_proposal.json)
4. Implement `scripts/run_demo.py`
5. Implement `scripts/test_retrieval_quality.py`

## Prompt Templates

### Normalization prompt (Haiku 4.5)
The normalization prompt must instruct Haiku to extract: material, location, change_type, original_material, new_material, quantity, people (with roles if mentioned), deadlines, and a one-sentence summary. Output must be valid JSON matching the NormalizedEvent Pydantic schema.

### Routing prompt (Haiku 4.5)
The routing prompt must instruct Haiku to classify the event into one of the known event types by analyzing the normalized content. It returns the event_type string which maps to a YAML config file in config/event_types/.

### Proposal prompt (Sonnet 4)
The proposal prompt receives: enriched context (knowledge chunks + ACC data + historical matches) + fired signals + triggered rules. It must output a structured JSON proposal with: event_summary, affected_stakeholders[], recommended_actions[], confidence_rationale. The prompt includes the output JSON schema.

## Key Constraints

- **Anthropic SDK:** Use `anthropic` Python package. Model strings: `claude-sonnet-4-20250514`, `claude-haiku-4-5-20251001`
- **Voyage SDK:** Use `voyageai` Python package. Model string: `voyage-3`
- **pgvector:** Use `pgvector` Python package with psycopg2. Vector column type: `vector(1024)`
- **No OpenAI anywhere.** Not for embeddings, not for LLM calls, not for anything.
- **No spaCy, no Phi-3, no model training.** All NLP is Claude API calls + knowledge folder RAG.
- **No Claude Vision.** Drawing markups go through ACC markup API.
- **Pydantic v2** for all data validation. Every boundary between pipeline stages validates with Pydantic.
- **YAML for rules.** Project rules in `knowledge_folder/rules/` and event configs in `config/event_types/` are YAML.
- **All secrets in .env.** Never hardcode API keys.
