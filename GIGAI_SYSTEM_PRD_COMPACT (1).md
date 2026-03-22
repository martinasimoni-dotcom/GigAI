# GIGAI - System Implementation Guide

**AI-Powered Material Change Coordinator for Construction**

---

## ARCHITECTURE

```
INPUT (Fireflies/ACC webhooks) 
  ↓ 
Google Cloud Pub/Sub
  ↓
PROCESSING
├─ Normalization (Claude Haiku 4.5)
├─ Enrichment (ACC API + Knowledge)  
├─ Historical (PostgreSQL + pgvector)
├─ Proposal Generation (Claude Sonnet 4)
└─ Confidence Scoring (80% threshold)
  ↓
OUTPUT
├─ React Dashboard (PRIMARY)
├─ ACC Notification (SECONDARY)
├─ Email Alert (FALLBACK)
└─ Action Gateway → Feedback Loop
```

---

## PROJECT STRUCTURE

```
gigai/
├── .env.example, .env, .gitignore, requirements.txt, docker-compose.yml
├── backend/
│   ├── main.py, config.py
│   ├── api/ (webhooks.py, proposals.py)
│   ├── services/ (normalization.py, proposal_generator.py, confidence_scorer.py)
│   ├── integrations/ (acc_client.py, claude_client.py)
│   ├── models/ (database.py, schemas.py)
│   └── data/demo/ (porthole_scenario.json)
├── frontend/
│   ├── package.json, vite.config.js, tailwind.config.js
│   ├── public/manifest.json
│   └── src/ (App.jsx, pages/Dashboard.jsx)
└── scripts/ (setup_database.py, run_demo.py)
```

---

## CORE FILES

### .env.example
```env
ACC_CLIENT_ID=
ACC_CLIENT_SECRET=
ACC_ACCESS_TOKEN=
ACC_PROJECT_ID=
ACC_CONTAINER_ID=
ANTHROPIC_API_KEY=
GCP_PROJECT_ID=
DATABASE_URL=postgresql://gigai:gigai@localhost:5432/gigai
APP_PORT=8000
FRONTEND_URL=http://localhost:5173
CONFIDENCE_AUTO_APPROVE_THRESHOLD=0.80
```

### requirements.txt
```
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
psycopg2-binary==2.9.9
pgvector==0.2.4
google-cloud-pubsub==2.19.0
anthropic==0.25.0
httpx==0.26.0
python-dotenv==1.0.0
pydantic-settings==2.1.0
websockets==12.0
```

### docker-compose.yml
```yaml
version: '3.8'
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: gigai
      POSTGRES_PASSWORD: gigai
      POSTGRES_DB: gigai
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
volumes:
  pgdata:
```

---

## BACKEND

### backend/config.py
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ACC_CLIENT_ID: str
    ACC_CLIENT_SECRET: str
    ACC_ACCESS_TOKEN: str | None = None
    ACC_PROJECT_ID: str | None = None
    ACC_CONTAINER_ID: str | None = None
    ANTHROPIC_API_KEY: str
    CLAUDE_HAIKU_MODEL: str = "claude-haiku-4-20250514"
    CLAUDE_SONNET_MODEL: str = "claude-sonnet-4-20250514"
    GCP_PROJECT_ID: str
    DATABASE_URL: str
    APP_PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:5173"
    CONFIDENCE_AUTO_APPROVE_THRESHOLD: float = 0.80
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### backend/models/database.py
```python
from sqlalchemy import create_engine, Column, String, Float, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base  
from sqlalchemy.orm import sessionmaker
from pgvector.sqlalchemy import Vector
from datetime import datetime
from config import settings

Base = declarative_base()

class Proposal(Base):
    __tablename__ = "proposals"
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    status = Column(String, default="pending")
    confidence = Column(Float)
    cost = Column(Float)
    actions = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    embedding = Column(Vector(1024))

class Decision(Base):
    __tablename__ = "decisions"
    id = Column(String, primary_key=True)
    proposal_id = Column(String)
    decision = Column(String)
    decided_at = Column(DateTime, default=datetime.utcnow)
    embedding = Column(Vector(1024))

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### backend/main.py
```python
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from models.database import init_db

