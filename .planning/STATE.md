---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Communication Intelligence
status: defining_requirements
last_updated: "2026-03-21"
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# STATE.md — GigAI
## Project Memory (Updated Each Session)

---

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-21)

**Core value:** Eliminate manual PM coordination burden by automating capture, enrichment, proposal generation, action execution, and communication.
**Current focus:** Milestone v2.0 — Communication Intelligence

---

## Current Position

| Field | Value |
|-------|-------|
| Current Phase | Not started (defining requirements) |
| Current Plan | — |
| Status | Defining requirements for v2.0 milestone |
| Last Updated | 2026-03-21 |
| Last activity | 2026-03-21 — Milestone v2.0 started |

---

## Accumulated Context

### Key Decisions Made

- All v1.0 key decisions still apply (see below)
- **v2.0 scope**: 7 major features (unified inbox, RFI automation, auto-reports, stakeholder map, decision tracker, change impact simulator, smart notifications)
- **Prediction models**: Must use academically-grounded approaches (earned value, Monte Carlo, Bayesian) — not heuristics
- **Research completed**: Domain research done via brainstorming agent with academic sources (PMI, McKinsey, Deloitte)
- **Demo mode removed**: No more DEMO_MODE flag — pipeline runs synchronously when Pub/Sub unavailable
- **Pipeline renamed**: src/demo/pipeline.py → src/pipeline/runner.py

### v1.0 Architecture Decisions (still apply)

- **LLM stack**: Claude Sonnet 4 for proposals, Claude Haiku 4.5 for normalization/routing
- **Embeddings**: Voyage-3 at 1024 dimensions
- **Database**: PostgreSQL 15 + pgvector with HNSW indexes
- **Event bus**: Google Cloud Pub/Sub (at-least-once delivery)
- **Human-in-the-loop enforced**: Nothing executes without PM approval
- **Config-driven pipeline**: Domain processing driven by YAML configs
- **Pydantic v2 API only**: field_validator + @classmethod, ConfigDict
- **Settings fail-fast**: module-level singleton raises ValidationError on missing env vars

### v1.0 Completed Features

- Event-driven AI pipeline (webhooks → normalize → route → enrich → propose → execute)
- Project library (30 projects, 6 categories, filters, stats)
- Employee library (30 employees, profession filters, stats)
- Schedule predictions (Primavera P6-style urgency/conflict/delay analysis)
- GigAI learning engine (decision patterns → vector store)
- Apple macOS dark mode dashboard with sidebar navigation
- ACC facade with fallback, audit trail, SSE notifications

---

## Session Continuity

### To Resume Work

1. Read this STATE.md to understand current position
2. Read `.planning/ROADMAP.md` for phase structure
3. Read `.planning/REQUIREMENTS.md` for requirement details
4. Begin implementing from the first incomplete phase

---
