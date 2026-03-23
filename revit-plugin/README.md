# GigAI Revit Plugin

A minimal Revit 2026 plugin that lets you search for an RFI proposal in the GigAI backend directly from the Revit ribbon.

---

## Prerequisites

| Requirement | Version |
|---|---|
| Autodesk Revit | 2026 |
| .NET SDK | 4.8+ (included with Visual Studio / Build Tools) |
| GigAI backend | running on `http://localhost:8000` |

---

## 1 — Build

```powershell
cd revit-plugin
dotnet build GigAi.RevitPlugin/GigAi.RevitPlugin.csproj --configuration Release
```

The compiled output lands in:
```
GigAi.RevitPlugin/bin/Release/net48/
```

---

## 2 — Install

Run the installer script (PowerShell, no admin required):

```powershell
.\install-plugin.ps1
```

This copies `GigAi.RevitPlugin.dll`, `Newtonsoft.Json.dll`, and `GigAi.addin` to:

```
%APPDATA%\Autodesk\Revit\Addins\2026\
```

---

## 3 — Usage in Revit

1. Start (or restart) Revit 2026.
2. Open any project.
3. In the ribbon, click the **GigAI** tab.
4. Click **Locate RFI**.
5. Enter an RFI ID (e.g. `RFI-001`) and click **Find in Model**.
6. A message box displays:

```
RFI:      <title>
Location: <location>
Material: <material_from> → <material_to>
Cost:     €<cost>
Status:   <status>
```

---

## 4 — API endpoint used

```
GET http://localhost:8000/api/proposals?source_rfi_id={rfi_id}
```

No authentication — localhost only.

---

## 5 — Troubleshooting

| Symptom | Fix |
|---|---|
| "GigAI" tab not visible | Check `%APPDATA%\Autodesk\Revit\Addins\2026\` for `GigAi.addin` and `GigAi.RevitPlugin.dll` |
| "Could not reach GigAI backend" | Ensure `python start_backend.bat` (or equivalent) is running and listening on port 8000 |
| Build fails — RevitAPI.dll not found | Verify Revit 2026 is installed at `C:\Program Files\Autodesk\Revit 2026\` |
| Empty response / "No proposal found" | Check that the RFI ID exists in the database and the backend is healthy (`GET http://localhost:8000/health`) |
