# Product Requirements Document (PRD)
## Material Change Coordination Workflow

**Version:** 1.0  
**Date:** March 12, 2026  
**Status:** Draft  
**Owner:** Product Team  

---

## 1. Executive Summary

### 1.1 Product Vision
The Material Change Coordinator is an intelligent automation system that transforms how construction project managers handle material change coordination. By automatically capturing, processing, and coordinating material changes from various sources, the system reduces manual PM workload by 80% while improving accuracy and stakeholder communication.

### 1.2 Problem Statement
Construction project managers spend 60-70% of their time on coordination tasks when material changes occur:
- Manually tracking changes from meeting notes and conversations
- Contacting suppliers for quotes and availability
- Updating schedules and drawings
- Notifying multiple stakeholders
- Following up on procurement and delivery

This manual process leads to:
- Delays in procurement (average 3-5 days to start ordering)
- Communication gaps (stakeholders miss critical updates)
- Human errors (wrong quantities, missed notifications)
- PM burnout and reduced time for strategic work

### 1.3 Solution Overview
An event-driven AI system that:
1. Automatically detects material changes from meetings, ACC, and calendars
2. Enriches changes with project context (floor plans, suppliers, history)
3. Generates coordinated actions using AI (emails, tasks, calendar, drawings)
4. Presents proposals to PM with confidence scoring
5. Executes approved actions automatically
6. Learns from decisions to improve over time

### 1.4 Success Criteria
- **Efficiency**: Reduce PM coordination time by 80% (from 4 hours to 48 minutes per change)
- **Accuracy**: Achieve >90% accuracy on high-confidence (>80%) proposals
- **Speed**: Generate proposals within 5 minutes of change detection
- **Adoption**: 75% PM acceptance rate of proposals within 3 months
- **ROI**: Save $50K+ per project in PM time and faster procurement

---

## 2. User Personas

### 2.1 Primary User: Project Manager (Sarah)
- **Role**: Senior Project Manager at mid-size construction firm
- **Responsibilities**: Oversees 3-5 concurrent construction projects
- **Pain Points**: 
  - Drowning in coordination emails and calls
  - Struggles to track all material changes across projects
  - Delays in supplier communication cost project time
- **Goals**:
  - Focus on strategic decisions, not tactical coordination
  - Ensure no material changes fall through cracks
  - Maintain clear communication with all stakeholders
- **Tech Savvy**: Moderate (uses ACC, email, calendars daily)

### 2.2 Secondary User: Procurement Officer (Mike)
- **Role**: Procurement specialist
- **Responsibilities**: Orders materials, manages supplier relationships
- **Pain Points**:
  - Receives unclear or incomplete change requests
  - Wastes time chasing down missing information
- **Goals**:
  - Receive clear, complete procurement requests
  - Quick access to supplier preferences and pricing
- **Tech Savvy**: Moderate

### 2.3 Tertiary User: Suppliers (Jane)
- **Role**: Sales representative at material supplier company
- **Responsibilities**: Responds to quotes, manages orders
- **Pain Points**:
  - Receives inconsistent order requests
  - Unclear specifications lead to back-and-forth
- **Goals**:
  - Receive complete, clear order requests
  - Quick confirmation and order processing
- **Tech Savvy**: Low to Moderate

---

## 3. Use Cases & User Stories

### 3.1 Core Use Case: Material Substitution Workflow

**Scenario:** Window Material Change  
**Context:** During a weekly project meeting, the architect mentions changing third-floor windows from aluminum to wood frames due to design update.

**Current Manual Process (4 hours):**
1. PM takes meeting notes (15 min)
2. PM reviews floor plans to identify affected units (30 min)
3. PM emails supplier for quote on wood frames (20 min)
4. PM waits for supplier response (1-2 days)
5. PM creates task for procurement officer (10 min)
6. PM schedules follow-up meeting (15 min)
7. PM updates project schedule (30 min)
8. PM notifies installation team (15 min)
9. PM marks up drawings (45 min)

