from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AccRfiAutomationConfig:
    project_id: str
    output_root: Path
    log_path: Path
    db_path: Path
    rfi_base_url: str
    page_size: int
    poll_interval_seconds: int
    access_token: str | None
    client_id: str | None
    client_secret: str | None
    refresh_token: str | None
    scopes: str
    rfis_input_path: Path | None = None

    @classmethod
    def from_env(
        cls,
        *,
        project_id: str,
        rfis_input_path: str | Path | None = None,
        poll_interval_seconds: int = 300,
    ) -> "AccRfiAutomationConfig":
        root = Path(
            (os.getenv("GIGAI_ACC_RFI_ROOT") or "").strip()
            or Path.home() / "AppData" / "Local" / "GigAI" / "acc-rfi-automation"
        )
        root.mkdir(parents=True, exist_ok=True)
        return cls(
            project_id=project_id,
            output_root=root,
            log_path=root / "acc-rfi-automation.log",
            db_path=Path(os.getenv("GIGAI_ACC_RFI_DB_PATH") or root / "acc-rfi-automation.sqlite3"),
            rfi_base_url=(
                os.getenv("ACC_RFI_BASE_URL")
                or "https://developer.api.autodesk.com/construction/rfis/v3"
            ).strip().rstrip("/"),
            page_size=max(int(os.getenv("ACC_RFI_PAGE_SIZE") or "100"), 1),
            poll_interval_seconds=max(poll_interval_seconds, 5),
            access_token=(os.getenv("ACC_ACCESS_TOKEN") or "").strip() or None,
            client_id=(os.getenv("ACC_CLIENT_ID") or "").strip() or None,
            client_secret=(os.getenv("ACC_CLIENT_SECRET") or "").strip() or None,
            refresh_token=(os.getenv("ACC_REFRESH_TOKEN") or "").strip() or None,
            scopes=(os.getenv("ACC_TOKEN_SCOPES") or "data:read account:read").strip(),
            rfis_input_path=Path(rfis_input_path) if rfis_input_path else None,
        )

