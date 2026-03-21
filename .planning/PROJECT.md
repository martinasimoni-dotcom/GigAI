# PROJECT.md — GigAI

## What This Is

GigAI is an AI-powered construction project management platform that automates material change coordination, project/employee management, schedule predictions, and cross-stakeholder communication for construction PMs. It reduces 4+ hours of manual PM coordination to under 12 minutes per change.

## Core Value

Eliminate manual PM coordination burden by automating capture, enrichment, proposal generation, action execution, and communication — turning PMs from paperwork processors into decision-makers.

## Requirements

### Validated

- ✓ Event-driven AI pipeline (webhooks → normalize → route → enrich → propose → execute) — v1.0
- ✓ Fireflies transcript webhook + ACC webhook + Gmail/Calendar polling — v1.0
- ✓ Haiku LLM normalization and routing — v1.0
- ✓ ACC API integration with fallback — v1.0
- ✓ pgvector knowledge base with Voyage-3 embeddings — v1.0
- ✓ Sonnet 4 proposal generation with confidence scoring — v1.0
- ✓ Action gateway (email, task, calendar, drawing) — v1.0
- ✓ React dashboard with real-time SSE, accept/reject flow, audit log — v1.0
- ✓ Project library (30 projects, 6 categories, filters) — v1.0
- ✓ Employee library (30 employees, profession filters) — v1.0
- ✓ Schedule predictions (Primavera P6-style urgency/conflict/delay analysis) — v1.0
- ✓ GigAI learning engine (decision patterns → vector store) — v1.0
- ✓ Apple macOS dark mode dashboard aesthetic — v1.0

### Active

- [ ] Multi-source unified inbox — ingest all project comms, extract action items, route automatically
- [ ] RFI/Submittal automation — auto-draft responses from knowledge base, one-click send
- [ ] Auto-generated daily/weekly reports — status, risks, pending decisions, stakeholder summaries
- [ ] Stakeholder communication map — visual graph of who needs to know what, auto-draft personalized messages
- [ ] Decision tracker — log every decision across all channels, searchable, linked to proposals
- [ ] Change impact simulator — show schedule, budget, stakeholder ripple effects before approving changes
- [ ] Smart notifications — priority routing, urgency scoring per person, digest batching

### Out of Scope

- Mobile native app — web-first, responsive design sufficient for v2.0
- Real-time video integration — high complexity, low ROI for coordination
- Custom LLM fine-tuning — Claude API is sufficient without fine-tuning
- Multi-language support — English only for initial market

## Current Milestone: v2.0 Communication Intelligence

**Goal:** Transform GigAI from a material-change-only tool into a full communication intelligence platform that eliminates PM coordination chaos across all project communications.

**Target features:**
- Multi-source unified inbox
- RFI/Submittal automation
- Auto-generated reports (daily digest)
- Stakeholder communication map
- Decision tracker
- Change impact simulator
- Smart notifications with priority routing

**Research basis:** Academic research shows 29% of construction projects fail due to poor communication (PMI), 26% of rework caused by miscommunication, PMs spend 45% of time on manual admin. AI document automation cuts handling time in half. These features directly attack the #1 and #3 ranked problems in construction PM.

## Context

- **Stack:** Python 3.11+, FastAPI, Claude Sonnet 4 + Haiku 4.5, Voyage-3, PostgreSQL + pgvector, Google Cloud Pub/Sub, ACC API, React + Vite + Tailwind
- **Existing codebase:** Production-ready v1.0 with full pipeline, project/employee libraries, schedule engine, learning system
- **Prediction models:** All predictions must use proper statistical/ML models (earned value analysis, Monte Carlo simulation, Bayesian inference) — not heuristic guesses
- **Dashboard:** Apple macOS dark mode aesthetic with Inter font, warm grays, system colors
- **User:** Rafik — construction tech developer, prefers autonomous YOLO mode, production-quality code

## Constraints

- **Tech stack**: Must integrate with existing Python/FastAPI backend and React frontend — no new frameworks
- **Predictions**: Must use academically-grounded prediction models (earned value, Monte Carlo, Bayesian) — not heuristics
- **Quality**: Production-ready code — reliable, accurate, detailed
- **Design**: Maintain Apple macOS dark mode aesthetic consistency
- **LLMs**: Claude Sonnet 4 for complex analysis, Haiku 4.5 for classification/extraction

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Skip GSD research phase | Already completed domain research via brainstorming agent with academic sources | — Pending |
| v2.0 (major) not v1.1 | 7 major features = new capability tier, not incremental patch | — Pending |
| All 7 features in one milestone | Rafik wants comprehensive communication intelligence, not piecemeal delivery | — Pending |
| Earned value + Monte Carlo for predictions | Academic rigor required — not heuristic scoring | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-21 after v2.0 milestone initialization*
