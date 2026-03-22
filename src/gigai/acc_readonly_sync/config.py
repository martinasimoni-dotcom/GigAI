from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AccReadonlySyncConfig:
    project_id: str
    include_rfis: bool
    output_path: Path
    log_path: Path
    state_path: Path
    access_token: str | None
    client_id: str | None
    client_secret: str | None
    refresh_token: str | None
    scopes: str
    issues_base_url: str
    rfis_base_url: str
    page_size: int
    issues_input_path: Path | None = None
    rfis_input_path: Path | None = None

    @classmethod
    def from_env(
        cls,
        *,
        project_id: str,
        include_rfis: bool,
        output_path: str | Path | None = None,
        issues_input_path: str | Path | None = None,
        rfis_input_path: str | Path | None = None,
    ) -> "AccReadonlySyncConfig":
        root = Path(
            (os.getenv("GIGAI_ACC_SYNC_ROOT") or "").strip()
            or Path.home() / "AppData" / "Local" / "GigAI" / "acc-sync"
        )
        root.mkdir(parents=True, exist_ok=True)

        resolved_output = Path(output_path) if output_path else root / "latest-acc-items.json"
        resolved_log = root / "acc-readonly-sync.log"
        return cls(
            project_id=project_id,
            include_rfis=include_rfis,
            output_path=resolved_output,
            log_path=resolved_log,
            state_path=root / "source-state.json",
            access_token=(os.getenv("ACC_ACCESS_TOKEN") or "").strip() or None,
            client_id=(os.getenv("ACC_CLIENT_ID") or "").strip() or None,
            client_secret=(os.getenv("ACC_CLIENT_SECRET") or "").strip() or None,
            refresh_token=(os.getenv("ACC_REFRESH_TOKEN") or "").strip() or None,
            scopes=(
                os.getenv("ACC_TOKEN_SCOPES")
                or "data:read account:read"
            ).strip(),
            issues_base_url=(
                os.getenv("ACC_ISSUES_BASE_URL")
                or "https://developer.api.autodesk.com/construction/issues/v1"
            ).strip().rstrip("/"),
            rfis_base_url=(
                os.getenv("ACC_RFIS_BASE_URL")
                or "https://developer.api.autodesk.com/construction/rfis/v3"
            ).strip().rstrip("/"),
            page_size=max(int(os.getenv("ACC_PAGE_SIZE") or "100"), 1),
            issues_input_path=Path(issues_input_path) if issues_input_path else None,
            rfis_input_path=Path(rfis_input_path) if rfis_input_path else None,
        )
