import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import parse, request
from urllib.error import HTTPError, URLError

from gigai.models import DecisionPackage, NormalizedEvent


def _is_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Bim360Config:
    enabled: bool
    client_id: str
    client_secret: str
    default_container_id: str
    project_map_path: str
    base_url: str
    scope: str
    token_url: str

    @classmethod
    def from_env(cls) -> "Bim360Config":
        return cls(
            enabled=_is_truthy(os.getenv("GIGAI_BIM360_ENABLED")),
            client_id=os.getenv("GIGAI_BIM360_CLIENT_ID", "").strip(),
            client_secret=os.getenv("GIGAI_BIM360_CLIENT_SECRET", "").strip(),
            default_container_id=os.getenv("GIGAI_BIM360_CONTAINER_ID", "").strip(),
            project_map_path=os.getenv(
                "GIGAI_BIM360_PROJECT_MAP_PATH",
                "config/bim360_project_map.json",
            ).strip(),
            base_url=os.getenv("GIGAI_BIM360_BASE_URL", "https://developer.api.autodesk.com/issues/v2").strip(),
            scope=os.getenv("GIGAI_BIM360_SCOPE", "data:read data:write account:read").strip(),
            token_url=os.getenv(
                "GIGAI_BIM360_TOKEN_URL",
                "https://developer.api.autodesk.com/authentication/v2/token",
            ).strip(),
        )

    @property
    def ready(self) -> bool:
        return (
            self.enabled
            and bool(self.client_id)
            and bool(self.client_secret)
        )


class Bim360Error(RuntimeError):
    pass


class Bim360Client:
    def __init__(self, config: Bim360Config):
        self._config = config
        self._token: str | None = None
        self._token_expiry_epoch: float = 0.0

    def writeback(self, event: NormalizedEvent, decision: DecisionPackage) -> dict[str, Any]:
        if not self._config.enabled:
            return {"status": "disabled"}
        if not self._config.ready:
            return {"status": "not_configured"}

        container_id, source = self._resolve_container_id(event)
        if not container_id:
            return {"status": "not_configured", "reason": "missing_container_id"}

        if decision.proposal == "create_issue_note":
            result = self._create_issue(container_id, event, decision)
            result["container_source"] = source
            return result

        issue_id = event.artifact_id or str(event.payload.get("issue_id") or "").strip()
        if issue_id:
            result = self._add_comment(container_id, issue_id, event, decision)
            result["container_source"] = source
            return result

        return {"status": "skipped_missing_issue_id"}

    def _create_issue(
        self,
        container_id: str,
        event: NormalizedEvent,
        decision: DecisionPackage,
    ) -> dict[str, Any]:
        payload = {
            "title": f"GigAI: {decision.proposal}",
            "description": _build_issue_description(event, decision),
            "status": "open",
            "metadata": {
                "gigai_event_id": event.event_id,
                "gigai_decision_id": decision.decision_id,
                "gigai_focus_space": event.focus_space or "",
            },
        }
        body = self._request_json("POST", f"/containers/{container_id}/issues", payload)
        issue_id = str(body.get("id") or "")
        result: dict[str, Any] = {"status": "issue_created", "container_id": container_id}
        if issue_id:
            result["issue_id"] = issue_id
        return result

    def _add_comment(
        self,
        container_id: str,
        issue_id: str,
        event: NormalizedEvent,
        decision: DecisionPackage,
    ) -> dict[str, Any]:
        payload = {
            "body": _build_comment_body(event, decision),
            "metadata": {
                "gigai_event_id": event.event_id,
                "gigai_decision_id": decision.decision_id,
            },
        }
        body = self._request_json(
            "POST",
            f"/containers/{container_id}/issues/{issue_id}/comments",
            payload,
        )
        comment_id = str(body.get("id") or "")
        result: dict[str, Any] = {
            "status": "comment_written",
            "container_id": container_id,
            "issue_id": issue_id,
        }
        if comment_id:
            result["comment_id"] = comment_id
        return result

    def _request_json(self, method: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        token = self._get_access_token()
        url = _join_url(self._config.base_url, path)
        req = request.Request(url=url, method=method)
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Content-Type", "application/json")
        data = json.dumps(payload).encode("utf-8")
        return _open_json(req, data=data)

    def _get_access_token(self) -> str:
        if self._token and time.time() < self._token_expiry_epoch:
            return self._token

        form = parse.urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": self._config.client_id,
                "client_secret": self._config.client_secret,
                "scope": self._config.scope,
            }
        ).encode("utf-8")
        req = request.Request(url=self._config.token_url, method="POST", data=form)
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        response = _open_json(req)

        token = str(response.get("access_token") or "").strip()
        expires_in = int(response.get("expires_in") or 0)
        if not token:
            raise Bim360Error("APS token response did not include access_token.")

        self._token = token
        # Refresh slightly before expiry.
        self._token_expiry_epoch = time.time() + max(0, expires_in - 30)
        return token

    def _resolve_container_id(self, event: NormalizedEvent) -> tuple[str | None, str]:
        payload_container = (
            str(event.payload.get("container_id") or "").strip()
            or str(event.payload.get("containerId") or "").strip()
            or str(event.payload.get("bim360_container_id") or "").strip()
        )
        if payload_container:
            return payload_container, "payload"

        mapped = _read_container_from_project_map(self._config.project_map_path, event.project_id)
        if mapped:
            return mapped, "project_map"

        if self._config.default_container_id:
            return self._config.default_container_id, "default"

        return None, "missing"


