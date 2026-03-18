# GigAI Decision Intelligence Platform

This repository is the implementation baseline for the architecture in your diagram.

## Canonical Docs
1. `README.md` for the product and architecture overview.
2. `docs/operations.md` for startup, health-check, and test commands.
3. `docs/workspace-guide.md` for active code paths versus legacy/reference material.
4. `docs/clean-structure.md` for the cleaned workspace tree.

## Target Outcome
Build an AI-assisted BIM 360 decision system that:
1. Ingests project activity from BIM 360 and collaboration channels.
2. Routes events through policy + orchestration.
3. Uses RAG and specialized agents to generate decisions.
4. Applies authority thresholds to auto-act or request PM approval.
5. Writes outcomes back to BIM 360, dashboard, and team notifications.

## System Blocks Mapped From Diagram
1. Connectors Layer
- BIM 360 connectors: auth, webhook, API polling, normalization, writeback queue.
- Collaboration connectors: Gmail/calendar/notetaker/profiles.

2. Policy Gate
- Event classification (LLM or rules).
- Context enrichment.
- Security checks.
- Priority scoring (0-100).

3. Supervisor
- Maintains project state DB and team knowledge graph.
- Coordinates agent fan-out and context packaging.
- Resolves cross-agent conflicts before decision synthesis.

4. Search Foundation (RAG)
- Indexer: periodic BIM 360 + communication refresh.
- Retriever: semantic/hybrid search.
- Vector store + metadata filters.

5. Agent Layer
- Understanding agents: RFIs, issues, schedule, email/meeting.
- Forecasting agents: schedule and risk projections.

6. Decision Intelligence
- Aggregates agent outputs.
- Applies BIM 360 constraints and conflict resolution.
- Produces confidence-calibrated decision packages.

7. Communication Intelligence
- Formats outputs for dashboard, BIM 360 comments/updates, and email.
- Handles concurrent-write merge logic.

8. Action Gateway (Authority Boundary)
- If confidence >= threshold and no blockers: auto-execute.
- Else route to PM approval workflow.
- Every action is logged with evidence.

9. Output Layer
- GigAI dashboard entries.
- BIM 360 update/comment.
- Team notifications.

## Delivery Artifacts
- [Implementation plan](docs/implementation-plan.md)
- [System contracts](docs/system-contracts.md)
- [MVP code scaffold](src/gigai/main.py)

## Recommended MVP Sequence
1. End-to-end path for one event type (`issue.updated`).
2. RAG retrieval + two agents (`IssueAgent`, `RiskAgent`).
3. Confidence gate + manual approval path.
4. BIM 360 writeback + dashboard log + email notice.

## Definition of Done (MVP)
1. An incoming BIM 360 event produces a decision package with evidence.
2. System can auto-apply low-risk actions and defer medium/high-risk to PM.
3. Action and rationale are traceable in dashboard logs.
4. Retry-safe, idempotent writeback and notification flows.

## Quick Start
1. Create environment and install dependencies:
`pip install -e .[dev]`

For Fireflies transcript integration:
`pip install -e .[dev,fireflies]`

2. Run API:
`python -m gigai`

Alternative:
`gigai-api`

No-install local launcher:
`.\start-api.ps1 -App dashboard -Reload`

Current dashboard backend layout:
`src/gigai/dashboard/dashboard_api.py`
`src/gigai/dashboard/routers/`
`src/gigai/dashboard/mock_data.py`

3. Run tests:
`pytest`

## Meeting Focus Shortcut
If someone says a space name in a meeting, send:

```json
{
  "projectId": "project_alpha",
  "type": "meeting.focus",
  "meeting_utterance": "Please focus on East Lobby and check the issue",
  "available_spaces": ["East Lobby", "West Lobby", "Roof"]
}
```

to `POST /meetings/focus`.
The pipeline auto-detects `East Lobby` and scopes decisioning to that space.

## Voice Command Shortcut
Send spoken text transcript to `POST /voice/command`:

```json
{
  "projectId": "project_alpha",
  "transcript": "GigAI focus on East Lobby and check the issue",
  "available_spaces": ["East Lobby", "West Lobby", "Roof"]
}
```

If `available_spaces` is omitted, the API extracts a space candidate from phrases like
`focus on <space>` and scopes the decision flow to that space.

### Fireflies Transcript Input
You can also source transcript text from a local Fireflies helper checkout if you restore one from `trash/` or point to an external folder.
Set env vars:
`GIGAI_FIREFLIES_ENABLED=true`
`FIREFLIES_API_KEY=...`
Optional:
`GIGAI_FIREFLIES_REPO_PATH=fireflies-raycast-main`

Then call `POST /voice/command` without `transcript`:

