# Requirements: GigAI v2.0 — Communication Intelligence

**Defined:** 2026-03-21
**Core Value:** Eliminate manual PM coordination burden by automating capture, enrichment, proposal generation, action execution, and communication across all project channels.

## v2.0 Requirements

### Unified Inbox

- [ ] **INBOX-01**: System ingests emails, meeting transcripts, ACC notifications, and internal messages into a single unified event stream
- [ ] **INBOX-02**: AI extracts action items from every ingested communication with assignee, deadline, and priority
- [ ] **INBOX-03**: AI classifies each communication by type (decision, action-item, FYI, question, escalation) and urgency
- [ ] **INBOX-04**: PM can view all project communications in a filterable feed sorted by urgency
- [ ] **INBOX-05**: Each inbox item links to its source (email, transcript, ACC issue) for full context
- [ ] **INBOX-06**: AI auto-routes communications to the relevant project and stakeholders based on content analysis

### RFI/Submittal Automation

- [ ] **RFI-01**: System detects RFI-type questions from any communication source (email, meeting, ACC)
- [ ] **RFI-02**: AI auto-drafts RFI responses by searching knowledge base, past RFIs, and project specs
- [ ] **RFI-03**: PM can review, edit, and send AI-drafted RFI response with one click
- [ ] **RFI-04**: System tracks RFI lifecycle (open → drafted → reviewed → sent → responded → closed)
- [ ] **RFI-05**: Dashboard displays RFI queue with status, age, assignee, and priority
- [ ] **RFI-06**: System learns from PM edits to improve future RFI draft quality

### Auto-Generated Reports

- [ ] **RPT-01**: System generates daily project digest summarizing activities, decisions, risks, and pending items
- [ ] **RPT-02**: System generates weekly status report with progress metrics, budget tracking, and schedule health
- [ ] **RPT-03**: Reports include AI-identified risks and recommendations based on schedule/budget analysis
- [ ] **RPT-04**: Reports are viewable in dashboard and exportable as structured data
- [ ] **RPT-05**: PM can configure report frequency, recipients, and content sections

### Stakeholder Communication Map

- [ ] **SCOM-01**: System maintains a stakeholder graph mapping people to projects, roles, and notification preferences
- [ ] **SCOM-02**: When a change occurs, system identifies the full notification chain based on impact analysis
- [ ] **SCOM-03**: AI drafts personalized messages for each stakeholder based on their role and information needs
- [ ] **SCOM-04**: PM can review and send all stakeholder notifications in a single batch action
- [ ] **SCOM-05**: Dashboard displays visual stakeholder map showing communication flow and recent interactions

### Decision Tracker

- [ ] **DEC-01**: System captures decisions from all communication channels (meetings, emails, proposals, ACC)
- [ ] **DEC-02**: Each decision record includes: what was decided, who decided, when, context, and linked documents
- [ ] **DEC-03**: PM can search decisions by keyword, date range, project, person, or topic
- [ ] **DEC-04**: Decision timeline view shows chronological decision history per project
- [ ] **DEC-05**: System detects when a new communication contradicts or revisits a previous decision and alerts PM

### Change Impact Simulator

- [ ] **CIS-01**: Before approving a change, PM sees predicted schedule impact using earned value analysis
- [ ] **CIS-02**: System calculates budget delta including direct costs, indirect costs, and contingency impact
- [ ] **CIS-03**: System identifies all affected stakeholders and downstream tasks from the proposed change
- [ ] **CIS-04**: System shows similar past changes and their actual outcomes (from learning engine)
- [ ] **CIS-05**: Monte Carlo simulation provides probabilistic completion date range (P50, P75, P90)
- [ ] **CIS-06**: Impact analysis is presented as a summary card before the accept/reject decision

### Smart Notifications

- [ ] **NOTIF-01**: System scores each notification by urgency (0-100) using deadline proximity, financial impact, and dependency analysis
- [ ] **NOTIF-02**: System scores each notification by relevance per recipient based on their role and project assignments
- [ ] **NOTIF-03**: Critical notifications (urgency > 80) are delivered immediately; lower-priority items batched into digest
- [ ] **NOTIF-04**: PM can configure notification preferences (immediate threshold, digest frequency, channels)
- [ ] **NOTIF-05**: Dashboard shows notification center with read/unread state and urgency indicators

## Future Requirements

### Advanced Analytics

- **ANLYT-01**: Executive dashboard with portfolio-level KPIs across all projects
- **ANLYT-02**: Predictive budget forecasting using historical project data
- **ANLYT-03**: Resource optimization recommendations based on employee availability and skills

### Integrations

- **INTG-01**: Slack/Teams integration for real-time notifications
- **INTG-02**: Procore/PlanGrid integration for document management
- **INTG-03**: Primavera P6 direct schedule import (XML/XER)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time chat/messaging | High complexity, overlaps with Slack/Teams — defer to integration |
| Mobile native app | Web responsive design sufficient for v2.0 |
| Custom LLM fine-tuning | Claude API provides sufficient quality without fine-tuning |
| Multi-language support | English-only for initial construction market |
| Video call integration | Low ROI relative to transcript ingestion which already captures content |
| Automated contract generation | Legal complexity, requires domain-specific review beyond AI scope |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INBOX-01 | TBD | Pending |
| INBOX-02 | TBD | Pending |
| INBOX-03 | TBD | Pending |
| INBOX-04 | TBD | Pending |
| INBOX-05 | TBD | Pending |
| INBOX-06 | TBD | Pending |
| RFI-01 | TBD | Pending |
| RFI-02 | TBD | Pending |
| RFI-03 | TBD | Pending |
| RFI-04 | TBD | Pending |
| RFI-05 | TBD | Pending |
| RFI-06 | TBD | Pending |
| RPT-01 | TBD | Pending |
| RPT-02 | TBD | Pending |
| RPT-03 | TBD | Pending |
| RPT-04 | TBD | Pending |
| RPT-05 | TBD | Pending |
| SCOM-01 | TBD | Pending |
| SCOM-02 | TBD | Pending |
| SCOM-03 | TBD | Pending |
| SCOM-04 | TBD | Pending |
| SCOM-05 | TBD | Pending |
| DEC-01 | TBD | Pending |
| DEC-02 | TBD | Pending |
| DEC-03 | TBD | Pending |
| DEC-04 | TBD | Pending |
| DEC-05 | TBD | Pending |
| CIS-01 | TBD | Pending |
| CIS-02 | TBD | Pending |
| CIS-03 | TBD | Pending |
| CIS-04 | TBD | Pending |
| CIS-05 | TBD | Pending |
| CIS-06 | TBD | Pending |
| NOTIF-01 | TBD | Pending |
| NOTIF-02 | TBD | Pending |
| NOTIF-03 | TBD | Pending |
| NOTIF-04 | TBD | Pending |
| NOTIF-05 | TBD | Pending |

**Coverage:**
- v2.0 requirements: 37 total
- Mapped to phases: 0
- Unmapped: 37

---
*Requirements defined: 2026-03-21*
*Last updated: 2026-03-21 after initial definition*
