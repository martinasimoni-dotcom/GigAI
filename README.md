# GigAI — AI-Powered Material Change Coordinator for Construction

> Transforms unstructured RFIs and meeting transcripts into structured change proposals in under 3 minutes, directly inside Autodesk Construction Cloud.

---

## The Problem

Material substitution requests are one of the most common sources of delay in construction projects. A Project Manager receiving an RFI about switching from PVC to teak wood windows must manually:

1. Read and interpret the request
2. Cross-check specs, costs, and supplier availability
3. Draft a formal proposal with cost breakdown
4. Route it to the right stakeholders
5. Create a new RFI or update the existing one in ACC

**Current reality:** 45 minutes average per change request — surveyed across 15 PMs. Up to 30% of that time is pure coordination overhead with no design value.

**GigAI reduces this to under 3 minutes** — a 99% time reduction — while keeping the PM in full control with a one-tap approve/reject interface.

---

## How It Works

```
1. DETECT    An RFI is created in Autodesk Construction Cloud
             (or a Fireflies meeting transcript is received via webhook)
                          ↓
2. GENERATE  Claude Haiku extracts the material change details.
             Claude Sonnet generates a structured proposal:
             cost breakdown, technical summary, recommended actions.
             A confidence score determines if human review is needed.
                          ↓
3. DECIDE    The PM sees the proposal on a mobile-first dashboard.
             One tap to Approve (creates ACC RFI + sends email)
             or Reject (closes source RFI + notifies team).
```

---

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│                   INPUT SOURCES                     │
│   ACC Webhook (RFI created)   Fireflies Transcript  │
│           ACC Poller (5-min fallback)               │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
         ┌─────────────────────────┐
         │   FastAPI Backend       │
         │                         │
         │  [1] Fetch RFI from ACC │
         │  [2] Resolve assignee   │
         │  [3] Claude Haiku       │ ◄── material extraction
         │  [4] Claude Sonnet      │ ◄── proposal + cost analysis
         │  [5] Confidence score   │ ◄── 80% auto-approve threshold
         │  [6] Send email (opt.)  │ ◄── Gmail OAuth
         │  [7] Save to PostgreSQL │
         │  [8] Broadcast via WS   │
         └────────────┬────────────┘
                      │ WebSocket
          ┌───────────▼───────────┐
          │   React Dashboard     │
          │   (mobile-first PWA)  │
          │                       │
          │  • Proposal cards     │
          │  • Confidence badge   │
          │  • Cost breakdown     │
          │  • Approve / Reject   │
          └───────────────────────┘
                      │ on Approve
          ┌───────────▼───────────┐
          │   ACC API             │
          │  • Create new RFI     │
          │  • Update source RFI  │
          │  • Email notification │
          └───────────────────────┘
                      │
          ┌───────────▼───────────┐
          │   Revit Plugin (.NET) │
          │  • Look up RFI by ID  │
          │  • View proposal info │
          └───────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Backend API | FastAPI + Uvicorn | Async REST API + WebSocket server |
