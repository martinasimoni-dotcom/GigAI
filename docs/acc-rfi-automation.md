# ACC RFI Automation

This feature adds a separate automation workflow for ACC RFIs.

Flow:

1. poll ACC RFI v3
2. normalize RFIs
3. for open RFIs only:
   send email
   create calendar event
4. store local idempotency state in SQLite
5. log every action

Entry point:

`python -m gigai.acc_rfi_automation --project-id <acc-project-id> --watch --interval-seconds 300`

Offline test:

```powershell
$env:PYTHONPATH='src'
$env:GIGAI_ACC_RFI_ROOT="$PWD\.acc-rfi"
.venv\Scripts\python.exe -m gigai.acc_rfi_automation `
  --project-id project_alpha `
  --rfis-input tests/fixtures/acc_rfi_automation/rfis_response.json
```
