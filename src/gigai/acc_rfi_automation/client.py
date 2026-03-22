from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib import request

from .config import AccRfiAutomationConfig


class AccRfiClient:
    def __init__(self, config: AccRfiAutomationConfig, access_token: str) -> None:
        self._config = config
        self._access_token = access_token

    def fetch_rfis(self) -> list[dict[str, Any]]:
        if self._config.rfis_input_path is not None:
            return _read_records_from_file(self._config.rfis_input_path)

        all_records: list[dict[str, Any]] = []
        offset = 0
        while True:
            body = _request_json(
                f"{self._config.rfi_base_url}/projects/{self._config.project_id}/search:rfis",
                self._access_token,
                payload={"limit": self._config.page_size, "offset": offset},
            )
            records = _coerce_records(body)
            if not records:
                break
            all_records.extend(records)
            if len(records) < self._config.page_size:
                break
            offset += self._config.page_size
        return all_records


def _request_json(url: str, access_token: str, payload: dict[str, Any]) -> dict[str, Any] | list[dict[str, Any]]:
    req = request.Request(
        url,
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    with request.urlopen(req, timeout=30) as response:
        body = response.read().decode("utf-8")
    return json.loads(body) if body else {}


def _read_records_from_file(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return _coerce_records(payload)


def _coerce_records(body: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(body, list):
        return [item for item in body if isinstance(item, dict)]

    for key in ("results", "data", "items", "records", "rfis"):
        value = body.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

    return []