**Automated Process (12 minutes):**
1. System captures meeting transcript via Fireflies (automatic)
2. System normalizes event: Aluminum → Wood, 3rd floor, 12 units (30 seconds)
3. System enriches with floor plan, supplier data, pricing (1 min)
4. System generates coordinated actions via Claude API (2 min)
5. System presents proposal to PM with 86% confidence (instant)
6. PM reviews and approves (5 min)
7. System executes all actions automatically (3 min)

**Time Saved:** 3 hours 48 minutes (95% reduction)

### 3.2 User Stories

#### Epic 1: Event Capture & Normalization

**US-1.1:** As a PM, I want the system to automatically capture material changes mentioned in meeting transcripts, so I don't have to manually transcribe and track them.

**Acceptance Criteria:**
- Fireflies webhook integration receives transcripts within 5 minutes of meeting end
- System extracts material changes with >85% accuracy
- Material, location, and quantity are correctly identified

**US-1.2:** As a PM, I want the system to monitor ACC for change orders, so I don't miss official change documentation.

**Acceptance Criteria:**
- System polls ACC every 5 minutes for new change orders
- Change orders are normalized into consistent format
- System links change orders to relevant meeting transcripts

**US-1.3:** As a PM, I want the system to detect material-related calendar events, so schedule impacts are automatically considered.

**Acceptance Criteria:**
- System monitors Google Calendar for material delivery events
- Installation schedule conflicts are flagged
- Timeline impacts are calculated automatically

#### Epic 2: Context Enrichment & Intelligence

**US-2.1:** As a PM, I want the system to automatically identify affected building units/areas, so I don't have to manually cross-reference floor plans.

**Acceptance Criteria:**
- System accesses ACC floor plans via API
- Markup files provide supplementary context
- Affected units are listed with specific IDs (e.g., W-301 to W-312)

**US-2.2:** As a PM, I want the system to suggest appropriate suppliers based on material type and past performance, so I get competitive pricing quickly.

**Acceptance Criteria:**
- Supplier database maintained in markup files
- Historical performance data retrieved from PostgreSQL
- Top 2-3 suppliers ranked by price, lead time, and quality

**US-2.3:** As a PM, I want the system to find similar past changes and their outcomes, so I can leverage proven approaches.

**Acceptance Criteria:**
- PostgreSQL similarity search finds ≥3 comparable changes
- Success rate and lessons learned are displayed
- Historical data influences confidence scoring

#### Epic 3: Action Generation & Coordination

**US-3.1:** As a PM, I want the system to automatically draft supplier emails with complete specifications, so I can send them with one click.

**Acceptance Criteria:**
- Email includes material specs, quantity, delivery timeline
- Supplier contact pre-populated from database
- Email tone is professional and clear
- PM can edit before sending

**US-3.2:** As a procurement officer, I want to receive clear tasks with all information needed to order materials, so I don't waste time chasing details.

**Acceptance Criteria:**
- Task includes material name, quantity, supplier contact, budget code
- Task is created in PM tool (future: Asana/Monday integration)
- Checklist breaks down procurement steps
- Due date calculated based on project timeline

**US-3.3:** As a PM, I want calendar events automatically created for material follow-ups, so nothing falls through the cracks.

**Acceptance Criteria:**
- Follow-up event scheduled 1 week after order
- Relevant stakeholders invited
- Event includes link to change details

**US-3.4:** As a PM, I want drawing markups automatically generated, so drawings stay current without manual work.

**Acceptance Criteria:**
- Correct drawing identified from ACC
- Markup highlights affected area with change description
- Markup color-coded by change type (red = material change)

#### Epic 4: Decision Intelligence & Confidence Scoring

**US-4.1:** As a PM, I want the system to calculate confidence scores, so I know which proposals I can trust.

**Acceptance Criteria:**
- Confidence score based on: data clarity, historical match, cost, red flags
- Score displayed as percentage (e.g., 86%)
- Breakdown shows contributing factors
- Threshold: >80% recommended for acceptance

**US-4.2:** As a PM, I want red flags clearly highlighted for high-risk changes, so I can focus my attention appropriately.

