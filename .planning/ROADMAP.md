# ROADMAP.md — GigAI
## Material Change Coordination Automation System

**Version:** 1.0
**Date:** 2026-03-12
**Granularity:** Fine (10 phases, following CLAUDE_PLAN.md implementation order)
**Total Requirements:** 58 v1 requirements across 10 phases

---

## Phases

- [x] **Phase 0: Foundation** — Project scaffold, shared infrastructure, database schema, LLM/embedding clients, Pydantic models
- [ ] **Phase 1: Input Layer** — All event ingestion endpoints: Fireflies webhook, ACC webhook, Gmail polling, Calendar polling
- [ ] **Phase 2: Knowledge Folder** — Domain context files (glossary, team, rules, historical patterns) embedded into pgvector
- [ ] **Phase 3: Data Processing** — Haiku-powered normalization, scope filtering, and event routing pipeline
- [ ] **Phase 4: Context Enrichment** — ACC API integration and pgvector semantic retrieval for project context and history
- [ ] **Phase 5: Domain Processing** — Config-driven time analysis, policy evaluation, and typed signal generation
- [ ] **Phase 6: Decision Intelligence** — Sonnet 4 proposal generation and weighted confidence scoring
- [ ] **Phase 7: Output + API** — Proposal builder, action gateway with all executors, notifications, feedback loop, FastAPI routes
- [ ] **Phase 8: Dashboard** — React SPA with proposal feed, accept/reject flow, confidence display, audit log
- [ ] **Phase 9: Tests and Demo** — Unit tests, integration tests, fixtures, demo script, retrieval validation

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 0. Foundation | 2/2 | Complete    | 2026-03-12 |
| 1. Input Layer | 1/5 | In progress | - |
| 2. Knowledge Folder | 0/1 | Not started | - |
| 3. Data Processing | 0/1 | Not started | - |
| 4. Context Enrichment | 0/1 | Not started | - |
| 5. Domain Processing | 0/1 | Not started | - |
| 6. Decision Intelligence | 0/1 | Not started | - |
| 7. Output + API | 0/1 | Not started | - |
| 8. Dashboard | 0/1 | Not started | - |
| 9. Tests and Demo | 0/1 | Not started | - |

---

## Phase Details

### Phase 0: Foundation
**Goal**: The system can connect to all infrastructure — database, vector store, LLMs, and embeddings — with all data contracts defined and validated.
**Depends on**: Nothing (first phase)
**Requirements**: FOUND-01, FOUND-02, FOUND-03, FOUND-04, FOUND-05, FOUND-06, FOUND-07, FOUND-08, FOUND-09, FOUND-10
**Success Criteria** (what must be TRUE):
  1. A Python script can open a connection to PostgreSQL, insert a row, and retrieve it using the postgres.py helper.
  2. A Python script can embed a text string via Voyage-3 and perform a cosine similarity search in pgvector using vector_store.py.
  3. A Python script can call Claude Haiku 4.5 and Claude Sonnet 4 via claude.py wrappers and receive valid responses.
  4. A RawEvent, NormalizedEvent, Proposal, Action, Signal, and EventTypeConfig object can be instantiated and validated using the Pydantic models without errors.
  5. The SQL migrations run cleanly and all tables (events, proposals, actions, feedback, past_changes) plus HNSW vector indexes exist in the database.
**Plans**: 2 plans
Plans:
- [x] 00-01-PLAN.md — Scaffold, settings, Pydantic models, SQL migrations, Wave 0 test stubs (FOUND-01, FOUND-06, FOUND-07, FOUND-08, FOUND-09, FOUND-10)
- [x] 00-02-PLAN.md — DB layer (postgres.py, vector_store.py) and LLM clients (claude.py, voyage.py) (FOUND-02, FOUND-03, FOUND-04, FOUND-05)

### Phase 1: Input Layer
**Goal**: External event sources can deliver material change signals to the system and those signals are published to Pub/Sub for downstream processing.
**Depends on**: Phase 0
**Requirements**: INPUT-01, INPUT-02, INPUT-03, INPUT-04
**Success Criteria** (what must be TRUE):
  1. Posting a sample Fireflies webhook payload to POST /webhooks/fireflies results in a message appearing on the raw-events Pub/Sub topic within 5 seconds.
  2. Posting a sample ACC webhook payload to POST /webhooks/acc results in a message on the raw-events topic with the correct source field.
  3. Running the Gmail polling connector against a test inbox with a material-related email publishes that email to the Pub/Sub topic.
  4. Running the Calendar polling connector against a calendar with a delivery event publishes that event to the Pub/Sub topic.
