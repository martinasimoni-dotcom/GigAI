# GigAI — AI-Powered Construction Intelligence Platform

GigAI automates construction project coordination by capturing communications from meetings, emails, and ACC, processing them through an AI pipeline, and generating actionable proposals — reducing PM coordination time by 80%.

## Quick Start

### Prerequisites
- **Python 3.11+** — [python.org/downloads](https://python.org/downloads)
- **Node.js 18+** — [nodejs.org](https://nodejs.org)
- **PostgreSQL 16+** (optional) — system works without it using in-memory stores

### 1. Clone & Install

```bash
git clone https://github.com/martinasimoni-dotcom/Research-studio_GigAI.git
cd Research-studio_GigAI
git checkout New-York

# Backend
pip install -r requirements.txt

# Frontend
cd dashboard
npm install
cd ..
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your API keys. **Minimum required for the dashboard to work:**
- None — the app starts with sample data even without any keys

**For AI features (classification, proposal generation):**
- `ANTHROPIC_API_KEY` — get from [console.anthropic.com](https://console.anthropic.com)

**For full pipeline (embedding search, vector DB):**
- `VOYAGE_API_KEY` — get from [dash.voyageai.com](https://dash.voyageai.com)
- `DATABASE_URL` — PostgreSQL connection string

**For live data from Autodesk Construction Cloud:**
- `ACC_CLIENT_ID` + `ACC_CLIENT_SECRET` — from [aps.autodesk.com/myapps](https://aps.autodesk.com/myapps)
- `ACC_ACCOUNT_ID` + `ACC_PROJECT_ID`

### 3. Run

**Terminal 1 — Backend:**
```bash
python -m uvicorn src.main:app --reload --port 8080
```

**Terminal 2 — Frontend:**
```bash
cd dashboard
echo VITE_API_URL=http://localhost:8080 > .env
npm run dev
```

**Open:** [http://localhost:5173](http://localhost:5173)

### 4. Explore

The dashboard loads with sample data immediately:
- **Inbox** — 44 communications across email, meetings, ACC, internal
- **RFIs** — 17 auto-detected with AI draft responses
- **Decisions** — 8 captured from meetings and emails
- **Proposals** — AI-generated coordination proposals
- **Projects** — 30 construction projects across 6 categories
- **Team** — 30 employees with certifications and specializations
- **Schedule** — Primavera P6-style predictions with urgency scoring

API docs: [http://localhost:8080/docs](http://localhost:8080/docs) (interactive Swagger UI)

---

## What It Does

### v1.0 — Material Change Coordination
An event-driven AI pipeline that captures material changes from meetings and emails, enriches them with project context (ACC floor plans, knowledge base, historical patterns), generates coordinated action proposals (emails, tasks, calendar events, drawing markups), and executes approved actions automatically.

### v2.0 — Communication Intelligence
7 features that transform GigAI into a full communication intelligence platform:

| Feature | What It Does |
|---------|-------------|
| **Unified Inbox** | All project comms in one feed — AI-classified, action items extracted |
| **RFI Automation** | Auto-detects questions, drafts responses from knowledge base |
| **Decision Tracker** | Captures decisions from all channels, detects contradictions |
| **Stakeholder Map** | Notification chains by role, personalized message drafting |
| **Impact Simulator** | Earned Value Analysis + Monte Carlo simulation before approving changes |
| **Auto Reports** | Daily/weekly digests with AI-identified risks |
| **Smart Notifications** | Urgency + relevance scoring, 3-tier routing |

### ACC Integration
Pulls 16 data categories from Autodesk Construction Cloud: projects, users, companies, budgets, contracts, change orders, cost items, issues, RFIs, submittals, documents, locations, schedule, checklists, photos, daily logs.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+ / FastAPI |
| AI — Proposals | Claude Sonnet 4 |
| AI — Classification | Claude Haiku 4.5 |
| Embeddings | Voyage-3 (1024-dim) |
| Database | PostgreSQL 16 + pgvector |
| Frontend | React 18 + Vite + Tailwind |
| External APIs | Autodesk Construction Cloud, Fireflies.ai, Gmail |

## Tests

```bash
# Backend (235 tests)
python -m pytest tests/unit/ tests/api/ tests/output/ src/inbox/tests/ -q

# Frontend (16 tests)
cd dashboard && npx vitest run
```

## Docs

- `docs/GigAI_Technical_Report.pdf` — 11-page technical report
- `docs/GigAI_Presentation.pptx` — 10-slide executive presentation

Regenerate: `python scripts/generate_report.py`