app = FastAPI(title="GIGAI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    init_db()

@app.get("/")
def root():
    return {"status": "healthy"}

active_connections = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        active_connections.remove(websocket)

from api import webhooks, proposals
app.include_router(webhooks.router, prefix="/webhooks")
app.include_router(proposals.router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.APP_PORT)
```

### backend/integrations/acc_client.py
```python
import httpx
from config import settings

class ACCClient:
    BASE_URL = "https://developer.api.autodesk.com"
    
    def __init__(self):
        self.access_token = settings.ACC_ACCESS_TOKEN
        self.project_id = settings.ACC_PROJECT_ID
        self.container_id = settings.ACC_CONTAINER_ID
    
    def _headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    async def create_rfi(self, title: str, description: str):
        url = f"{self.BASE_URL}/construction/issues/v1/containers/{self.container_id}/issues"
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, 
                headers=self._headers(),
                json={"title": title, "description": description, "status": "open"}
            )
            return response.json()
    
    async def send_notification(self, message: str):
        # ACC notification (SECONDARY channel)
        pass
```

### backend/integrations/claude_client.py
```python
from anthropic import Anthropic
from config import settings

class ClaudeClient:
    def __init__(self):
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    
    async def extract_with_haiku(self, transcript: str) -> dict:
        """Normalization - Claude Haiku for fast extraction"""
        response = self.client.messages.create(
            model=settings.CLAUDE_HAIKU_MODEL,
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": f"Extract material change details from: {transcript}\nReturn JSON: location, material_from, material_to, quantity, elements, cost"
            }]
        )
        return response.content[0].text
    
    async def generate_proposal_with_sonnet(self, context: dict) -> dict:
        """Proposal Generation - Claude Sonnet 4 for complex reasoning"""
        response = self.client.messages.create(
            model=settings.CLAUDE_SONNET_MODEL,
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": f"Generate proposal from: {context}\nInclude: summary, cost analysis, 4 actions (email, RFI, calendar, markup), justification. Return JSON."
            }]
        )
        return response.content[0].text
```

### backend/api/webhooks.py
```python
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

router = APIRouter()

class FirefliesWebhook(BaseModel):
    transcript: str
    title: str
    participants: list

@router.post("/fireflies")
async def fireflies_webhook(data: FirefliesWebhook, background_tasks: BackgroundTasks):
    background_tasks.add_task(process_transcript, data.transcript)
    return {"status": "received"}

async def process_transcript(transcript: str):
    from integrations.claude_client import ClaudeClient
    from integrations.acc_client import ACCClient
    
    claude = ClaudeClient()
    acc = ACCClient()
    
    # Extract with Haiku
    extracted = await claude.extract_with_haiku(transcript)
    # Enrich with ACC data
    # Generate proposal with Sonnet
    proposal = await claude.generate_proposal_with_sonnet(extracted)
    # Calculate confidence
    # Save to DB
    # Notify dashboard (PRIMARY - WebSocket)
    # Send ACC notification (SECONDARY)
    # Send email if urgent (FALLBACK)
```

### backend/api/proposals.py
```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from models.database import get_db, Proposal, Decision
from integrations.acc_client import ACCClient

router = APIRouter()

@router.get("/proposals")
def get_proposals(db: Session = Depends(get_db)):
    return db.query(Proposal).filter(Proposal.status == "pending").all()

@router.post("/proposals/{id}/approve")
async def approve_proposal(id: str, db: Session = Depends(get_db)):
    proposal = db.query(Proposal).filter(Proposal.id == id).first()
    
    # Execute actions (Action Gateway)
    acc = ACCClient()
    for action in proposal.actions:
        if action["type"] == "acc_rfi":
            await acc.create_rfi(action["title"], action["description"])
    
    proposal.status = "approved"
    
    # Feedback Loop
    decision = Decision(id=f"decision_{id}", proposal_id=id, decision="approved")
    db.add(decision)
    db.commit()
    
    return {"status": "approved", "actions_executed": len(proposal.actions)}