def _open_json(req: request.Request, data: bytes | None = None) -> dict[str, Any]:
    try:
        with request.urlopen(req, data=data, timeout=20) as resp:
            body = resp.read().decode("utf-8")
            if not body:
                return {}
            return json.loads(body)
    except HTTPError as ex:
        detail = ex.read().decode("utf-8", errors="replace")
        raise Bim360Error(f"BIM 360 API HTTP error {ex.code}: {detail}") from ex
    except URLError as ex:
        raise Bim360Error(f"BIM 360 API connection failed: {ex.reason}") from ex
    except json.JSONDecodeError as ex:
        raise Bim360Error("BIM 360 API returned invalid JSON.") from ex


def _build_issue_description(event: NormalizedEvent, decision: DecisionPackage) -> str:
    lines = [
        "Generated by GigAI",
        f"Event: {event.event_id}",
        f"Decision: {decision.decision_id}",
        f"Proposal: {decision.proposal}",
    ]
    if event.focus_space:
        lines.append(f"Focus space: {event.focus_space}")
    if decision.evidence:
        refs = ", ".join(item["ref"] for item in decision.evidence if item.get("ref"))
        if refs:
            lines.append(f"Evidence: {refs}")
    return "\n".join(lines)


def _build_comment_body(event: NormalizedEvent, decision: DecisionPackage) -> str:
    lines = [f"GigAI proposal: {decision.proposal} (confidence {decision.confidence:.2f})"]
    if event.focus_space:
        lines.append(f"Focus space: {event.focus_space}")
    if decision.alternatives:
        lines.append(f"Alternatives: {', '.join(decision.alternatives)}")
    return "\n".join(lines)


def _join_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _read_container_from_project_map(project_map_path: str, project_id: str) -> str | None:
    path = Path(project_map_path)
    if not path.is_file():
        return None

    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    entry: Any = None
    if isinstance(content, dict):
        projects = content.get("projects")
        if isinstance(projects, dict) and project_id in projects:
            entry = projects.get(project_id)
        elif project_id in content:
            entry = content.get(project_id)

    if isinstance(entry, str) and entry.strip():
        return entry.strip()
    if isinstance(entry, dict):
        value = str(entry.get("container_id") or entry.get("containerId") or "").strip()
        if value:
            return value
    return None
