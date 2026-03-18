# GigAI Clean File Structure

## Root

```text
GigAi/
├── .env.example
├── .gitignore
├── README.md
├── pyproject.toml
├── requirements.txt
├── start-api.ps1
├── START_BACKEND.bat
├── START_FRONTEND.bat
├── START_HERE.txt
├── QUICK_START.txt
├── SETUP.bat
├── setup.sh
├── move_to_trash.ps1
├── trash_manager.py
├── config/
├── docs/
├── frontend/
├── revit-addon/
├── src/
├── tests/
├── trash/
└── .venv/
```

Transient note:

- `.pytest_tmp/` may appear temporarily if a Python or test process is holding it open. It is not part of the intended project surface.

## Runtime Paths

- `src/`: Python backend package.
- `frontend/`: Next.js dashboard UI.
- `config/`: runtime JSON configuration.
- `revit-addon/`: Revit integration scaffold.
- `docs/`: current operational and structure docs.
- `tests/`: backend test suite.

## Important Subtrees

### Backend

```text
src/
└── gigai/
    ├── dashboard/
    │   ├── dashboard_api.py
    │   ├── mock_data.py
    │   ├── models.py
    │   └── routers/
    ├── meeting_intelligence/
    ├── revit/
    ├── main.py
    ├── orchestrator.py
    └── storage.py
```

### Frontend

```text
frontend/
├── app/
├── components/
├── lib/
├── package.json
└── tsconfig.json
```

### Docs

```text
docs/
├── clean-structure.md
├── implementation-plan.md
├── operations.md
├── system-contracts.md
└── workspace-guide.md
```

## Trashed Material

Everything removed during cleanup is recoverable from:

- `trash/manifest.json`
- `trash/items/`