@router.post("/proposals/{id}/reject")
def reject_proposal(id: str, reason: str, db: Session = Depends(get_db)):
    proposal = db.query(Proposal).filter(Proposal.id == id).first()
    proposal.status = "rejected"
    
    decision = Decision(id=f"decision_{id}", proposal_id=id, decision="rejected")
    db.add(decision)
    db.commit()
    
    return {"status": "rejected"}
```

---

## FRONTEND (Mobile-First)

### frontend/package.json
```json
{
  "name": "gigai-dashboard",
  "type": "module",
  "scripts": {
    "dev": "vite --host",
    "build": "vite build"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@tanstack/react-query": "^5.20.0",
    "axios": "^1.6.7",
    "lucide-react": "^0.330.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.1",
    "vite": "^5.1.0",
    "tailwindcss": "^3.4.1"
  }
}
```

### frontend/vite.config.js
```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': { target: 'ws://localhost:8000', ws: true }
    }
  }
})
```

### frontend/index.html
```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
    <meta name="theme-color" content="#2563eb" />
    <meta name="apple-mobile-web-app-capable" content="yes" />
    <link rel="manifest" href="/manifest.json" />
    <title>GigAI</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

### frontend/public/manifest.json
```json
{
  "name": "GigAI",
  "short_name": "GigAI",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#2563eb",
  "icons": [
    {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
    {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"}
  ]
}
```

### frontend/src/index.css
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  -webkit-font-smoothing: antialiased;
  overscroll-behavior: none;
}

button { min-height: 44px; min-width: 44px; }
```

### frontend/src/App.jsx
```jsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Dashboard from './pages/Dashboard'

const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchOnWindowFocus: false, retry: 1 } }
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Dashboard />
    </QueryClientProvider>
  )
}
```

### frontend/src/pages/Dashboard.jsx
```jsx
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { CheckCircle, XCircle, TrendingUp, Loader2 } from 'lucide-react'
import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export default function Dashboard() {
  const queryClient = useQueryClient()
  
  const { data: proposals, isLoading } = useQuery({
    queryKey: ['proposals'],
    queryFn: () => api.get('/proposals').then(r => r.data),
    refetchInterval: 15000
  })
  
  const approveMutation = useMutation({
    mutationFn: (id) => api.post(`/proposals/${id}/approve`),
    onSuccess: () => queryClient.invalidateQueries(['proposals'])
  })
  
  const rejectMutation = useMutation({
    mutationFn: (id) => api.post(`/proposals/${id}/reject`, { reason: '' }),
    onSuccess: () => queryClient.invalidateQueries(['proposals'])
  })
  
  const pending = proposals?.filter(p => p.status === 'pending') || []
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-white border-b shadow-sm">
        <div className="px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-xl flex items-center justify-center">
                <span className="text-white font-bold">Gi</span>
              </div>
              <div>
                <h1 className="text-xl font-bold">GigAI</h1>
                <p className="text-xs text-gray-500">Material Coordinator</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span className="text-xs">Live</span>
            </div>
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="px-4 py-4 space-y-4">
        {/* Stats */}
        <div className="bg-white rounded-2xl shadow-sm p-4">
          <div className="flex justify-between">
            <div>
              <p className="text-sm text-gray-600">Pending</p>
              <p className="text-3xl font-bold">{pending.length}</p>
            </div>
            <TrendingUp className="w-8 h-8 text-blue-600" />
          </div>
        </div>

        {/* Loading */}
        {isLoading && (
          <div className="flex justify-center py-12">
            <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
          </div>
        )}

        {/* Empty */}
        {!isLoading && pending.length === 0 && (
          <div className="bg-white rounded-2xl p-8 text-center">
            <p className="text-gray-600">No pending proposals</p>
          </div>
        )}

        {/* Proposals */}
        {pending.map(proposal => (
          <ProposalCard 
            key={proposal.id} 
            proposal={proposal}
            onApprove={() => approveMutation.mutate(proposal.id)}
            onReject={() => rejectMutation.mutate(proposal.id)}
            isApproving={approveMutation.isPending}
            isRejecting={rejectMutation.isPending}
          />
        ))}
      </main>
    </div>
  )
}

