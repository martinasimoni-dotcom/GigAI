# REQUIREMENTS.md — GigAI

## Version: v1

All requirements below are in scope for the current build (10-phase implementation as defined in CLAUDE_PLAN.md).

---

## FOUND-01 through FOUND-10: Foundation

| ID | Requirement |
|----|-------------|
| FOUND-01 | Python project scaffold: requirements.txt, pyproject.toml, .env.example |
| FOUND-02 | PostgreSQL connection pool with query helpers (postgres.py) |
| FOUND-03 | pgvector integration: embed + retrieve operations (vector_store.py) |
| FOUND-04 | Claude Sonnet 4 and Haiku 4.5 client wrappers (claude.py) |
| FOUND-05 | Voyage-3 embedding client (voyage.py) |
| FOUND-06 | Pydantic v2 models: RawEvent, NormalizedEvent (events.py) |
| FOUND-07 | Pydantic v2 models: Proposal, Action, Signal (proposals.py) |
| FOUND-08 | Pydantic v2 model: EventTypeConfig (config.py) |
| FOUND-09 | SQL migration files: 001_create_tables.sql, 002_create_indexes.sql (HNSW) |
| FOUND-10 | App settings loader from environment variables (settings.py) |

## INPUT-01 through INPUT-04: Input Layer

| ID | Requirement |
|----|-------------|
| INPUT-01 | Fireflies webhook endpoint (POST /webhooks/fireflies): validate payload, publish to Pub/Sub raw-events topic within 5 minutes of meeting end |
| INPUT-02 | ACC webhook endpoint (POST /webhooks/acc): validate payload, publish to Pub/Sub |
| INPUT-03 | Gmail API polling connector: detect material-related emails, publish to Pub/Sub |
| INPUT-04 | Google Calendar polling connector: detect delivery/installation events, publish to Pub/Sub |

## KF-01 through KF-05: Knowledge Folder

| ID | Requirement |
|----|-------------|
| KF-01 | Glossary file: element types, materials, locations for demo building (demo_project.md) |
| KF-02 | Team directory: 6-8 team members with roles, contacts, responsibilities (demo_project.json) |
| KF-03 | Rules file: 15-20 rules covering material change approvals, thresholds, escalations (demo_project.yaml) |
| KF-04 | Historical patterns: 10-15 past material change events with outcomes (demo_project.json) |
| KF-05 | Seed script: chunk, embed via Voyage-3, store in pgvector (seed_knowledge_folder.py) |

## PROC-01 through PROC-05: Data Processing

| ID | Requirement |
|----|-------------|
| PROC-01 | Haiku normalization prompt: extract material, location, quantity, people, deadlines, change_type, summary → valid JSON matching NormalizedEvent schema |
| PROC-02 | Normalizer module: calls Haiku, validates output with Pydantic, flags extraction confidence <70% for manual review |
| PROC-03 | Scope filter: validates event against ACC project scope, rejects out-of-scope changes, escalates cost >$50K immediately |
| PROC-04 | Haiku routing prompt: classify event into known event_type string mapping to a YAML config |
| PROC-05 | Router module: calls Haiku for classification, loads matching config from config/event_types/, publishes to normalized-events topic |

## CTX-01 through CTX-02: Context Enrichment

| ID | Requirement |
|----|-------------|
| CTX-01 | Context enrichment module: fetches floor plans and project data from ACC API, retrieves relevant knowledge chunks via Voyage-3 + pgvector semantic search, outputs enriched event |
| CTX-02 | Historical retrieval module: semantic search for similar past events in pgvector, returns top 5 matches with outcomes and success rate |

## DOM-01 through DOM-07: Domain Processing

| ID | Requirement |
|----|-------------|
| DOM-01 | Event type config: material_change.yaml — full config with rules, signal types, enrichment queries |
| DOM-02 | Event type config stubs: schedule_update.yaml, rfi_request.yaml |
| DOM-03 | Time analysis module: dateutil-based temporal reasoning, cross-references ACC schedule for conflicts |
| DOM-04 | Policy engine: loads YAML rules per event type, evaluates conditions, identifies triggered rules |
| DOM-05 | Signal generator: outputs typed signals (material_order_required, schedule_update_needed, drawing_markup_required, etc.) per config allowed set |
| DOM-06 | Domain processor orchestrator: runs time analysis, policy engine, signal generator with loaded config |
| DOM-07 | Haiku routing prompt written and tested; event_types configs validated against Pydantic EventTypeConfig schema |

## DI-01 through DI-03: Decision Intelligence

| ID | Requirement |
|----|-------------|
| DI-01 | Sonnet 4 proposal prompt: receives enriched context + signals + rules, outputs structured JSON with event_summary, affected_stakeholders, recommended_actions, confidence_rationale |
| DI-02 | Proposal generator: calls Sonnet 4 with context and signals, validates output with Pydantic, retries on error (3 attempts with exponential backoff) |
| DI-03 | Confidence scorer: weighted formula (data clarity 30%, historical match 25%, cost acceptable 25%, no red flags 20%), outputs 0-100% score with breakdown and recommendation (accept >80%, review 50-80%, reject <50%) |

## OUT-01 through OUT-12: Output Layer and API

