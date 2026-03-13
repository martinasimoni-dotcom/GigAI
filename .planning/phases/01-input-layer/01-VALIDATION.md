---
phase: 1
slug: input-layer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-12
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml (testpaths = ["tests"]) |
| **Quick run command** | `pytest tests/unit/ -x -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~20 seconds (unit only, all externals mocked) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/unit/ -x -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 0 | INPUT-01 | unit | `pytest tests/unit/test_webhooks.py -x -q` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 0 | INPUT-02 | unit | `pytest tests/unit/test_webhooks.py -x -q` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | INPUT-01 | unit | `pytest tests/unit/test_webhooks.py -x -q` | ❌ W0 | ⬜ pending |
| 1-01-04 | 01 | 1 | INPUT-02 | unit | `pytest tests/unit/test_webhooks.py -x -q` | ❌ W0 | ⬜ pending |
| 1-01-05 | 01 | 1 | INPUT-03 | unit | `pytest tests/unit/test_connectors.py -x -q` | ❌ W0 | ⬜ pending |
| 1-01-06 | 01 | 1 | INPUT-04 | unit | `pytest tests/unit/test_connectors.py -x -q` | ❌ W0 | ⬜ pending |
| 1-01-07 | 01 | 2 | INPUT-01,02 | unit | `pytest tests/unit/test_main.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_webhooks.py` — stubs for INPUT-01, INPUT-02
- [ ] `tests/unit/test_connectors.py` — stubs for INPUT-03, INPUT-04
- [ ] `tests/unit/test_main.py` — stub for FastAPI app wiring
- [ ] `tests/conftest.py` — already exists with mock fixtures from Phase 0

*Existing conftest.py from Phase 0 covers mock DB and mock LLM fixtures. New fixtures needed: mock_pubsub_publisher, mock_gmail_service, mock_calendar_service.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Pub/Sub message appears on raw-events topic within 5 seconds of webhook POST | INPUT-01 | Requires live GCP project with Pub/Sub enabled | Run `curl -X POST /webhooks/fireflies -d @tests/fixtures/sample_transcript.json`; verify message in GCP Console or with `gcloud pubsub subscriptions pull` |
| Gmail polling publishes real email to Pub/Sub | INPUT-03 | Requires live Gmail OAuth credentials | Set GMAIL_REFRESH_TOKEN in .env, send test email to monitored inbox, run `python -c "from src.input.connectors.gmail import poll_gmail; poll_gmail()"` |
| Calendar polling publishes real calendar event to Pub/Sub | INPUT-04 | Requires live Google Calendar OAuth credentials | Set credentials in .env, create test event with "delivery" in title, run `python -c "from src.input.connectors.calendar import poll_calendar; poll_calendar()"` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