**Acceptance Criteria:**
- Structural changes flagged
- Cost exceeding $50K flagged
- Regulatory/safety impacts flagged
- Out-of-scope changes flagged and routed for special review

**US-4.3:** As a PM, I want to see a complete proposal with all coordinated actions before approval, so I understand exactly what will happen.

**Acceptance Criteria:**
- Proposal shows alert summary (what, where, quantity, cost)
- All 4 action types previewed (email, task, calendar, drawing)
- Confidence score and recommendation displayed
- Accept/Reject buttons with optional reason field

#### Epic 5: Execution & Feedback Loop

**US-5.1:** As a PM, when I accept a proposal, I want all actions to execute automatically, so I don't have to perform each action manually.

**Acceptance Criteria:**
- Email sent via configured email service
- Task created in PM tool
- Calendar event added to Google Calendar
- Drawing markup added to ACC
- Execution status reported back to PM

**US-5.2:** As a PM, when I reject a proposal, I want to provide feedback so the system learns and improves.

**Acceptance Criteria:**
- Rejection reason captured (dropdown + optional text)
- Feedback stored in PostgreSQL
- System adjusts confidence weights based on patterns
- PM notified of system improvements quarterly

**US-5.3:** As a PM, I want to see system performance metrics, so I know it's saving me time and working accurately.

**Acceptance Criteria:**
- Dashboard shows: proposals generated, acceptance rate, time saved
- Accuracy metrics: high-confidence acceptance rate
- Response time: average time from event to proposal
- Monthly email summary of system impact

---

## 4. Functional Requirements

### 4.1 Input Layer

**FR-1.1: Fireflies Integration**
- System MUST receive meeting transcripts via webhook within 5 minutes of meeting end
- System MUST parse transcripts for material change keywords
- System MUST extract: material names, quantities, locations, participants
- System MUST publish raw events to Google Cloud Pub/Sub

**FR-1.2: ACC (Autodesk Construction Cloud) Integration**
- System MUST poll ACC API every 5 minutes for new change orders
- System MUST retrieve project context (floor plans, unit locations, drawings)
- System MUST authenticate via OAuth 2.0
- System MUST handle API rate limits gracefully

**FR-1.3: Google Calendar Integration**
- System MUST monitor calendars for material delivery and installation events
- System MUST detect schedule conflicts
- System MUST write calendar events for follow-ups

### 4.2 System Layer - Data Processing

**FR-2.1: Event Normalization**
- System MUST convert raw events into standardized schema
- System MUST extract: original material, new material, location, quantity, change type
- System MUST validate required fields before processing
- System MUST handle extraction confidence <70% by flagging for manual review

**FR-2.2: Security & Scope Filtering**
- System MUST filter events based on project scope rules
- System MUST reject out-of-scope changes (wrong location, wrong material type)
- System MUST escalate cost changes >$50K to PM immediately
- System MUST enforce read/write permissions based on user roles

**FR-2.3: Event Routing**
- System MUST route events to appropriate processing pipelines
- Material changes → Material processing
- Schedule changes → Schedule processing
- Cost changes → Budget processing

### 4.3 System Layer - Context Enrichment

**FR-3.1: Floor Plan & Location Enrichment**
- System MUST fetch floor plans from ACC API
- System MUST identify affected units/areas from location description
- System MUST cross-reference with markup files for additional context
- System MUST provide visual references when available

**FR-3.2: Team & Supplier Enrichment**
- System MUST retrieve team contacts from markup files
- System MUST match material types to qualified suppliers
- System MUST include supplier pricing and lead times
- System MUST rank suppliers by performance history

**FR-3.3: Historical Data Retrieval**
- System MUST query PostgreSQL for similar past changes
- System MUST use similarity scoring based on: material type, location, cost range
- System MUST return top 5 similar cases with outcomes
- System MUST calculate success rate for similar changes

### 4.4 System Layer - Domain Processing

**FR-4.1: Meeting Logic & Task Identification**
- System MUST identify required actions:
  - Procurement needed? (check inventory, compare to requirement)
  - Schedule update needed? (check timeline impact)
  - Stakeholder notification needed? (identify affected parties)
  - Drawing markup needed? (check if drawings exist)

