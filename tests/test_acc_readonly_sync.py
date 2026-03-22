from __future__ import annotations

import json
from pathlib import Path
import shutil
import uuid

from gigai.acc_readonly_sync.cli import main
from gigai.acc_readonly_sync.normalize import normalize_issue_records, normalize_rfi_records


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "acc_readonly_sync"


def _load_json(name: str) -> dict:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def test_normalize_issue_records_ignores_items_without_location() -> None:
    payload = _load_json("issues_response.json")

    items, ignored = normalize_issue_records(payload["results"])

    assert ignored == 1
    assert len(items) == 2
    assert items[0].id == "ISSUE-100"
    assert items[0].createdBy == "Coordinator One"
    assert items[0].location.elementId == "45001"
    assert items[1].location.viewId == "Sheet A201"


def test_normalize_rfi_records_extracts_location_and_assignee() -> None:
    payload = _load_json("rfis_response.json")

    items, ignored = normalize_rfi_records(payload["results"])

    assert ignored == 0
    assert len(items) == 1
    assert items[0].id == "RFI-200"
    assert items[0].createdBy == "Site Manager"
    assert items[0].assignedUser == "Project Engineer"
    assert items[0].location.elementId == "33002"
    assert items[0].location.viewId == "Section AA"


def test_cli_writes_snapshot_from_offline_files(monkeypatch) -> None:
    workspace_temp = Path(".pytest_runtime") / f"acc_sync_{uuid.uuid4().hex}"
    workspace_temp.mkdir(parents=True, exist_ok=True)
    output_path = workspace_temp / "latest-acc-items.json"
    root_path = workspace_temp / "acc-sync-root"
    monkeypatch.setenv("GIGAI_ACC_SYNC_ROOT", str(root_path))

    try:
        exit_code = main(
            [
                "--project-id",
                "project_alpha",
                "--include-rfis",
                "--issues-input",
                str(FIXTURE_ROOT / "issues_response.json"),
                "--rfis-input",
                str(FIXTURE_ROOT / "rfis_response.json"),
                "--output",
                str(output_path),
            ]
        )

        assert exit_code == 0
        written = json.loads(output_path.read_text(encoding="utf-8"))
        assert written["metadata"]["projectId"] == "project_alpha"
        assert written["metadata"]["itemsWritten"] == 3
        assert written["metadata"]["ignoredWithoutLocation"] == 1
        assert written["metadata"]["newItems"] == 3
        assert written["metadata"]["updatedItems"] == 0
        assert [item["id"] for item in written["items"]] == ["ISSUE-100", "ISSUE-101", "RFI-200"]
        assert written["items"][0]["createdBy"] == "Coordinator One"

        log_path = root_path / "acc-readonly-sync.log"
        log_content = log_path.read_text(encoding="utf-8")
        assert "items_written=3" in log_content
        assert "issue:ISSUE-100 -> detected -> new" in log_content
    finally:
        shutil.rmtree(workspace_temp, ignore_errors=True)
