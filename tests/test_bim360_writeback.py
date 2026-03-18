from pathlib import Path

from gigai.orchestrator import process_webhook


def _base_issue_payload() -> dict:
    return {
        "id": "evt_bim360_writeback",
        "eventType": "issue.updated",
        "projectId": "project_alpha",
        "artifactId": "issue_123",
        "status": "open",
        "due_overrun_days": 0,
    }


def test_bim360_disabled_keeps_local_fallback(monkeypatch) -> None:
    monkeypatch.delenv("GIGAI_BIM360_ENABLED", raising=False)

    result = process_webhook(_base_issue_payload())

    assert result.action.outputs["bim360"] == "comment_written"
    assert result.action.outputs.get("bim360_writeback") == "disabled"


def test_bim360_writeback_result_is_reflected_in_outputs(monkeypatch) -> None:
    def _fake_writeback(self, event, decision):  # noqa: ANN001
        return {
            "status": "comment_written",
            "issue_id": "issue_live_9",
            "comment_id": "comment_42",
        }

    monkeypatch.setattr("gigai.action_gateway.Bim360Client.writeback", _fake_writeback)

    result = process_webhook(_base_issue_payload())

    assert result.action.outputs["bim360"] == "comment_written"
    assert result.action.outputs["bim360_issue_id"] == "issue_live_9"
    assert result.action.outputs["bim360_comment_id"] == "comment_42"


def test_bim360_writeback_failure_does_not_break_pipeline(monkeypatch) -> None:
    from gigai.action_gateway import Bim360Error

    def _failing_writeback(self, event, decision):  # noqa: ANN001
        raise Bim360Error("api unavailable")

    monkeypatch.setattr("gigai.action_gateway.Bim360Client.writeback", _failing_writeback)

    result = process_webhook(_base_issue_payload())

    assert result.action.status == "executed"
    assert result.action.outputs["bim360"] == "writeback_failed"
    assert "api unavailable" in result.action.outputs["bim360_error"]


def test_bim360_project_map_container_resolution(monkeypatch, scratch_dir: Path) -> None:
    project_map = scratch_dir / "bim360_project_map.json"
    project_map.write_text(
        '{"project_alpha": {"container_id": "ctr_map_1"}}',
        encoding="utf-8",
    )

    monkeypatch.setenv("GIGAI_BIM360_ENABLED", "true")
    monkeypatch.setenv("GIGAI_BIM360_CLIENT_ID", "cid")
    monkeypatch.setenv("GIGAI_BIM360_CLIENT_SECRET", "secret")
    monkeypatch.delenv("GIGAI_BIM360_CONTAINER_ID", raising=False)
    monkeypatch.setenv("GIGAI_BIM360_PROJECT_MAP_PATH", str(project_map))

    called_paths: list[str] = []

    def _fake_request_json(self, method, path, payload):  # noqa: ANN001
        called_paths.append(path)
        return {"id": "comment_88"}

    monkeypatch.setattr("gigai.bim360_client.Bim360Client._request_json", _fake_request_json)
    monkeypatch.setattr("gigai.bim360_client.Bim360Client._get_access_token", lambda self: "token")

    result = process_webhook(_base_issue_payload())

    assert any("/containers/ctr_map_1/" in path for path in called_paths)
    assert result.action.outputs["bim360_container_id"] == "ctr_map_1"
    assert result.action.outputs["bim360_container_source"] == "project_map"