function ProposalCard({ proposal, onApprove, onReject, isApproving, isRejecting }) {
  const confidence = Math.round(proposal.confidence * 100)
  const isHigh = confidence >= 80
  
  return (
    <div className="bg-white rounded-2xl shadow-lg overflow-hidden">
      {/* Confidence */}
      <div className={`px-4 py-3 ${isHigh ? 'bg-green-50' : 'bg-yellow-50'}`}>
        <div className="flex justify-between">
          <span className="text-sm font-medium">Confidence</span>
          <span className={`text-lg font-bold ${isHigh ? 'text-green-700' : 'text-yellow-700'}`}>
            {confidence}%
          </span>
        </div>
        {isHigh && <p className="text-xs text-green-700 mt-1">✓ Auto-approve eligible</p>}
      </div>

      {/* Content */}
      <div className="p-4 space-y-4">
        <h3 className="text-lg font-bold">{proposal.title}</h3>
        
        <div className="flex justify-between py-3 px-4 bg-gray-50 rounded-xl">
          <span className="text-sm text-gray-600">Cost</span>
          <span className="text-xl font-bold">€{proposal.cost?.toLocaleString()}</span>
        </div>

        {/* Actions */}
        <div className="grid grid-cols-2 gap-3">
          <button
            onClick={onReject}
            disabled={isApproving || isRejecting}
            className="flex items-center justify-center gap-2 py-4 bg-gray-100 hover:bg-gray-200 disabled:bg-gray-50 rounded-xl font-semibold"
          >
            <XCircle className="w-5 h-5" />
            Reject
          </button>
          
          <button
            onClick={onApprove}
            disabled={isApproving || isRejecting}
            className="flex items-center justify-center gap-2 py-4 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white rounded-xl font-semibold shadow-lg"
          >
            {isApproving ? <Loader2 className="w-5 h-5 animate-spin" /> : <CheckCircle className="w-5 h-5" />}
            Accept
          </button>
        </div>
      </div>
    </div>
  )
}
```

---

## SCRIPTS

### scripts/setup_database.py
```python
from backend.models.database import init_db
init_db()
print("✅ Database created")
```

### scripts/run_demo.py
```python
import asyncio, httpx

async def trigger_demo():
    async with httpx.AsyncClient() as client:
        await client.post("http://localhost:8000/webhooks/fireflies", json={
            "transcript": "Marco: Upgrade attic porthole windows PVC to wood...",
            "title": "Design Review",
            "participants": []
        })
        print("✅ Demo triggered")

asyncio.run(trigger_demo())
```

---

## QUICK START

```bash
# 1. Setup
cp .env.example .env  # Fill with real API keys

# 2. Database
docker-compose up -d
python scripts/setup_database.py

# 3. Backend
cd backend
pip install -r ../requirements.txt
python main.py

# 4. Frontend (new terminal)
cd frontend
npm install
npm run dev

# 5. Demo
python scripts/run_demo.py

# 6. Access
# Computer: http://localhost:5173
# Phone: http://YOUR_IP:5173 (same WiFi)
# Add to home screen for PWA
```

---

## SUCCESS CRITERIA

1. ✅ Demo triggers → Creates proposal
2. ✅ Dashboard shows proposal (89% confidence)
3. ✅ Click Accept → Creates RFI in ACC
4. ✅ RFI appears in ACC project
5. ✅ Decision stored in PostgreSQL
6. ✅ WebSocket updates real-time