| ID | Requirement |
|----|-------------|
| OUT-01 | Proposal builder: formats proposal (alert + actions + confidence score + recommendation) for dashboard consumption |
| OUT-02 | Action gateway: routes approved actions to appropriate executors in parallel, reports execution status per action, handles partial failures gracefully |
| OUT-03 | ACC executor: creates RFIs, tasks, issues, and drawing markups via ACC API |
| OUT-04 | Gmail executor: sends stakeholder notification and supplier emails via Gmail API |
| OUT-05 | Calendar executor: creates follow-up calendar events via Google Calendar API |
| OUT-06 | Document executor: adds markups to ACC drawings via ACC Document/Markup API |
| OUT-07 | Dashboard notifier: pushes real-time proposal notifications to dashboard (primary channel) |
| OUT-08 | ACC notifier: sends secondary notifications via ACC notifications API |
| OUT-09 | Email notifier: sends fallback email alerts when dashboard is unavailable |
| OUT-10 | Feedback loop: logs all PM decisions (accept/reject + reason) to PostgreSQL, embeds decisions as historical patterns in pgvector |
| OUT-11 | FastAPI routes: all REST endpoints (proposals, decisions, feedback, health) |
| OUT-12 | FastAPI middleware: authentication, CORS, structured error handling |

## DASH-01 through DASH-05: Dashboard

| ID | Requirement |
|----|-------------|
| DASH-01 | React + Vite + Tailwind project setup in dashboard/ |
| DASH-02 | API client utility (api.js): handles all backend calls |
| DASH-03 | Proposal components: ProposalCard (accept/reject), ProposalFeed (real-time list), ConfidenceIndicator, ActionPreview, AuditLog |
| DASH-04 | React hooks: useProposals (fetch + poll), useActions (approve/reject) |
| DASH-05 | App.jsx: wires all components into working SPA with proposal feed and decision flow |

## TEST-01 through TEST-05: Tests and Demo

| ID | Requirement |
|----|-------------|
| TEST-01 | Unit tests: normalizer, router, policy_engine, signal_generator, confidence_scorer, retrieval |
| TEST-02 | Integration tests: full pipeline (webhook → proposal), ACC integration, knowledge retrieval |
| TEST-03 | Test fixtures: sample_transcript.json (Fireflies demo), sample_acc_event.json, expected_proposal.json |
| TEST-04 | Demo script (run_demo.py): triggers full window-material-substitution pipeline end-to-end |
| TEST-05 | Retrieval quality validation script: tests 20+ queries against seeded knowledge folder |

---

## Summary

| Category | Count |
|----------|-------|
| Foundation (FOUND) | 10 |
| Input Layer (INPUT) | 4 |
| Knowledge Folder (KF) | 5 |
| Data Processing (PROC) | 5 |
| Context Enrichment (CTX) | 2 |
| Domain Processing (DOM) | 7 |
| Decision Intelligence (DI) | 3 |
| Output + API (OUT) | 12 |
| Dashboard (DASH) | 5 |
| Tests + Demo (TEST) | 5 |
| **Total v1** | **58** |

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | Phase 0 | Complete |
| FOUND-02 | Phase 0 | Complete |
| FOUND-03 | Phase 0 | Complete |
| FOUND-04 | Phase 0 | Complete |
| FOUND-05 | Phase 0 | Complete |
| FOUND-06 | Phase 0 | Complete |
| FOUND-07 | Phase 0 | Complete |
| FOUND-08 | Phase 0 | Complete |
| FOUND-09 | Phase 0 | Complete |
| FOUND-10 | Phase 0 | Complete |
| INPUT-01 | Phase 1 | Pending |
| INPUT-02 | Phase 1 | Pending |
| INPUT-03 | Phase 1 | Pending |
| INPUT-04 | Phase 1 | Pending |
| KF-01 | Phase 2 | Pending |
| KF-02 | Phase 2 | Pending |
| KF-03 | Phase 2 | Pending |
| KF-04 | Phase 2 | Pending |
| KF-05 | Phase 2 | Pending |
| PROC-01 | Phase 3 | Pending |
| PROC-02 | Phase 3 | Pending |
| PROC-03 | Phase 3 | Pending |
| PROC-04 | Phase 3 | Pending |
| PROC-05 | Phase 3 | Pending |
| CTX-01 | Phase 4 | Pending |
| CTX-02 | Phase 4 | Pending |
| DOM-01 | Phase 5 | Pending |
| DOM-02 | Phase 5 | Pending |
| DOM-03 | Phase 5 | Pending |
| DOM-04 | Phase 5 | Pending |
| DOM-05 | Phase 5 | Pending |
| DOM-06 | Phase 5 | Pending |
| DOM-07 | Phase 5 | Pending |
| DI-01 | Phase 6 | Pending |
| DI-02 | Phase 6 | Pending |
| DI-03 | Phase 6 | Pending |
| OUT-01 | Phase 7 | Pending |
| OUT-02 | Phase 7 | Pending |
| OUT-03 | Phase 7 | Pending |
| OUT-04 | Phase 7 | Pending |
| OUT-05 | Phase 7 | Pending |
| OUT-06 | Phase 7 | Pending |
| OUT-07 | Phase 7 | Pending |
| OUT-08 | Phase 7 | Pending |
| OUT-09 | Phase 7 | Pending |
| OUT-10 | Phase 7 | Pending |
| OUT-11 | Phase 7 | Pending |
| OUT-12 | Phase 7 | Pending |
| DASH-01 | Phase 8 | Pending |
| DASH-02 | Phase 8 | Pending |
| DASH-03 | Phase 8 | Pending |
| DASH-04 | Phase 8 | Pending |
| DASH-05 | Phase 8 | Pending |
| TEST-01 | Phase 9 | Pending |
| TEST-02 | Phase 9 | Pending |
| TEST-03 | Phase 9 | Pending |
| TEST-04 | Phase 9 | Pending |
| TEST-05 | Phase 9 | Pending |