**Plans**: 5 plans
Plans:
- [x] 01-01-PLAN.md — Wave 0: test stubs + add google-api-python-client to requirements.txt (INPUT-01, INPUT-02, INPUT-03, INPUT-04)
- [ ] 01-02-PLAN.md — Shared Pub/Sub publisher helper (src/input/pubsub.py) + infra/pubsub/setup.sh (INPUT-01, INPUT-02, INPUT-03, INPUT-04)
- [ ] 01-03-PLAN.md — Webhook endpoints: POST /webhooks/fireflies and POST /webhooks/acc (INPUT-01, INPUT-02)
- [ ] 01-04-PLAN.md — Polling connectors: poll_gmail() and poll_calendar() (INPUT-03, INPUT-04)
- [ ] 01-05-PLAN.md — FastAPI app wiring: src/main.py with all routers and GET /health (INPUT-01, INPUT-02)

### Phase 2: Knowledge Folder
**Goal**: Project domain knowledge (team, materials, rules, history) is stored in pgvector and retrievable by semantic query.
**Depends on**: Phase 0
**Requirements**: KF-01, KF-02, KF-03, KF-04, KF-05
**Success Criteria** (what must be TRUE):
  1. The glossary file covers all element types, materials, and floor locations referenced in the demo window-substitution scenario (aluminum frames, wood frames, third floor, units W-301 to W-312).
  2. A semantic query for "wood frame supplier" returns the correct supplier contact (Premium Wood Co. / Jane) from the team directory embedded in pgvector.
  3. A semantic query for "material change approval threshold" returns a rule specifying the $50K escalation threshold from the rules file.
  4. A semantic query for "past aluminum to wood window change" returns at least one historical pattern from the historical_patterns file.
  5. The seed script completes without errors and reports the number of chunks embedded for each knowledge folder file.
**Plans**: TBD

### Phase 3: Data Processing
**Goal**: Raw events from Pub/Sub are normalized into structured JSON, validated against project scope, and routed to the correct event-type processing config.
**Depends on**: Phase 1, Phase 2
**Requirements**: PROC-01, PROC-02, PROC-03, PROC-04, PROC-05
**Success Criteria** (what must be TRUE):
  1. Given the demo Fireflies transcript ("change third-floor windows from aluminum to wood, 12 units"), the normalizer outputs a valid NormalizedEvent JSON with material, location, quantity, change_type, and summary fields populated correctly.
  2. An event with extraction confidence below 70% is flagged with a review_required field rather than rejected, and its reason is logged.
  3. An event describing a change at "the neighboring property" is rejected by the scope filter with an out_of_scope reason, and the PM receives an alert for manual review.
  4. An event with estimated cost above $50,000 is escalated immediately with a high_cost flag before further processing.
  5. The router classifies the demo transcript as event_type "material_change" and loads the material_change.yaml config successfully.
**Plans**: TBD

### Phase 4: Context Enrichment
**Goal**: Normalized events are enriched with ACC floor plan data, supplier contacts, and semantically similar historical changes — giving downstream stages everything they need to generate accurate proposals.
**Depends on**: Phase 3
**Requirements**: CTX-01, CTX-02
**Success Criteria** (what must be TRUE):
  1. Given a normalized material change event for "third floor windows", the enrichment module returns the specific unit IDs (W-301 to W-312) retrieved from ACC floor plan data.
  2. The enrichment module retrieves the correct supplier name, pricing, and lead time for wood frames from the knowledge folder via pgvector semantic search.
  3. The historical retrieval module returns at least 3 past events similar to the demo scenario, each with outcome and success rate fields populated.
  4. The enriched event object passes Pydantic validation and contains all fields required by the domain processing stage.
**Plans**: TBD

### Phase 5: Domain Processing
**Goal**: Enriched events are analyzed for time impacts and policy compliance, and produce a typed set of signals that drive action generation.
**Depends on**: Phase 4
**Requirements**: DOM-01, DOM-02, DOM-03, DOM-04, DOM-05, DOM-06, DOM-07
**Success Criteria** (what must be TRUE):
  1. For the demo scenario, the domain processor fires the signals: material_order_required, schedule_update_needed, and drawing_markup_required — matching what a PM would identify manually.
  2. The policy engine loads material_change.yaml and evaluates at least 5 rules, correctly identifying triggered rules for the demo scenario (e.g., quantity > 5 units requires procurement task).
  3. The time analysis module detects a schedule conflict when the demo event's implied lead time (3-4 weeks) overlaps with an existing installation event in the calendar.
  4. Processing the demo enriched event through the full domain processor produces a typed Signal list that passes Pydantic validation.
  5. Stub configs for schedule_update and rfi_request load without errors from their YAML files.
**Plans**: TBD