```json
{
  "projectId": "project_alpha",
  "fireflies_latest": true,
  "available_spaces": ["East Lobby", "West Lobby"]
}
```

or by specific Fireflies transcript id:

```json
{
  "projectId": "project_alpha",
  "fireflies_transcript_id": "your_transcript_id",
  "available_spaces": ["East Lobby", "West Lobby"]
}
```

### Architecture Reference Correction
Voice transcripts are corrected using an architecture reference dictionary before focus extraction.
Default reference path:
`config/architecture_reference.json`
Optional env override:
`GIGAI_ARCH_REFERENCE_PATH=...`

If you want to regenerate a larger architecture dataset and refresh the reference file:
restore `generate_massive_dataset.py` from `trash/` and run:
`python generate_massive_dataset.py --reference-only`

### LLM Layer
Space understanding now goes through a dedicated layer:
`src/gigai/llm.py`

This layer takes:
1. transcript
2. available spaces from Revit
3. drawing context (view name/type/scale)

and returns the best focus space with confidence/reason.

### Rafik LLM Bridge (Claude)
You can enable a Rafik-style Claude inference pass for voice-to-space mapping before the local matcher:
`src/gigai/rafik_llm.py`

Set env vars:
`GIGAI_RAFIK_LLM_ENABLED=true`
`ANTHROPIC_API_KEY=...`
Optional:
`GIGAI_RAFIK_LLM_MODEL=claude-haiku-4-5-20251001`

Behavior:
1. If enabled and credentials are available, backend asks Claude to choose one space from `available_spaces`.
2. If Claude is unavailable or returns no safe match, GigAI falls back to the existing local inference layer.
3. Revit marking flow continues unchanged; it just gets stronger focus-space detection.

### Project Glossary
You can customize architectural vocabulary without code changes using:
`config/project_glossary.json`

Supports:
1. `term_normalization`: speech/firm term normalization.
2. `space_aliases`: per-space alias phrases.

Set custom path if needed:
`$env:GIGAI_PROJECT_GLOSSARY=\"C:\\path\\to\\project_glossary.json\"`

## Revit Add-in
Revit integration scaffold is available at:
`revit-addon/`

Setup/build/install steps:
`revit-addon/README.md`

The Revit dialog includes:
1. `Start Mic` / `Stop Mic` for laptop microphone dictation.
2. `Test API` to validate local API connectivity before sending.

## BIM 360 / ACC Live Writeback
By default, the API runs in local fallback mode and returns mocked BIM 360 statuses.
To enable real BIM 360/ACC writeback from the action gateway:

1. Create an APS app and copy `Client ID` + `Client Secret`.
2. Find your BIM 360 Issues `container id` (project container for issue endpoints).
3. Set env vars (see `.env.example`):
`GIGAI_BIM360_ENABLED=true`
`GIGAI_BIM360_CLIENT_ID=...`
`GIGAI_BIM360_CLIENT_SECRET=...`
`GIGAI_BIM360_CONTAINER_ID=...`
Optional per-project mapping:
`GIGAI_BIM360_PROJECT_MAP_PATH=config/bim360_project_map.json`
4. Restart API:
`.\start-api.ps1 -Reload`

When enabled:
1. `create_issue_note` proposals call BIM 360 issue creation.
2. Other auto-executed proposals attempt comment writeback on the linked issue (`artifactId` / `issue_id`).
3. If BIM 360 call fails, pipeline still completes and action output includes `bim360=writeback_failed`.

Container ID resolution order:
1. Event payload (`container_id`, `containerId`, or `bim360_container_id`).
2. Project map file (`config/bim360_project_map.json`).
3. Default env container (`GIGAI_BIM360_CONTAINER_ID`).

## Google Calendar + Gmail Integration
Google email and calendar execution is now implemented in a dedicated folder:
`src/gigai/google_integrations/`

Main action flow (`src/gigai/action_gateway.py`) now attempts:
1. Gmail notification send via Google API.
2. Google Calendar event creation via Google API.

Required env vars:
`GIGAI_GOOGLE_INTEGRATION_ENABLED=true`
`GMAIL_CLIENT_ID=...`
`GMAIL_CLIENT_SECRET=...`
`GMAIL_REFRESH_TOKEN=...`
`GOOGLE_CALENDAR_ID=primary`

Optional default recipients:
`GIGAI_NOTIFICATION_EMAILS=pm@example.com,team@example.com`

Behavior when credentials are missing:
1. Pipeline still completes.
2. Outputs mark Google email/calendar as `skipped`.

### Deployed API Endpoint (Revit)
The Revit add-in can default to your deployed API endpoint via env vars:
`GIGAI_API_URL=https://your-deployed-api.example.com/voice/command`
`GIGAI_PROJECT_ID=your_project_id`

If these are set on the machine, the Revit voice dialog pre-fills them automatically.
