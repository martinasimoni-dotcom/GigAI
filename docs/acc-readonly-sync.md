# ACC Readonly Sync

This feature adds a separate, non-intrusive read-only workflow that:

1. reads ACC Issues and RFIs
2. normalizes only deterministic location data
3. writes a local snapshot JSON
4. tracks new and updated ACC records locally
5. places or updates Revit revision clouds and text markers from that snapshot

It does not modify GigAI pipelines and it does not write back to ACC.

## Components

Python extractor:

`python -m gigai.acc_readonly_sync --project-id <acc-project-id> --include-rfis`

Continuous local polling:

`python -m gigai.acc_readonly_sync --project-id <acc-project-id> --include-rfis --watch --interval-seconds 300`

Revit add-in command:

`GigAI` -> `Sync ACC Issues`

## Environment

Optional local root:

`GIGAI_ACC_SYNC_ROOT=%LOCALAPPDATA%\\GigAI\\acc-sync`

Optional explicit paths:

`GIGAI_ACC_SYNC_SNAPSHOT`
`GIGAI_ACC_SYNC_STATE`
`GIGAI_ACC_SYNC_CONFIG`

Authentication options for the extractor:

1. `ACC_ACCESS_TOKEN`
2. or `ACC_CLIENT_ID`, `ACC_CLIENT_SECRET`, `ACC_REFRESH_TOKEN`

## Local Files

Snapshot written by the extractor:

`%LOCALAPPDATA%\\GigAI\\acc-sync\\latest-acc-items.json`

Annotation state written by Revit:

`%LOCALAPPDATA%\\GigAI\\acc-sync\\annotation-state.json`

Extractor source-state written locally:

`%LOCALAPPDATA%\\GigAI\\acc-sync\\source-state.json`

Optional config:

`%LOCALAPPDATA%\\GigAI\\acc-sync\\config.json`

Use [config/acc_readonly_sync.sample.json](../config/acc_readonly_sync.sample.json) as the starting point.

## Offline Test Run

Use the included fixtures:

```powershell
.venv\Scripts\python.exe -m gigai.acc_readonly_sync `
  --project-id project_alpha `
  --include-rfis `
  --issues-input tests/fixtures/acc_readonly_sync/issues_response.json `
  --rfis-input tests/fixtures/acc_readonly_sync/rfis_response.json
```

This writes a 3-item snapshot that can be used to test the Revit sync command locally.

## Notes

- Items without coordinates or element references are ignored.
- Extractor logs new versus updated ACC records deterministically using a local source-state file.
- Watch mode can keep the local ACC snapshot refreshed on a fixed polling interval.
- Existing managed annotations are updated instead of duplicated.
- Stale managed annotations are removed when they disappear from the latest snapshot.
- Mapping is deterministic: direct element match first, then nearest element by coordinates.