### Phase 6: Decision Intelligence
**Goal**: Signals and enriched context are synthesized by Claude Sonnet 4 into a complete proposal with four action types and a weighted confidence score.
**Depends on**: Phase 5
**Requirements**: DI-01, DI-02, DI-03
**Success Criteria** (what must be TRUE):
  1. For the demo scenario, the proposal generator produces all four action types: a supplier email to Jane, a procurement task for Mike, a follow-up calendar event, and a drawing markup for drawing A-301.
  2. The confidence scorer calculates a score of approximately 86% for the demo scenario (data clarity 95%, historical match 90%, cost 100%, no red flags 100%) and outputs "Accept" as the recommendation.
  3. A scenario with estimated cost exceeding $50K produces a confidence score below 50% and a "Requires Review" recommendation.
  4. When the Claude API returns an error, the system retries up to 3 times with exponential backoff before failing gracefully with a logged error.
**Plans**: TBD

### Phase 7: Output + API
**Goal**: Approved proposals execute automatically across all external APIs, rejected proposals capture feedback, and the full pipeline is accessible via REST endpoints.
**Depends on**: Phase 6
**Requirements**: OUT-01, OUT-02, OUT-03, OUT-04, OUT-05, OUT-06, OUT-07, OUT-08, OUT-09, OUT-10, OUT-11, OUT-12
**Success Criteria** (what must be TRUE):
  1. Accepting the demo proposal triggers all four executors in parallel: Gmail sends the supplier email, Calendar creates the follow-up event, ACC executor creates the drawing markup, and ACC creates the procurement task — all within 3 minutes of approval.
  2. If one executor fails (e.g., ACC API rate limit), the other executors still complete and the failed action is reported with its specific error in the execution status response.
  3. Rejecting a proposal with a reason stores the decision and reason in PostgreSQL and triggers an embedding of the decision pattern in pgvector via the feedback loop.
  4. GET /api/proposals returns the current proposal list, and POST /api/proposals/:id/decision accepts an accept/reject payload and returns execution status — both within 2 seconds.
  5. The dashboard notifier pushes a real-time notification to connected dashboard clients when a new proposal is created.
**Plans**: TBD

### Phase 8: Dashboard
**Goal**: The PM can view incoming proposals, inspect all proposed actions and confidence details, and accept or reject with a single click from a browser.
**Depends on**: Phase 7
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05
**Success Criteria** (what must be TRUE):
  1. Opening the dashboard in a browser shows a live feed of proposals; the demo proposal appears with its alert summary, confidence score (86%), and recommendation badge visible without scrolling.
  2. Clicking "Accept" on a proposal sends the decision to the backend, disables the buttons, and shows an execution status for each of the four actions (email sent, task created, calendar event added, markup created).
  3. Clicking "Reject" opens a reason input field; submitting stores the rejection and removes the proposal from the active feed.
  4. The AuditLog component shows a chronological history of past decisions with proposal title, decision, confidence score, and timestamp.
  5. The dashboard works correctly on a mobile browser (375px width) — proposal cards are readable and accept/reject buttons are tappable.
**Plans**: TBD

### Phase 9: Tests and Demo
**Goal**: The system is verifiably correct end-to-end, and a single script can demonstrate the complete window-substitution scenario to a stakeholder.
**Depends on**: Phase 8
**Requirements**: TEST-01, TEST-02, TEST-03, TEST-04, TEST-05
**Success Criteria** (what must be TRUE):
  1. Running the unit test suite produces passing results for normalizer, router, policy_engine, signal_generator, confidence_scorer, and retrieval modules with 80%+ code coverage.
  2. The full pipeline integration test (POST sample_transcript.json to /webhooks/fireflies → wait → check proposals endpoint) completes and returns a proposal matching expected_proposal.json within 5 minutes.
  3. Running run_demo.py triggers the complete window-substitution scenario and prints a step-by-step trace showing: event captured → normalized → enriched → signals fired → proposal generated (86% confidence) → ready for PM decision.
  4. The retrieval quality script tests 20+ queries against the seeded knowledge folder and reports recall scores; at least 18/20 queries return the expected top result.
  5. All tests pass in a clean environment using only the .env.example variables and a fresh PostgreSQL database seeded by the seed scripts.
**Plans**: TBD

---

## Coverage Validation

| Phase | Requirements Mapped | Count |
|-------|---------------------|-------|
| Phase 0: Foundation | FOUND-01 through FOUND-10 | 10 |
| Phase 1: Input Layer | INPUT-01 through INPUT-04 | 4 |
| Phase 2: Knowledge Folder | KF-01 through KF-05 | 5 |
| Phase 3: Data Processing | PROC-01 through PROC-05 | 5 |
| Phase 4: Context Enrichment | CTX-01, CTX-02 | 2 |
| Phase 5: Domain Processing | DOM-01 through DOM-07 | 7 |
| Phase 6: Decision Intelligence | DI-01 through DI-03 | 3 |
| Phase 7: Output + API | OUT-01 through OUT-12 | 12 |
| Phase 8: Dashboard | DASH-01 through DASH-05 | 5 |
| Phase 9: Tests and Demo | TEST-01 through TEST-05 | 5 |
| **Total** | | **58/58** |

Coverage: 58/58 requirements mapped. No orphans.
