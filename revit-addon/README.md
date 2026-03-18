# Revit Integration (GigAI Voice Focus + Revision Sync)

This add-in provides two production-oriented workflows:
1. `Voice Focus`: sends transcript text to GigAI `/voice/command` and focuses model spaces.
2. `GigAI Sync`: ingests external JSON revision events and automatically creates `Revision` + `RevisionCloud` in Revit.

The revision sync pipeline is file-event driven:

External AI System (GigAI) → JSON inbox file or local webhook → Revit listener → ExternalEvent → Transactional Revit update

## 1. Prerequisites

1. Revit installed (default project target: Revit 2024 API).
2. GigAI API running locally:
`powershell -ExecutionPolicy Bypass -File ..\start-api.ps1 -Reload`
3. .NET Framework 4.8 targeting pack and build tools.

## 2. Build

From repo root:

```powershell
dotnet build .\revit-addon\GigAi.RevitAddin\GigAi.RevitAddin.csproj -c Debug
```

If your Revit API DLLs are in a different folder, pass:

```powershell
dotnet build .\revit-addon\GigAi.RevitAddin\GigAi.RevitAddin.csproj -c Debug -p:RevitInstallDir="C:\Program Files\Autodesk\Revit 2025"
```

## 3. Install

Close Revit before installing/updating the add-in DLL.

```powershell
powershell -ExecutionPolicy Bypass -File .\revit-addon\install-addin.ps1 -RevitVersion 2024 -Configuration Debug -TargetFramework net48
```

This writes:
1. `%APPDATA%\Autodesk\Revit\Addins\2024\GigAi.RevitAddin.dll`
2. `%APPDATA%\Autodesk\Revit\Addins\2024\GigAi.RevitAddin.addin`

## 4. Use in Revit

1. Restart Revit.
2. Open the `GigAI` ribbon tab.
3. For speech workflow, click `Voice Focus` and follow the dialog.
4. For revision workflow, click `GigAI Sync` to process any pending JSON files from the GigAI inbox.

## 5. Revision Sync Inputs

Default inbox folder:

`%LOCALAPPDATA%\GigAI\revit\inbox`

Override with environment variable:

`GIGAI_REVIT_INBOX=C:\custom\gigai\inbox`

Sample payload (`revit-addon/example-create-revision.json`):

```json
{
	"action": "create_revision",
	"description": "Door size updated after coordination meeting",
	"view_name": "Level 1",
	"coordinates": [[0,0,0],[10,0,0],[10,10,0],[0,10,0]]
}
```

Processing behavior:
1. Add-in validates payload.
2. Creates `Revision` with description + issued flag.
3. Finds target view by exact name (case-insensitive).
4. Creates `RevisionCloud` using curve geometry derived from coordinates.
5. Links revision to cloud via `RevisionCloud.Create(document, view, revisionId, curves)`.
6. Archives source files to sibling `processed` / `failed` folders.

## 6. HTTP/Webhook Input (Direct)

Default local endpoint (enabled by default):

`POST http://127.0.0.1:8765/gigai/revit/revisions`

Environment variables:
1. `GIGAI_REVIT_HTTP_ENABLED=true|false`
2. `GIGAI_REVIT_HTTP_PREFIX=http://127.0.0.1:8765/`
3. `GIGAI_REVIT_HTTP_ROUTE=/gigai/revit/revisions`

PowerShell test:

```powershell
$body = Get-Content -Raw .\revit-addon\example-create-revision.json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8765/gigai/revit/revisions" -ContentType "application/json" -Body $body
```

Expected response:

`{ "status": "accepted", "request_id": "..." }`

## 7. Logging & Audit

Default log file:

`%LOCALAPPDATA%\GigAI\revit\gigai-revit-addon.log`

Override with environment variable:

`GIGAI_REVIT_LOG=C:\logs\gigai-revit-addon.log`

Each entry includes UTC timestamp, severity, action details, and exceptions.

## 8. Notes

1. Revision clouds are created only in supported non-3D graphical views/sheets.
2. Coordinates are treated as Revit internal units (feet).
3. All model changes are wrapped in a Revit `Transaction` with rollback on failure.
4. The listener is event-driven (`FileSystemWatcher`) and avoids polling.

## 9. Use Deployed API Instead Of Localhost
Set machine/user environment variables:

```powershell
[System.Environment]::SetEnvironmentVariable("GIGAI_API_URL", "https://your-api.example.com/voice/command", "User")
[System.Environment]::SetEnvironmentVariable("GIGAI_PROJECT_ID", "your_project_id", "User")
```

Restart Revit. The voice dialog will pre-fill these values automatically.

## 10. Extend for Approval Workflow

The architecture is prepared for human-in-the-loop approval:
1. Keep `GigAiRevisionEventHandler` as the Revit API execution boundary.
2. Add a pre-enqueue policy gate for risk/confidence thresholds.
3. Reuse runtime queueing (`Enqueue + ExternalEvent.Raise`) for thread-safe execution.
4. Add approval gating before enqueue for human-in-the-loop workflows.
