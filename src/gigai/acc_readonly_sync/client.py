from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import parse, request

from .config import AccReadonlySyncConfig


@dataclass(slots=True)
class RawAccPayload:
    source: str
    records: list[dict[str, Any]]


class AccReadonlyClient:
    def __init__(self, config: AccReadonlySyncConfig, access_token: str) -> None:
        self._config = config
        self._access_token = access_token

    def fetch_issues(self) -> RawAccPayload:
        if self._config.issues_input_path is not None:
            return RawAccPayload("issues:file", _read_records_from_file(self._config.issues_input_path))

        all_records: list[dict[str, Any]] = []
        offset = 0
        while True:
            query = parse.urlencode({"limit": self._config.page_size, "offset": offset})
            url = f"{self._config.issues_base_url}/projects/{self._config.project_id}/issues?{query}"
            body = _request_json(url, self._access_token)
            records = _coerce_records(body)
            if not records:
                break
            all_records.extend(records)
            if len(records) < self._config.page_size:
                break
            offset += self._config.page_size
        return RawAccPayload("issues:api", all_records)

    def fetch_rfis(self) -> RawAccPayload:
        if self._config.rfis_input_path is not None:
            return RawAccPayload("rfis:file", _read_records_from_file(self._config.rfis_input_path))

        all_records: list[dict[str, Any]] = []
        offset = 0
        while True:
            url = f"{self._config.rfis_base_url}/projects/{self._config.project_id}/search:rfis"
            body = _request_json(
                url,
                self._access_token,
                method="POST",
                payload={"limit": self._config.page_size, "offset": offset},
            )
            records = _coerce_records(body)
            if not records:
                break
            all_records.extend(records)
            if len(records) < self._config.page_size:
                break
            offset += self._config.page_size
        return RawAccPayload("rfis:api", all_records)


def _request_json(
    url: str,
    access_token: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any] | list[dict[str, Any]]:
    data = None
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(url, method=method, data=data, headers=headers)
    with request.urlopen(req, timeout=30) as response:
        body = response.read().decode("utf-8")
    return json.loads(body) if body else {}


def _read_records_from_file(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return _coerce_records(payload)


def _coerce_records(body: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(body, list):
        return [item for item in body if isinstance(item, dict)]

    for key in ("results", "data", "items", "records", "rfis", "issues"):
        value = body.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]

    return []