**FR-4.2: Signal Generation**
- System MUST generate signals for each identified action
- Signals MUST include: type, priority, data payload, timestamp
- System MUST publish signals to decision intelligence layer

### 4.5 System Layer - Decision Intelligence

**FR-5.1: Action Generation (Claude API)**
- System MUST call Claude API with enriched context
- System MUST generate 4 action types: Email, Task, Calendar Event, Drawing Markup
- System MUST format actions using templates
- System MUST handle API errors with retry logic (3 attempts)

**FR-5.2: Confidence Scoring**
- System MUST calculate confidence score based on:
  - Data clarity: 30% weight (all fields present and validated?)
  - Historical match: 25% weight (similar past changes successful?)
  - Cost acceptable: 25% weight (within budget threshold?)
  - No red flags: 20% weight (structural/safety/regulatory concerns?)
- System MUST display score as percentage (0-100%)
- System MUST provide score breakdown
- System MUST recommend: auto-approve (>80%), review (50-80%), reject (<50%)

### 4.6 Output Layer

**FR-6.1: Proposal Building**
- System MUST compile alert + actions + confidence into proposal
- Proposal MUST include:
  - Alert: Title, description, location, quantity, estimated cost
  - Actions: Email preview, task preview, calendar preview, drawing preview
  - Confidence: Overall score + breakdown
  - Recommendation: Accept/Review/Reject
- System MUST store proposal in database with unique ID

**FR-6.2: PM Decision Interface**
- System MUST present proposal to PM via web interface
- Interface MUST show all proposal details clearly
- Interface MUST provide Accept/Reject buttons
- Interface MUST allow optional rejection reason input
- Interface MUST confirm action before execution

**FR-6.3: Action Gateway (Execution)**
- System MUST execute approved actions in parallel
- Email: Send via SendGrid or Gmail API
- Task: Create in PM tool (initially local DB, future: Asana/Monday)
- Calendar: Add event to Google Calendar
- Drawing: Add markup to ACC drawing
- System MUST report execution status for each action
- System MUST handle partial failures gracefully

**FR-6.4: Feedback & Learning**
- System MUST store all PM decisions (accept/reject + reason)
- System MUST calculate acceptance rate by confidence range
- System MUST identify patterns in rejections
- System MUST adjust confidence weights quarterly based on feedback
- System MUST notify PM of system improvements

---

## 5. Non-Functional Requirements

### 5.1 Performance
- **Response Time**: Proposals generated within 5 minutes of event detection (95th percentile)
- **API Latency**: Claude API calls complete within 10 seconds
- **Database Queries**: PostgreSQL queries return within 2 seconds
- **Scalability**: Handle 100+ material changes per day across 10+ projects

### 5.2 Reliability
- **Uptime**: 99.5% availability during business hours (8am-6pm)
- **Data Durability**: Zero data loss for events and proposals
- **Fault Tolerance**: Graceful degradation if external APIs fail
- **Recovery**: Automatic retry for failed external API calls (3 attempts with exponential backoff)

### 5.3 Security
- **Authentication**: OAuth 2.0 for all external API integrations
- **Data Encryption**: TLS 1.3 for data in transit, AES-256 for data at rest
- **API Keys**: Stored in environment variables, never in code
- **Access Control**: Role-based permissions (PM, Procurement, Admin)
- **Audit Logging**: All actions and decisions logged with timestamps

### 5.4 Usability
- **PM Interface**: Simple, intuitive decision UI (no training required)
- **Mobile Responsive**: Decision interface works on mobile devices
- **Accessibility**: WCAG 2.1 AA compliant
- **Language**: English (future: Spanish, French)

### 5.5 Maintainability
- **Code Quality**: 80%+ test coverage
- **Documentation**: All components documented with JSDoc
- **Logging**: Structured JSON logs for easy parsing
- **Monitoring**: Integrated with logging service (e.g., CloudWatch, Datadog)