| AI — Extraction | Claude Haiku 4.5 | Fast material detail extraction from RFI text |
| AI — Proposals | Claude Sonnet 4.6 | Structured proposal generation with cost analysis |
| ACC Integration | Autodesk Construction Cloud API | RFI read/create/update, user resolution |
| Database | PostgreSQL + pgvector | Proposal storage, decision history, vector embeddings |
| Frontend | React 18 + Vite + Tailwind CSS | Mobile-first PWA dashboard |
| Real-time | WebSockets | Live proposal delivery to dashboard |
| Email | Gmail API (OAuth2) | Optional email notifications to assignees |
| BIM Plugin | Revit .NET (C#) | In-model RFI lookup and proposal view |

---

## Key Metrics

| Metric | Value |
|---|---|
| Time per change request (before) | ~45 minutes |
| Time per change request (with GigAI) | ~3 minutes |
| Time reduction | 99% |
| Project managers surveyed | 15 |
| Adoption intent | 80% |
| Confidence threshold for auto-approval | 80% |
| ACC polling interval | 5 minutes |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (for PostgreSQL)
- Autodesk Platform Services app (CLIENT_ID + CLIENT_SECRET)
- Anthropic API key

### 1. Environment

```bash
cp .env.example .env
# Edit .env — fill in ANTHROPIC_API_KEY, ACC_CLIENT_ID, ACC_CLIENT_SECRET,
# ACC_HUB_ID, ACC_PROJECT_ID, ACC_CONTAINER_ID, DATABASE_URL
```

### 2. Database

```bash
docker-compose up -d
python scripts/setup_database.py
```

### 3. Backend

```bash
pip install -r requirements.txt
cd backend
python main.py
# Running at http://localhost:8000
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
# Running at http://localhost:5173
# Open on phone at http://YOUR_IP:5173 (same WiFi) — add to home screen for PWA
```

### 5. Run the demo

```bash
python scripts/run_demo.py
# Triggers the porthole window scenario — proposal appears on dashboard in ~10s
```

### Test connectivity

```bash
python scripts/test_claude_api.py
python scripts/test_acc_connection.py
python scripts/test_database.py
python scripts/test_gmail.py      # optional
```

---

## Key API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `GET` | `/api/proposals` | List pending proposals |
| `GET` | `/api/proposals/{id}` | Get single proposal |
| `POST` | `/api/proposals/{id}/approve` | Approve — creates ACC RFI, sends email |
| `POST` | `/api/proposals/{id}/reject` | Reject — closes source RFI, notifies team |
| `POST` | `/api/proposals/{id}/create-rfi` | Manually create ACC RFI from proposal |
| `POST` | `/api/proposals/{id}/send-email` | Resend email to assignee |
| `POST` | `/api/process-rfi` | Manually trigger pipeline for a given RFI ID |
| `POST` | `/webhooks/acc` | ACC webhook receiver (RFI created events) |
| `POST` | `/webhooks/fireflies` | Fireflies transcript webhook |
| `WS` | `/ws` | WebSocket — live proposal broadcast |

---

## Demo Scenario

The included demo replicates a real coordination scenario from a Sea House project:

**Trigger:** A site meeting transcript is received. The team discussed upgrading 6 porthole windows in the attic from PVC to solid teak wood.

**What GigAI does:**

1. Claude Haiku extracts: `location: attic`, `material_from: PVC`, `material_to: solid teak wood`, `quantity: 6`
2. Claude Sonnet generates a full change proposal with cost estimate (~€2,340), technical justification, and recommended actions
3. Confidence score: **~89%** (above the 80% threshold — auto-approve eligible)
4. Proposal appears on the dashboard within ~10 seconds
5. PM taps **Accept** → new RFI created in ACC, source RFI updated to "answered", email sent to assignee

Run it:
```bash
python scripts/run_demo.py
```

---

## Team

| Name | Contributions |
|---|---|
| **Martina Simoni** | Backend architecture, ACC integration, Claude AI pipeline, Revit plugin, database design |
| **Sumit Sudhir Shingne** | Frontend development, dashboard UX, React components, PWA configuration |
| **Rafik El Khoury** | Research, user research (15 PM surveys), system design, demo scenario |

---

## Project Status

**Status:** Research prototype — fully functional core system.

| Component | Status |
|---|---|
| RFI processing pipeline (8 steps) | Complete |
| React dashboard + WebSocket | Complete |
| ACC OAuth + RFI CRUD | Complete |
| Claude Haiku extraction | Complete |
| Claude Sonnet proposal generation | Complete |
| Confidence scoring | Complete |
| Gmail email notifications | Complete (optional) |
| PostgreSQL + pgvector | Complete |
| Revit .NET plugin | Built, untested in live Revit |
| pgvector semantic ranking | Schema ready, not yet wired |

This project is part of the **Master in Advanced Architecture (MAA)** Research Studio at [IAAC — Institute for Advanced Architecture of Catalonia](https://iaac.net), Barcelona, 2025–2026. It investigates how AI agents can reduce coordination overhead in the Architecture, Engineering and Construction (AEC) industry.

---

## License

MIT — see [LICENSE](LICENSE) for details.
