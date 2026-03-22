from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)


def _safe_int(value: str | None, default: int) -> int:
    """Safely parse an integer environment variable with a fallback default."""
    if not value:
        return default
    try:
        parsed = int(value.strip())
        return max(parsed, 1)
    except ValueError:
        return default


def _resolve_config_root() -> Path:
    """Resolve platform-appropriate config root with migration logic."""
    configured_root = (os.getenv("GIGAI_ACC_SYNC_ROOT") or "").strip()
    if configured_root:
        return Path(configured_root)

    # Platform-specific defaults
    if sys.platform == "win32" or os.name == "nt":
        # Windows: use %LOCALAPPDATA%/GigAI/acc-sync
        root = Path.home() / "AppData" / "Local" / "GigAI" / "acc-sync"
        # Check for old XDG-style path on Windows and migrate if present
        old_root = Path.home() / ".config" / "GigAI" / "acc-sync"
        if old_root.exists() and not root.exists():
            log.info(f"Migrating ACC sync configuration from {old_root} to {root}")
            try:
                root.parent.mkdir(parents=True, exist_ok=True)
                old_root.replace(root)
            except Exception as ex:
                log.warning(f"Failed to migrate old config directory: {ex}, using new path anyway")
    else:
        # Linux/macOS: use ~/.config/GigAI/acc-sync
        root = Path.home() / ".config" / "GigAI" / "acc-sync"

    return root


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
        root = _resolve_config_root()
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
            page_size=_safe_int(os.getenv("ACC_PAGE_SIZE"), 100),
            issues_input_path=Path(issues_input_path) if issues_input_path else None,
            rfis_input_path=Path(rfis_input_path) if rfis_input_path else None,
        )
