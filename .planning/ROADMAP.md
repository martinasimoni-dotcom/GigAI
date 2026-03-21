# ROADMAP.md — GigAI
## v1.0 Material Change Coordination (Complete) + v2.0 Communication Intelligence

**Version:** 2.0
**Date:** 2026-03-21
**Granularity:** Standard (7 phases, starting Phase 10)
**Total v2.0 Requirements:** 37 requirements across 7 categories

---

## v1.0 Phases (Complete — reference only)

- [x] **Phase 0: Foundation** — Project scaffold, shared infrastructure, database schema, LLM/embedding clients, Pydantic models
- [x] **Phase 1: Input Layer** — All event ingestion endpoints: Fireflies webhook, ACC webhook, Gmail polling, Calendar polling
- [x] **Phase 2: Knowledge Folder** — Domain context files embedded into pgvector (completed 2026-03-13)
- [x] **Phase 3: Data Processing** — Haiku-powered normalization, scope filtering, and event routing pipeline (completed 2026-03-13)
- [x] **Phase 4: Context Enrichment** — ACC API integration and pgvector semantic retrieval (completed 2026-03-13)
- [x] **Phase 5: Domain Processing** — Config-driven time analysis, policy evaluation, typed signal generation (completed 2026-03-13)
- [x] **Phase 6: Decision Intelligence** — Sonnet 4 proposal generation and weighted confidence scoring (completed 2026-03-13)
- [x] **Phase 7: Output + API** — Proposal builder, action gateway, notifications, feedback loop, FastAPI routes (completed 2026-03-14)
- [x] **Phase 8: Dashboard** — React SPA with proposal feed, accept/reject flow, confidence display, audit log (completed 2026-03-14)
- [x] **Phase 9: Tests and Demo** — Unit tests, integration tests, fixtures, demo script (completed 2026-03-14)

---

## v2.0 Phases

- [ ] **Phase 10: Unified Inbox** — Ingest all project communications into a single classified and routed event stream
- [ ] **Phase 11: RFI/Submittal Automation** — Detect RFI-type questions and auto-draft responses from the knowledge base
- [ ] **Phase 12: Decision Tracker** — Capture decisions from all channels, make them searchable, detect contradictions
- [ ] **Phase 13: Stakeholder Communication Map** — Model the stakeholder graph and auto-draft personalized notification chains
- [ ] **Phase 14: Change Impact Simulator** — Simulate schedule, budget, and stakeholder impact before approving changes
- [ ] **Phase 15: Auto-Generated Reports** — Generate daily and weekly project digests with AI-identified risks
- [ ] **Phase 16: Smart Notifications** — Score, route, and batch notifications by urgency and recipient relevance

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 10. Unified Inbox | 0/TBD | Not started | - |
| 11. RFI/Submittal Automation | 0/TBD | Not started | - |
| 12. Decision Tracker | 0/TBD | Not started | - |
| 13. Stakeholder Communication Map | 0/TBD | Not started | - |
| 14. Change Impact Simulator | 0/TBD | Not started | - |
| 15. Auto-Generated Reports | 0/TBD | Not started | - |
| 16. Smart Notifications | 0/TBD | Not started | - |

---

## Phase Details

### Phase 10: Unified Inbox
**Goal**: All project communications — emails, meeting transcripts, ACC notifications, and internal messages — are ingested, classified, enriched with action items, and available in a single filterable PM feed.
**Depends on**: v1.0 pipeline (existing ingestion connectors for Gmail, Fireflies, ACC)
**Requirements**: INBOX-01, INBOX-02, INBOX-03, INBOX-04, INBOX-05, INBOX-06
**Success Criteria** (what must be TRUE):
  1. A new email, a Fireflies transcript, and an ACC notification all appear in the unified inbox feed without any manual import — each tagged with source, project, and urgency.
  2. Opening any inbox item shows the extracted action items with assignee, deadline, and priority — derived by AI from the raw communication.
  3. Each item is classified as one of: decision, action-item, FYI, question, or escalation — and the PM can filter the feed by any of these types.
  4. Items are automatically routed to the correct project without PM intervention, based on content analysis of the communication body.
  5. Clicking the source link on any inbox item opens the original email, transcript, or ACC issue for full context.
