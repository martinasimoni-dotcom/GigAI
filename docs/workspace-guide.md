# GigAI Workspace Guide

## Active Product Surface

The current app you run and validate is composed of:

- [src/gigai](../src/gigai): Python package for the backend pipeline and dashboard API.
- [src/gigai/dashboard](../src/gigai/dashboard): Dashboard app factory, routers, models, and mock data.
- [frontend](../frontend): Next.js dashboard UI.
- [tests](../tests): Backend tests for the canonical app.
- [config](../config): Runtime configuration and vocabularies.
- [docs](../docs): Current implementation and operations documentation.
- [revit-addon](../revit-addon): Revit integration scaffold.

## Clean Root Layout

- [.env.example](../.env.example)
- [.gitignore](../.gitignore)
- [README.md](../README.md)
- [pyproject.toml](../pyproject.toml)
- [requirements.txt](../requirements.txt)
- [start-api.ps1](../start-api.ps1)
- [START_BACKEND.bat](../START_BACKEND.bat)
- [START_FRONTEND.bat](../START_FRONTEND.bat)
- [START_HERE.txt](../START_HERE.txt)
- [QUICK_START.txt](../QUICK_START.txt)
- [SETUP.bat](../SETUP.bat)
- [setup.sh](../setup.sh)
- [move_to_trash.ps1](../move_to_trash.ps1)
- [trash_manager.py](../trash_manager.py)
- [config](../config)
- [docs](../docs)
- [frontend](../frontend)
- [revit-addon](../revit-addon)
- [src](../src)
- [tests](../tests)
- [trash](../trash)

Transient exception:

- `.pytest_tmp/` can remain temporarily when Windows keeps a test temp folder locked.

## Legacy or Reference Material

The workspace has been trimmed to the active runtime surface. Historical docs, prior archive content, and side-branch material were moved into the managed trash area.

- Optional integration repos, datasets, examples, and training utilities were moved into trash.
- Trash manifest: [trash/manifest.json](../trash/manifest.json)
- Trashed material store: [trash/items](../trash/items)

## Current Backend Layout

- [src/gigai/dashboard/dashboard_api.py](../src/gigai/dashboard/dashboard_api.py): Thin FastAPI app factory.
- [src/gigai/dashboard/routers/health.py](../src/gigai/dashboard/routers/health.py): Health and voice endpoints.
- [src/gigai/dashboard/routers/meetings.py](../src/gigai/dashboard/routers/meetings.py): Meeting detail, transcript, decisions, and revisions endpoints.
- [src/gigai/dashboard/routers/tasks.py](../src/gigai/dashboard/routers/tasks.py): Task list and task-status update endpoints.
- [src/gigai/dashboard/routers/dashboard.py](../src/gigai/dashboard/routers/dashboard.py): Summary, timeline, revisions, and team workload endpoints.
- [src/gigai/dashboard/routers/integrations.py](../src/gigai/dashboard/routers/integrations.py): Export, webhook, and WebSocket endpoints.
- [src/gigai/dashboard/mock_data.py](../src/gigai/dashboard/mock_data.py): Mock dataset builders used by the dashboard API.
- [src/gigai/dashboard/models.py](../src/gigai/dashboard/models.py): Shared Pydantic models for the dashboard surface.

## Cleanup Policy

- Add new runtime code under [src/gigai](../src/gigai) or [frontend](../frontend), not the workspace root.
- Treat one-off status files, archive folders, and branch snapshots as trash candidates unless they are updated to point at [README.md](../README.md), [docs/operations.md](./operations.md), or [docs/workspace-guide.md](./workspace-guide.md).
- Keep generated assets, caches, databases, logs, and model checkpoints out of source control via [.gitignore](../.gitignore).
