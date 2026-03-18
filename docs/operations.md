# GigAI Operations Guide

## Canonical Startup

### Backend

From the workspace root:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-api.ps1 -App dashboard -Reload
```

Alternative:

```powershell
.\.venv\Scripts\python.exe -m uvicorn gigai.dashboard.dashboard_api:create_dashboard_app --factory --app-dir src --reload --host 127.0.0.1 --port 8000
```

### Frontend

From [frontend](../frontend):

```powershell
npm run dev
```

## Health Checks

```powershell
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/revisions
curl http://127.0.0.1:8000/api/dashboard/architects
```

Frontend:

- Dashboard: <http://localhost:3000>
- API docs: <http://localhost:8000/docs>
- API redoc: <http://localhost:8000/redoc>

## Test Commands

Backend contract tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_dashboard_api_contracts.py tests/test_api_contracts.py
```

Full backend test suite:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

End-to-end simulation test:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_system_e2e_simulation.py -q
```

Manual end-to-end simulation API call:

```powershell
curl -X POST http://127.0.0.1:8000/system/e2e/simulate -H "Content-Type: application/json" -d '{"project_id":"project_alpha","meeting_id":"meet_01","transcript":"GigAI focus on East Lobby and create revision cloud for window frame change","available_spaces":["East Lobby","West Lobby"],"assign_to":"architect_1","notification_emails":["pm@gigai.local"]}'
```

Frontend checks:

```powershell
cd frontend
npm run type-check
npm run build
```

## Active Runtime Entry Points

- Backend app factory: [src/gigai/dashboard/dashboard_api.py](../src/gigai/dashboard/dashboard_api.py)
- Backend routers: [src/gigai/dashboard/routers](../src/gigai/dashboard/routers)
- Dashboard mock data: [src/gigai/dashboard/mock_data.py](../src/gigai/dashboard/mock_data.py)
- Frontend API client: [frontend/lib/api.ts](../frontend/lib/api.ts)
- Frontend pages: [frontend/app](../frontend/app)

## Legacy Notes

Historical docs and legacy root artifacts have been moved into the managed trash area.

- Trash manifest: [trash/manifest.json](../trash/manifest.json)
- Trash items: [trash/items](../trash/items)