**Plans**: TBD

### Phase 11: RFI/Submittal Automation
**Goal**: RFI-type questions detected from any communication source are automatically drafted into complete responses using the knowledge base, and the PM can review, edit, and send in one click.
**Depends on**: Phase 10 (unified inbox provides the communication stream)
**Requirements**: RFI-01, RFI-02, RFI-03, RFI-04, RFI-05, RFI-06
**Success Criteria** (what must be TRUE):
  1. A question about spec compliance in a meeting transcript is automatically flagged as an RFI and appears in the RFI queue — without any manual tagging by the PM.
  2. The AI-drafted RFI response cites at least one specific section from the project knowledge base and includes a recommended answer drawn from past RFIs.
  3. The PM can review the draft, edit inline, and send the RFI response to the appropriate parties with a single click.
  4. The RFI queue shows each item's current lifecycle status (open, drafted, reviewed, sent, responded, closed), age in days, assigned person, and priority.
  5. After the PM edits and sends a draft, the system learns the correction and applies it to improve future drafts for similar questions.
**Plans**: TBD

### Phase 12: Decision Tracker
**Goal**: Every decision made across meetings, emails, proposals, and ACC is captured into a searchable record, shown in a project timeline, and the PM is alerted when a new communication contradicts a prior decision.
**Depends on**: Phase 10 (unified inbox provides the classified decision events)
**Requirements**: DEC-01, DEC-02, DEC-03, DEC-04, DEC-05
**Success Criteria** (what must be TRUE):
  1. A decision made verbally in a Fireflies-transcribed meeting appears automatically in the decision log — attributed to the correct person and meeting.
  2. Each decision record shows: what was decided, who decided, when, the original communication context, and any linked proposal or document.
  3. The PM can search decisions by keyword, date range, project, person, or topic and get relevant results within 2 seconds.
  4. The decision timeline view shows all decisions for a project in chronological order, readable at a glance without needing to open individual records.
  5. When a new communication contradicts a logged decision, the PM receives an alert identifying both the original decision and the contradicting communication before any action is taken.
**Plans**: TBD

### Phase 13: Stakeholder Communication Map
**Goal**: A live stakeholder graph maps people to projects, roles, and preferences — and when a change occurs, the PM can review and send a full personalized notification chain to all affected parties in a single batch action.
**Depends on**: Phase 10 (inbox provides interaction data); v1.0 employee library (provides role/project assignments)
**Requirements**: SCOM-01, SCOM-02, SCOM-03, SCOM-04, SCOM-05
**Success Criteria** (what must be TRUE):
  1. Opening the stakeholder map for a project shows a visual graph with all assigned people, their roles, notification preferences, and recent communication activity.
  2. When the PM approves a material change, the system identifies every person in the notification chain — subcontractors, owners, architects — based on the change's impact analysis.
  3. Each stakeholder in the notification chain receives a draft message tailored to their role: the owner sees cost implications, the subcontractor sees schedule and scope details.
  4. The PM can review all drafted stakeholder messages in a single screen and send them all with one batch action — or edit individual messages before sending.
  5. The stakeholder map updates automatically as new communications occur, reflecting who has been notified and when.
**Plans**: TBD

### Phase 14: Change Impact Simulator
**Goal**: Before the PM approves any change, they see a complete impact summary — predicted schedule delta from earned value analysis, budget delta with contingency, all affected downstream tasks and stakeholders, similar past outcomes, and a Monte Carlo probability range for completion date.
**Depends on**: v1.0 schedule engine and learning engine; Phase 13 (stakeholder identification)
**Requirements**: CIS-01, CIS-02, CIS-03, CIS-04, CIS-05, CIS-06
**Success Criteria** (what must be TRUE):
  1. The schedule impact card shows a predicted delay range calculated using earned value analysis — not a static estimate — with the specific activities affected listed by name.
  2. The budget delta shows direct costs, indirect costs, and contingency impact separately, with a total calculated from the change's scope and current project rates.
  3. The affected parties panel lists every downstream task and stakeholder impacted by the change, derived from the dependency graph — not a manual lookup.
  4. The "similar past changes" panel shows at least one comparable historical change with its actual outcome: final cost, actual delay, and PM decision.
  5. The Monte Carlo probability bar shows P50, P75, and P90 completion dates, with the number of simulation runs and confidence interval visible.
  6. The entire impact summary appears as a single card before the accept/reject buttons — the PM cannot approve without seeing it.