### 5.6 Compliance
- **Data Privacy**: GDPR compliant (user data deletion within 30 days of request)
- **Data Retention**: Event data retained for 2 years, then archived
- **Regulatory**: Follows construction industry standards for document management

---

## 6. Technical Architecture

### 6.1 Technology Stack
- **Runtime**: Node.js 18+
- **Database**: PostgreSQL 14+
- **Event Bus**: Google Cloud Pub/Sub
- **AI**: Anthropic Claude API (Sonnet 4)
- **APIs**: Fireflies, Autodesk ACC, Google Calendar, SendGrid/Gmail
- **Hosting**: Google Cloud Platform (Cloud Run for containers)

### 6.2 Data Flow
1. **Input** → Event sources publish to Pub/Sub → `raw-events` topic
2. **Normalization** → Subscriber processes → Publishes to `normalized-events` topic
3. **Enrichment** → Adds context → Publishes to `enriched-events` topic
4. **Domain Processing** → Analyzes → Publishes to `signals` topic
5. **Decision Intelligence** → Generates actions → Stores proposal in PostgreSQL
6. **Output** → PM decides → Action Gateway executes → Feedback stored

### 6.3 Database Schema

**Events Table:**
```sql
event_id (PK), event_type, source, raw_data, normalized_data, enriched_data, created_at, processed_at
```

**Proposals Table:**
```sql
proposal_id (PK), event_id (FK), alert, actions, confidence_score, status, created_at
```

**Actions Table:**
```sql
action_id (PK), proposal_id (FK), action_type, action_data, status, executed_at, created_at
```

**Feedback Table:**
```sql
feedback_id (PK), proposal_id (FK), decision, rejection_reason, confidence_at_decision, created_at
```

**Past Changes Table (for historical matching):**
```sql
change_id (PK), change_type, material_from, material_to, location, cost, outcome, confidence, created_at
```

---

## 7. Example Scenarios

### 7.1 Scenario: Window Material Substitution

**Input Event (Fireflies Transcript):**
> "We discussed the third-floor windows during the design review meeting. The architect wants to change from aluminum frames to wood frames to match the building aesthetic. This affects all windows on the third floor—that's 12 units total. We need to get pricing from our wood supplier and update the installation schedule."

**System Processing:**

1. **Normalization:**
   - Material: { original: "Aluminum frames", new: "Wood frames" }
   - Location: "Third floor"
   - Quantity: "12 units"
   - Change type: "material_substitution"

2. **Enrichment:**
   - Floor plan: Retrieved from ACC (identifies units W-301 to W-312)
   - Supplier: Premium Wood Co. ($450/unit, 3-4 week lead time)
   - Team: Procurement Officer (Mike), Installation Lead (Bob), Supplier Contact (Jane)
   - Historical: 2 similar wood frame changes, 100% success rate, avg confidence 90%

3. **Domain Processing:**
   - Tasks identified: Procurement, Schedule update, Stakeholder notification, Drawing markup
   - Signals: "material_order_required", "schedule_update_needed", "drawing_markup_required"

4. **Decision Intelligence:**
   - Claude API generates:
     - **Email to Jane (Supplier):**  
       "Hi Jane, We need to order 12 wood frame units for our third-floor window replacement. Specs: Standard 48"x60", north-facing installation. Can you confirm availability and delivery within 3-4 weeks? Total budget: $5,400. Thanks!"
     
     - **Task for Mike (Procurement):**  
       "Order wood frames - 3rd floor. Supplier: Premium Wood Co. (Jane). Qty: 12 units. Budget: $5,400. Order by: April 1st."
     
     - **Calendar Event:**  
       "Follow-up: Wood frame delivery status. Date: April 8th. Attendees: PM, Mike, Jane."
     
     - **Drawing Markup:**  
       "Drawing A-301: Windows W-301 to W-312 - Material change: Aluminum → Wood frames."

   - Confidence Scoring:
     - Data clarity: 95% (all fields clear)
     - Historical match: 90% (2 similar successful changes)
     - Cost acceptable: 100% ($5,400 well below $50K threshold)
     - No red flags: 100% (no structural/safety concerns)
     - **Overall Confidence: 86%** → **Recommendation: Accept**

