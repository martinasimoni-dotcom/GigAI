# System Contracts

## 1. Service APIs (MVP)

### Ingestion
`POST /webhooks/bim360`
- Input: raw BIM 360 webhook payload
- Output: `202 Accepted` with `event_id`

`POST /internal/events/replay/{event_id}`
- Replays a normalized event through orchestration.

### Decision
`POST /internal/decisions/evaluate`
- Input: normalized event + context refs
- Output: decision package

### Action Gateway
`POST /internal/actions/execute`
- Input: decision package
- Output: execution result or approval request id

### Approval
`POST /approvals/{approval_id}/approve`
`POST /approvals/{approval_id}/reject`
- Input: approver metadata + optional note
- Output: action status update

## 2. Internal Event Bus Contracts

### `event.normalized`
```json
{
  "event_id": "evt_123",
  "type": "issue.updated",
  "project_id": "prj_10",
  "priority": 72,
  "context_refs": ["doc_44", "comment_91"],
  "payload": {}
}
```

### `decision.generated`
```json
{
  "decision_id": "dec_9",
  "event_id": "evt_123",
  "proposal": "assign_to_member",
  "params": {"assignee": "john", "due_date": "2026-03-06"},
  "confidence": 0.84,
  "risk_level": "low",
  "blockers": []
}
```

### `approval.requested`
```json
{
  "approval_id": "apr_55",
  "decision_id": "dec_9",
  "reason": "confidence_below_threshold",
  "requested_from": "pm_user_1",
  "expires_at": "2026-03-05T16:00:00Z"
}
```

## 3. Database Tables (Minimum)

### `events`
- `id` (pk)
- `source`
- `type`
- `project_id`
- `payload_json`
- `normalized_json`
- `status`
- `created_at`

### `decisions`
- `id` (pk)
- `event_id` (fk)
- `proposal_json`
- `confidence`
- `risk_level`
- `evidence_json`
- `created_at`

### `actions`
- `id` (pk)
- `decision_id` (fk)
- `mode` (`auto`|`manual`)
- `status`
- `result_json`
- `created_at`

### `approvals`
- `id` (pk)
- `decision_id` (fk)
- `requested_from`
- `status`
- `note`
- `requested_at`
- `resolved_at`

### `audit_logs`
- `id` (pk)
- `entity_type`
- `entity_id`
- `event_type`
- `actor`
- `metadata_json`
- `created_at`

## 4. Agent I/O Standard

### Agent Input
```json
{
  "trace_id": "trc_...",
  "event": {},
  "retrieved_context": [],
  "constraints": [],
  "time_budget_ms": 5000
}
```

### Agent Output
```json
{
  "agent": "IssueAgent",
  "summary": "Root cause likely unresolved dependency",
  "proposals": ["reassign", "adjust_milestone"],
  "risk_signals": ["deadline_slip"],
  "confidence": 0.78,
  "citations": ["chunk_111", "chunk_177"]
}
```

## 5. Non-Functional Requirements
1. Idempotency key: `source + external_event_id`.
2. Deterministic retries for writeback actions.
3. Structured logging with `trace_id`, `event_id`, `decision_id`.
4. PII-safe redaction in logs and prompts.
5. SLA guardrails:
- webhook ack < 1s
- full pipeline p95 < 20s
