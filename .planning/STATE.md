---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Communication Intelligence
status: roadmap_complete
last_updated: "2026-03-21"
progress:
  total_phases: 7
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
**Current focus:** Milestone v2.0 — Communication Intelligence (roadmap defined, ready to plan Phase 10)

---

## Current Position

| Field | Value |
|-------|-------|
| Current Phase | Phase 10: Unified Inbox (not started) |
| Current Plan | — |
| Status | Roadmap complete — awaiting phase planning |
| Last Updated | 2026-03-21 |
| Last activity | 2026-03-21 — v2.0 roadmap created (7 phases, 37 requirements) |

**Progress bar:** [ ] [ ] [ ] [ ] [ ] [ ] [ ]  0/7 phases complete

---

## Accumulated Context

### Key Decisions Made

- All v1.0 key decisions still apply (see below)
- **v2.0 scope**: 7 major features (unified inbox, RFI automation, auto-reports, stakeholder map, decision tracker, change impact simulator, smart notifications)
- **Phase numbering**: v2.0 starts at Phase 10 (v1.0 ended at Phase 9)
- **Phase ordering rationale**: Inbox first (data foundation) → RFI + Decision Tracker (immediate PM value) → Stakeholder Map (communication graph) → Change Impact Simulator (analytical layer) → Reports (synthesis of all data) → Notifications (delivery layer tying everything together)
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

### v2.0 Phase Dependencies

```
Phase 10: Unified Inbox
    └── Phase 11: RFI/Submittal Automation
    └── Phase 12: Decision Tracker
    └── Phase 13: Stakeholder Communication Map
              └── Phase 14: Change Impact Simulator
    └── Phase 15: Auto-Generated Reports (also needs 12 + 14)
Phase 10-15 all feed:
    └── Phase 16: Smart Notifications
```

---

## Session Continuity

### To Resume Work

1. Read this STATE.md to understand current position
2. Read `.planning/ROADMAP.md` for v2.0 phase structure (Phases 10-16)
3. Read `.planning/REQUIREMENTS.md` for requirement details
4. Begin with: `/gsd:plan-phase 10`

### Next Action

Run `/gsd:plan-phase 10` to decompose Phase 10 (Unified Inbox) into executable plans.

---