5. **Proposal Presented to PM:**
   ```
   ⚠️ WINDOWS CHANGE ALERT

   Location: Third floor (units W-301 to W-312)
   Change: Aluminum frames → Wood frames
   Quantity: 12 units
   Estimated Cost: $5,400
   Lead Time: 3-4 weeks

   PROPOSED ACTIONS:
   📧 Email to supplier (Jane@PremiumWood.com)
   ✅ Task for procurement (Mike)
   📅 Calendar follow-up (April 8th)
   📐 Drawing markup (A-301)

   Confidence: 86% ✓ RECOMMENDED
   ```

6. **PM Decision: ACCEPT**

7. **Execution:**
   - Email sent to Jane ✓
   - Task created for Mike ✓
   - Calendar event added ✓
   - Drawing markup added to ACC ✓

8. **Feedback Loop:**
   - Decision stored: Accepted, 86% confidence
   - System learns: High-confidence wood frame changes continue to be accepted
   - Confidence weights remain stable

**Time Saved:** 3 hours 48 minutes  
**Manual Steps Eliminated:** 9  
**Stakeholders Notified:** 3 (automatically)  

---

### 7.2 Scenario: Out-of-Scope Change (Rejection)

**Input Event:**
> "We might need to change the windows on the neighboring property as well."

**System Processing:**

1. **Normalization:** Location: "Neighboring property"
2. **Scope Filtering:** ❌ REJECTED - Out of project scope
3. **Action:** Alert sent to PM for manual review
4. **Result:** Not processed further

---

### 7.3 Scenario: High-Cost Change (Requires Review)

**Input Event:**
> "Change all HVAC units to more efficient models. About 50 units total."

**System Processing:**

1. **Normalization:** Material: HVAC units, Quantity: 50
2. **Enrichment:** Estimated cost: $75,000 (exceeds $50K threshold)
3. **Confidence Scoring:** 
   - Red flag: Cost exceeds threshold
   - **Overall Confidence: 45%** → **Recommendation: Requires Review**
4. **Proposal:** Flagged as "High Cost - PM Review Required"
5. **PM Reviews:** Can accept with justification or reject

---

## 8. Metrics & KPIs

### 8.1 System Performance Metrics
- **Event Processing Time**: Time from event capture to proposal generation
  - Target: <5 minutes (95th percentile)
- **Confidence Accuracy**: % of high-confidence (>80%) proposals that are accepted
  - Target: >90%
- **Action Execution Success Rate**: % of actions that execute without errors
  - Target: >95%

### 8.2 Business Impact Metrics
- **Time Saved per Change**: Manual time (4 hours) vs. automated time (12 minutes)
  - Target: 80% reduction
- **PM Adoption Rate**: % of proposals accepted by PMs
  - Target: 75% within 3 months
- **Procurement Speed**: Time from change detection to supplier contact
  - Target: <1 hour (vs. 1-2 days manual)

### 8.3 Quality Metrics
- **Stakeholder Notification Coverage**: % of relevant stakeholders notified
  - Target: 100%
- **Data Accuracy**: % of normalized events with correct data extraction
  - Target: >85%
- **User Satisfaction**: PM satisfaction score (survey)
  - Target: 4.0/5.0

---

## 9. Risks & Mitigations

### 9.1 Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Claude API downtime | High | Low | Implement retry logic, fallback to templates |
| ACC API rate limits | Medium | Medium | Cache floor plans, implement request throttling |
| PostgreSQL performance | Medium | Low | Optimize queries, add indexes, consider read replicas |
| Fireflies webhook delays | Low | Medium | Implement polling fallback |

### 9.2 Business Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Low PM adoption | High | Medium | User training, gradual rollout, champion program |
| Incorrect actions executed | High | Low | Require PM approval, high confidence threshold (80%) |
| Supplier email format issues | Low | Medium | Template validation, PM preview before send |
| Cost estimation errors | Medium | Medium | Conservative estimates, PM review for high costs |

