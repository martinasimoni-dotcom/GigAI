Material Change Coordinator
An intelligent, event-driven workflow automation system for construction material change coordination. This system automatically processes material change events from meetings, project management tools, and calendars, then generates coordinated actions with AI-powered decision intelligence.

🎯 Project Overview
The Material Change Coordinator automates the complex workflow of tracking, approving, and executing material changes in construction projects. When a material change is mentioned (e.g., "Change 3rd floor windows from aluminum to wood frames"), the system:

Captures the event from multiple sources (Fireflies transcripts, ACC, Google Calendar)
Processes and normalizes the data into structured format
Enriches with context (floor plans, suppliers, team contacts, historical data)
Analyzes impact and generates intelligent actions (emails, tasks, calendar events, drawing markups)
Presents a proposal to the PM with confidence scoring
Executes approved actions automatically
Learns from decisions to improve future recommendations

🏗️ Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                         INPUT LAYER                          │
│  Fireflies • ACC • Google Calendar → Event Bus (Pub/Sub)    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                        SYSTEM LAYER                          │
│                                                              │
│  Event Normalization → Context Enrichment →                 │
│  Domain Processing → Decision Intelligence                  │
│                                                              │
│  (PostgreSQL + pgvector for historical data & learning)     │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                        OUTPUT LAYER                          │
│  Proposal Builder → PM Decision → Action Gateway            │
│  → Feedback & Learning Layer                                │
└─────────────────────────────────────────────────────────────┘
```

✨ Key Features

- Multi-Source Event Capture: Integrates with Fireflies (meeting transcripts), Autodesk Construction Cloud (ACC), and Google Calendar
- Intelligent Context Enrichment: Combines API data with pgvector semantic search (floor plans, team contacts, supplier database)
- AI-Powered Action Generation: Uses Claude Haiku (normalization/routing) + Claude Sonnet (proposal generation)
- Confidence Scoring: 4-factor weighted scoring (data clarity, historical match, cost acceptability, no red flags)
- Real-time Dashboard: SSE-powered React dashboard with accept/reject decision flow
- Event-Driven Architecture: Scalable, loosely-coupled design using Google Cloud Pub/Sub

🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker Desktop

### 1. Clone and install

```bash
git clone <your-repo-url>
cd Research-studio_GigAI

python -m venv .venv

# Windows:
.venv\Scripts\Activate.ps1
# Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Environment variables

Create a `.env` file in the project root with the following:

```
ANTHROPIC_API_KEY=your_key_here        # console.anthropic.com
VOYAGE_API_KEY=your_key_here           # dash.voyageai.com
DATABASE_URL=postgresql://gigai:gigai@localhost:5433/gigai
DEMO_MODE=true
```

### 3. Database setup (Docker)

```bash
# Start PostgreSQL with pgvector
docker run -d --name gigai-pg \
  -e POSTGRES_USER=gigai \
  -e POSTGRES_PASSWORD=gigai \
  -e POSTGRES_DB=gigai \
  -p 5433:5432 \
  pgvector/pgvector:pg16

# Enable the vector extension
docker exec -it gigai-pg psql -U gigai -d gigai -c "CREATE EXTENSION vector;"

# Create the knowledge table
docker exec -it gigai-pg psql -U gigai -d gigai -c "
CREATE TABLE IF NOT EXISTS knowledge_chunks (
  id SERIAL PRIMARY KEY,
  content TEXT NOT NULL,
  embedding vector(1024),
  source TEXT,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);"

# Seed demo knowledge data (optional but recommended)
python -m scripts.seed_demo
```

### 4. Start the backend

```bash
uvicorn src.main:app --reload
```

- API: http://localhost:8000
- Swagger docs: http://localhost:8000/docs

### 5. Start the dashboard

```bash
cd dashboard
npm install
npm run dev
```

- Dashboard: http://localhost:5173

### 6. Run the demo

Trigger the pipeline from Swagger at `http://localhost:8000/docs` → `POST /demo/trigger`

This simulates a Fireflies meeting transcript with a material change event (aluminum → wood windows, 3rd floor, Barcelona Tower) and pushes a live ranked proposal to the dashboard.

📋 Example Scenario

**Input:** Meeting transcript

> "We need to change the third floor windows from aluminum frames to wood frames. That's 12 units total."

**Processing:**

- Extracts: Material change (Aluminum → Wood), Location (3rd floor), Quantity (12 units)
- Enriches: Adds floor plan data, supplier info (Premium Wood Co., FSC-certified), historical precedents
- Analyzes: Identifies procurement need, schedule impact, stakeholder notifications
- Generates: Ranked proposal with 4 coordinated actions ready to execute

**Output:** Proposal with ~85% confidence showing accept/reject decision for the PM.

📁 Project Structure

```
src/
├── input/              # Connectors (Fireflies webhook, ACC, Google Calendar)
├── system/             # Core processing pipeline
│   ├── data_processing/    # Normalization + routing (Claude Haiku)
│   ├── context/            # Enrichment (pgvector search, ACC floor plans)
│   ├── domain_processing/  # Policy engine + signal generation
│   └── decision_intelligence/  # Proposal generation (Claude Sonnet)
├── output/             # Action execution (Gmail, ACC, Calendar)
├── api/                # FastAPI routes + SSE
├── demo/               # Demo pipeline runner
└── shared/             # Models, DB, LLM clients
config/
├── prompts/            # LLM prompt templates
├── event_types/        # YAML configs per event type
└── rules/              # Policy rules (YAML)
dashboard/              # React + Vite frontend
scripts/                # seed_demo.py
```

🔐 Security

- All API keys stored in environment variables (never committed to git)
- `.env` is gitignored — share keys out-of-band with teammates
- PM approval required for all proposals before actions execute