**Plans**: TBD

### Phase 15: Auto-Generated Reports
**Goal**: The system automatically generates a daily project digest and a weekly status report for each active project, including AI-identified risks and recommendations, viewable in the dashboard and exportable.
**Depends on**: Phase 10 (inbox data), Phase 12 (decision log), Phase 14 (schedule/budget health data)
**Requirements**: RPT-01, RPT-02, RPT-03, RPT-04, RPT-05
**Success Criteria** (what must be TRUE):
  1. The daily digest for each project appears in the dashboard each morning without any PM action — covering activities from the past 24 hours, pending decisions, and flagged risks.
  2. The weekly status report includes schedule health, budget tracking, and progress metrics drawn from the current project data — not manually entered.
  3. Every report includes an AI-generated risks section listing specific risks (not generic warnings) with recommended actions the PM can take.
  4. The PM can export any report as structured data (JSON or PDF) directly from the dashboard.
  5. The PM can configure which projects receive automated reports, at what frequency, and which content sections to include — changes take effect on the next scheduled generation.
**Plans**: TBD

### Phase 16: Smart Notifications
**Goal**: Every notification is scored for urgency and relevance per recipient, critical items are delivered immediately, and lower-priority items are batched into a configurable digest — all visible in a notification center with urgency indicators.
**Depends on**: All preceding v2.0 phases (inbox, RFI, decisions, stakeholder map, reports feed the notification engine)
**Requirements**: NOTIF-01, NOTIF-02, NOTIF-03, NOTIF-04, NOTIF-05
**Success Criteria** (what must be TRUE):
  1. A notification about a critical schedule delay (urgency scored > 80) appears in the PM's notification center within 60 seconds of the triggering event — not held for the next digest.
  2. The same event generates notifications with different relevance scores for different recipients: the project engineer sees higher relevance than a tangentially involved stakeholder.
  3. Lower-priority notifications (urgency < 80) are held and delivered as a single digest at the PM's configured interval rather than creating noise.
  4. The PM can configure the urgency threshold for immediate delivery, the digest frequency, and which channels (dashboard, email) receive each type — changes apply to the next notification cycle.
  5. The notification center shows all notifications with read/unread state, urgency score, and source — and the PM can mark all as read or filter by urgency tier.
**Plans**: TBD

---

## Coverage Validation

| Phase | Requirements Mapped | Count |
|-------|---------------------|-------|
| Phase 10: Unified Inbox | INBOX-01, INBOX-02, INBOX-03, INBOX-04, INBOX-05, INBOX-06 | 6 |
| Phase 11: RFI/Submittal Automation | RFI-01, RFI-02, RFI-03, RFI-04, RFI-05, RFI-06 | 6 |
| Phase 12: Decision Tracker | DEC-01, DEC-02, DEC-03, DEC-04, DEC-05 | 5 |
| Phase 13: Stakeholder Communication Map | SCOM-01, SCOM-02, SCOM-03, SCOM-04, SCOM-05 | 5 |
| Phase 14: Change Impact Simulator | CIS-01, CIS-02, CIS-03, CIS-04, CIS-05, CIS-06 | 6 |
| Phase 15: Auto-Generated Reports | RPT-01, RPT-02, RPT-03, RPT-04, RPT-05 | 5 |
| Phase 16: Smart Notifications | NOTIF-01, NOTIF-02, NOTIF-03, NOTIF-04, NOTIF-05 | 5 |
| **Total v2.0** | | **37/37** |

Coverage: 37/37 v2.0 requirements mapped. No orphans.

---

*Last updated: 2026-03-21 — v2.0 roadmap initialized*
