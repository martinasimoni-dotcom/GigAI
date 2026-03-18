from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from urllib import request
from urllib.error import HTTPError, URLError

from gigai.action_gateway import _apply_google_calendar_sync, _apply_google_email_notify
from gigai.bim360_client import Bim360Client, Bim360Config
from gigai.coordination.models import CoordinationPlan
from gigai.models import DecisionPackage, NormalizedEvent


def _is_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _execute_revit(plan: CoordinationPlan) -> tuple[str, str]:
    base_url = (os.getenv("GIGAI_REVIT_API_URL") or "http://127.0.0.1:8011").strip().rstrip("/")
    endpoint = f"{base_url}/api/revisions/create"

    payload = {
        "shape_type": "CLOUD",
        "comment_text": plan.acc_action.markup_title,
        "comment_details": {
            "plan_id": plan.plan_id,
            "project_id": plan.project_id,
            "change_type": plan.normalized_change.change_type,
        },
        "requested_by": "GigAI",
        "revision_date": datetime.now(UTC).isoformat(),
    }

    for element_id in plan.revit_action.revision_bubble_element_ids:
        payload["element_id"] = element_id
        try:
            data = json.dumps(payload).encode("utf-8")
            req = request.Request(endpoint, method="POST", data=data)
            req.add_header("Content-Type", "application/json")
            with request.urlopen(req, timeout=8) as response:
                status_code = response.getcode()
            if status_code < 200 or status_code >= 300:
                return "failed", f"revit_http_status_{status_code}"
        except (HTTPError, URLError, TimeoutError) as error:
            return "failed", f"revit_api_error:{error}"

    return "executed", "revision_bubbles_created"


def _execute_acc(plan: CoordinationPlan) -> tuple[str, str]:
    event = NormalizedEvent(
        event_id=plan.plan_id,
        source="bim360",
        type="coordination.material_change",
        project_id=plan.project_id,
        artifact_id=plan.acc_action.drawing_id,
        focus_space=plan.normalized_change.location,
        occurred_at=datetime.now(UTC),
        payload={
            "container_id": plan.acc_action.drawing_id,
            "markup_title": plan.acc_action.markup_title,
            "markup_body": plan.acc_action.markup_body,
        },
    )
    decision = DecisionPackage(
        decision_id=plan.plan_id,
        event_id=plan.plan_id,
        proposal="create_issue_note",
        confidence=max(plan.normalized_change.confidence, 0.8),
        risk_level="low",
        constraints=[],
        evidence=[],
    )

    client = Bim360Client(Bim360Config.from_env())
    result = client.writeback(event, decision)
    status = str(result.get("status") or "unknown")
    if status in {"issue_created", "comment_written", "disabled", "not_configured", "skipped_missing_issue_id"}:
        return "executed", status
    return "failed", status


def _execute_google(plan: CoordinationPlan) -> dict[str, str]:
    event = NormalizedEvent(
        event_id=plan.plan_id,
        source="bim360",
        type="coordination.material_change",
        project_id=plan.project_id,
        artifact_id=plan.acc_action.drawing_id,
        focus_space=plan.normalized_change.location,
        occurred_at=datetime.now(UTC),
        payload={"notification_emails": plan.email_action.recipients},
    )
    decision = DecisionPackage(
        decision_id=plan.plan_id,
        event_id=plan.plan_id,
        proposal="coordination_execution",
        confidence=max(plan.normalized_change.confidence, 0.8),
        risk_level="low",
        constraints=[],
        evidence=[],
    )

    outputs: dict[str, str] = {}
    outputs = _apply_google_email_notify(event, decision, outputs)
    outputs = _apply_google_calendar_sync(event, decision, outputs)
    return outputs


def execute_plan(plan: CoordinationPlan) -> dict[str, str]:
    if _is_truthy(os.getenv("GIGAI_COORDINATION_DRY_RUN", "true")):
        return {
            "revit": "simulated",
            "acc": "simulated",
            "gmail": "simulated",
            "calendar": "simulated",
        }

    results: dict[str, str] = {}
    revit_status, revit_detail = _execute_revit(plan)
    acc_status, acc_detail = _execute_acc(plan)
    google_outputs = _execute_google(plan)

    results["revit"] = revit_status
    results["revit_detail"] = revit_detail
    results["acc"] = acc_status
    results["acc_detail"] = acc_detail
    results["gmail"] = str(google_outputs.get("google_email") or "unknown")
    results["calendar"] = str(google_outputs.get("google_calendar") or "unknown")

    return results
