from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import sys, os, logging

sys.path.insert(0, os.path.dirname(__file__))

# ── Logging ───────────────────────────────────────────────────────────────────
# Write to stdout so uvicorn doesn't buffer it.
# force=True re-configures even if a library already called basicConfig.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
    force=True,
)
log = logging.getLogger("gigai")

from config import settings
from models.database import init_db

app = FastAPI(title="GIGAI", version="1.0.0")

cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
log.info("CORS allowed origins: %s", cors_origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.on_event("startup")
async def startup():
    try:
        init_db()
        log.info("Database initialized")
    except Exception as e:
        log.warning("Database init failed (run docker-compose up -d): %s", e)
    log.info("=" * 50)
    log.info("Backend ready -- auto-reload DISABLED")
    log.info("=" * 50)


@app.get("/")
def root():
    return {"status": "healthy", "service": "GIGAI Material Coordinator"}


@app.get("/health")
def health():
    log.info("GET /health called -- logging is working")
    return {"status": "ok", "logging": "working", "reload": "disabled"}


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)
        log.info("WebSocket connected (%d active)", len(self.active))

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, message: dict):
        import json
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()
app.state.ws_manager = manager


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


from api import webhooks, proposals

app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
app.include_router(proposals.router, prefix="/api", tags=["proposals"])


if __name__ == "__main__":
    import uvicorn
    # reload=False is critical -- reload kills in-flight async tasks mid-pipeline
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.APP_PORT,
        reload=False,
        log_level="info",
    )