### 9.3 Compliance Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Data privacy violations | High | Low | GDPR compliance review, data encryption, audit logs |
| Unauthorized access | High | Low | OAuth 2.0, role-based access control |
| Data loss | Medium | Low | Daily backups, disaster recovery plan |

---

## 10. Development Phases

### Phase 1: MVP (Months 1-3)
**Goal:** Prove core value with manual PM decision step

**Features:**
- ✅ Fireflies webhook integration
- ✅ Event normalization (material, location, quantity extraction)
- ✅ Basic enrichment (markup files for suppliers, team contacts)
- ✅ Claude API action generation
- ✅ Simple confidence scoring (rule-based)
- ✅ PM decision web interface
- ✅ Manual action execution (copy-paste actions)
- ✅ PostgreSQL storage

**Success Criteria:**
- Process 10+ material changes successfully
- 70%+ PM acceptance rate
- Demonstrate time savings

### Phase 2: Automation (Months 4-6)
**Goal:** Automate action execution and add ACC integration

**Features:**
- ✅ ACC API integration (floor plans, drawings)
- ✅ Automated action execution (emails, tasks, calendar)
- ✅ Drawing markup automation
- ✅ Historical data retrieval for confidence scoring
- ✅ Feedback loop implementation

**Success Criteria:**
- 80%+ time reduction vs. manual
- 80%+ PM acceptance rate
- Actions execute without PM intervention

### Phase 3: Intelligence (Months 7-9)
**Goal:** Advanced ML and multi-project support

**Features:**
- ✅ ML-based confidence scoring (learn from feedback)
- ✅ Multi-project support
- ✅ Advanced similarity search
- ✅ Predictive analytics (anticipate changes)
- ✅ Mobile app for PM decisions
- ✅ Real-time dashboard

**Success Criteria:**
- >90% confidence accuracy
- Support 5+ concurrent projects
- Mobile adoption by PMs

### Phase 4: Scale (Months 10-12)
**Goal:** Enterprise features and optimization

**Features:**
- ✅ Cost optimization recommendations
- ✅ Supplier performance tracking
- ✅ Regulatory compliance checking
- ✅ Advanced reporting and analytics
- ✅ White-label customization

**Success Criteria:**
- 10+ enterprise clients
- $1M+ annual time savings across clients

---

## 11. Open Questions

1. **Email Service:** Should we use SendGrid (better deliverability) or Gmail API (easier setup)?
2. **PM Tool Integration:** Which PM tool to prioritize first? (Asana, Monday, Jira, other?)
3. **Markup File Management:** Should markup files be editable via UI or Git-based workflow?
4. **Confidence Threshold:** Should 80% threshold be configurable per PM or project?
5. **Multi-Language:** What's the priority for non-English support?
6. **Offline Mode:** Should the PM decision interface work offline?

---

## 12. Appendix

### 12.1 Glossary
- **ACC**: Autodesk Construction Cloud - Project management platform for construction
- **Material Change**: Any change in building materials (substitution, addition, removal)
- **Enrichment**: Adding contextual data to raw events (floor plans, suppliers, history)
- **Confidence Score**: ML-calculated probability that a proposal is correct (0-100%)
- **Markup File**: Markdown file containing project context (team, suppliers, etc.)
- **Signal**: Internal event indicating an action is needed
- **Proposal**: Package of alert + actions + confidence presented to PM

### 12.2 References
- [Fireflies API Documentation](https://docs.fireflies.ai/)
- [Autodesk Construction Cloud API](https://forge.autodesk.com/en/docs/acc/v1/overview/)
- [Google Cloud Pub/Sub](https://cloud.google.com/pubsub/docs)
- [Anthropic Claude API](https://docs.anthropic.com/)

---

**Document Status:** Ready for Review  
**Next Steps:** Technical feasibility review, architecture design, sprint planning

**Approvals:**
- [ ] Product Manager
- [ ] Engineering Lead
- [ ] PM User Representative (Sarah)
- [ ] Stakeholders

---
