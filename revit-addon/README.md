# Revit Integration (GigAI Voice Focus + Revision Sync)

This add-in now supports a Whisper-backed microphone workflow:
1. `Voice Focus`: records microphone audio in Revit, sends it to GigAI `/voice/command/audio`, resolves the target space, and creates the Revit revision mark locally.
2. `GigAI Sync`: ingests external JSON revision events and automatically creates `Revision` + `RevisionCloud` in Revit.

The revision sync pipeline is still file and webhook driven:

External AI System (GigAI) -> JSON inbox file or local webhook -> Revit listener -> ExternalEvent -> Transactional Revit update

## 1. Prerequisites

1. Revit installed. Default target is Revit 2024 API.
2. Python virtual environment available in the repo root at `.venv`.
3. .NET Framework 4.8 targeting pack and build tools.
4. Whisper dependencies installed for the backend if you want microphone transcription from Revit.

## 2. Fast Test Commands

From repo root, run these commands in order.

Install backend dependencies:

```powershell
.venv\Scripts\python.exe -m pip install -e ".[whisper-stt]"
```

Start the GigAI orchestrator API on port `8011`:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-api.ps1 -App orchestrator -Port 8011
```

Build the Revit add-in:

```powershell
dotnet build .\revit-addon\GigAi.RevitAddin\GigAi.RevitAddin.csproj -c Debug
```

Install the add-in and preconfigure the local API values used by the dialog:

```powershell
powershell -ExecutionPolicy Bypass -File .\revit-addon\install-addin.ps1 `
  -RevitVersion 2024 `
  -Configuration Debug `
  -TargetFramework net48 `
  -ConfigureUserEnvironment `
  -ApiUrl http://127.0.0.1:8011 `
  -ProjectId project_alpha
```

If your Revit API DLLs are in a different folder, build with:

```powershell
dotnet build .\revit-addon\GigAi.RevitAddin\GigAi.RevitAddin.csproj -c Debug -p:RevitInstallDir="C:\Program Files\Autodesk\Revit 2025"
```

## 3. What To Do In Revit

1. Restart Revit after install.
2. Open any project with rooms or areas.
3. Open the `GigAI` ribbon tab.
4. Click `Voice Focus`.
5. Speak while the dialog shows `Mic: recording`.
6. Click `Stop Mic`.
7. Click `Send`.
8. The add-in sends the recorded WAV audio to the local GigAI API, receives the Whisper transcript and decision response, then creates the revision cloud and note in Revit.

If you do not want to use audio, you can still type directly in the transcript box and send a text command.

## 4. Expected Local Endpoints

The add-in uses these backend routes:

1. `POST http://127.0.0.1:8011/voice/command/audio` for recorded microphone audio.
2. `POST http://127.0.0.1:8011/voice/command` for typed transcript fallback.
3. `POST http://127.0.0.1:8011/revit/revision-marked` after the Revit mark is created.
4. `GET http://127.0.0.1:8011/health` for connection checks.

## 5. Installer Behavior

Installer script:

`revit-addon/install-addin.ps1`

What it does:
1. Copies the built DLL into `%APPDATA%\Autodesk\Revit\Addins\<version>`.
2. Updates the `.addin` manifest to point at the installed DLL.
3. If `-ConfigureUserEnvironment` is passed, it also writes:
   `GIGAI_API_URL`
   `GIGAI_PROJECT_ID`
   `GIGAI_PROJECT_ROOT`

Example:

```powershell
powershell -ExecutionPolicy Bypass -File .\revit-addon\install-addin.ps1 -ConfigureUserEnvironment
```

## 6. Revision Sync Inputs

Default inbox folder:

`%LOCALAPPDATA%\GigAI\revit\inbox`

Override with environment variable:

`GIGAI_REVIT_INBOX=C:\custom\gigai\inbox`

Sample payload:

`revit-addon/example-create-revision.json`

```json
{
  "action": "create_revision",
  "description": "Door size updated after coordination meeting",
  "view_name": "Level 1",
  "coordinates": [[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 10, 0]]
}
```

## 7. HTTP/Webhook Input For Sync

Default local endpoint:

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

## 8. Logging

Default log file:

`%LOCALAPPDATA%\GigAI\revit\gigai-revit-addon.log`

Override with:

`GIGAI_REVIT_LOG=C:\logs\gigai-revit-addon.log`

## 9. Notes

1. Revision clouds are created only in supported non-3D graphical views or sheets.
2. Coordinates in sync payloads are treated as Revit internal units, feet.
3. All model changes are wrapped in a Revit `Transaction`.
4. The add-in now depends on the GigAI backend for Whisper transcription when you use microphone recording.
5. If the backend is not running, typed transcript entry still works through `/voice/command`.
