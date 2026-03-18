# Implementation Plan

## 1. Reference Architecture (Service Split)
1. `ingestion-service`
- Receives BIM 360 webhooks.
- Runs scheduled polling for missed events.
- Normalizes payloads into canonical event schema.

2. `policy-gate-service`
- Classifies event type/intent.
- Enriches context (project, actor, artifact metadata).
- Executes security + governance checks.
- Produces priority score.

3. `orchestrator-service`
- Owns workflow graph.
- Coordinates retrieval + agent fanout.
- Maintains idempotency state per `event_id`.

4. `retrieval-service`
- Index pipeline + embeddings.
- Query pipeline (semantic/hybrid retrieval).
- Citation/evidence packaging.

5. `agent-runtime`
- Runs domain agents.
- Standard I/O contract and timeout budget.

6. `decision-service`
- Aggregates agent outputs.
- Resolves conflicts.
- Calibrates confidence.
- Generates action proposals and alternatives.

7. `action-gateway`
- Applies authority rules.
- Auto-executes or routes to PM approval.
- Persists audit trail.

8. `notification-service`
- Dashboard payloads.
- BIM 360 writeback/comments.
- Team email notifications.

## 2. Canonical Event Pipeline
1. `bim360.webhook.received`
2. `event.normalized`
3. `policy.validated`
4. `context.retrieved`
5. `agents.completed`
6. `decision.generated`
7. `authority.checked`
8. `action.executed` OR `approval.requested`
9. `notifications.sent`

## 3. Data Stores
1. `PostgreSQL`
- `projects`, `events`, `decisions`, `actions`, `approvals`, `audit_logs`.

2. `Vector DB`
- RAG chunks from BIM docs, comments, meeting/email summaries.

3. `Queue/Broker`
- Async retries, fanout, and dead-lettering.

4. `Object Storage`
- Raw payload snapshots and evidence bundles.

## 4. Core Schemas

```json
{
  "event_id": "evt_...",
  "source": "bim360",
  "type": "issue.updated",
  "project_id": "prj_...",
  "artifact_id": "iss_...",
  "actor": {"id": "usr_...", "role": "engineer"},
  "occurred_at": "2026-03-04T20:12:00Z",
  "payload": {}
}
```

```json
{
  "decision_id": "dec_...",
  "event_id": "evt_...",
  "proposal": "Assign issue to John and shift milestone by 2 days",
  "alternatives": ["Assign to Jane", "Escalate to PM"],
  "confidence": 0.81,
  "risk_level": "medium",
  "constraints": ["permit_required"],
  "evidence": [
    {"source": "bim_comment", "ref": "cmt_1042"},
    {"source": "schedule_doc", "ref": "chunk_911"}
  ]
}
```

## 5. Authority Policy (Initial)
1. Auto-execute when:
- confidence >= 0.80
- risk_level in `low|medium`
- no blockers (`regulatory_block`, `missing_owner`, `conflict_unresolved`)

2. PM approval required when:
- confidence < 0.80
- risk_level = `high`
- policy or compliance blocker exists

## 6. Phase Plan

### Phase 0: Foundation (Day 1-2)
1. Create services + contracts package.
2. Add DB migrations for events/decisions/actions/audit.
3. Add queue and idempotency middleware.

### Phase 1: Single Vertical Slice (Day 3-5)
1. Implement BIM 360 webhook ingestion.
2. Normalize `issue.updated` events.
3. Add policy gate + retrieval + `IssueAgent` + `RiskAgent`.
4. Produce decision package and authority check.
5. Send dashboard + BIM comment + email output.

### Phase 2: Human-in-the-loop (Day 6-7)
1. PM approval endpoints and state machine.
2. Notification escalation for pending approvals.
3. Re-entry path when PM responds.

### Phase 3: Reliability & Governance (Week 2)
1. Retries, DLQ, and replay tooling.
2. PII redaction + secret handling.
3. Telemetry dashboards: latency, confidence drift, false-action review.

## 7. Testing Strategy
1. Unit tests
- Event normalization.
- Policy gate rules.
- Authority decisions.

2. Contract tests
- BIM 360 payload compatibility.
- Agent output schema validation.

3. E2E tests
- Simulate webhook -> decision -> action path.
- Simulate low-confidence -> PM approval path.

4. Safety tests
- Adversarial prompt/data injection in RAG context.
- Permission boundary checks for auto-actions.

## 8. KPI Baseline
1. Decision latency p95 < 20s.
2. Auto-action precision > 95% for low risk.
3. PM approval turnaround median < 2h.
4. Failed writeback retry success > 99% within 15m.
