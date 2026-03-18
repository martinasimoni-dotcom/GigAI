from __future__ import annotations

from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, status
from fastapi.responses import RedirectResponse
import uvicorn

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

def _load_env_fallback(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"").strip("'")
        if key and key not in __import__("os").environ:
            __import__("os").environ[key] = value

if load_dotenv is not None:
    _ROOT = Path(__file__).resolve().parents[2]
    load_dotenv(_ROOT / ".env", override=False)
else:
    _ROOT = Path(__file__).resolve().parents[2]
    _load_env_fallback(_ROOT / ".env")

from gigai.google_integrations import GoogleIntegrationConfig, GoogleWorkspaceClient
from gigai.fireflies_stt import FirefliesIntegrationError, resolve_fireflies_transcript
from gigai.mom_email_generator import generate_meeting_completed_mom
from gigai.coordination import (
    CoordinationDecisionUpdate,
    CoordinationPlanResponse,
    CoordinationRequest,
    CoordinationService,
    RealTimeVoiceIngestService,
    VoiceStreamChunkRequest,
    VoiceStreamFinalizeRequest,
    VoiceStreamFinalizeResponse,
    VoiceStreamSessionResponse,
    VoiceStreamStartRequest,
)
from gigai.models import ActionResult, ApprovalState, DecisionPackage, PipelineResponse, WebhookAccepted
from gigai.orchestrator import (
    get_cached_pipeline,
    ingest_payload,
    process_event,
    process_webhook,
    replay_event,
    resolve_approval_action,
)
from gigai.storage import list_bus_events
from gigai.storage import publish_bus_event
from gigai.voice import build_voice_focus_payload

app = FastAPI(title="GigAI MVP", version="0.2.0")
coordination_service = CoordinationService()
voice_ingest_service = RealTimeVoiceIngestService(coordination_service)


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/webhooks/bim360",
    response_model=WebhookAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
def bim360_webhook(payload: dict, background_tasks: BackgroundTasks) -> WebhookAccepted:
    event, idempotent = ingest_payload(payload)
    if not idempotent:
        background_tasks.add_task(process_event, event.event_id)
    return WebhookAccepted(event_id=event.event_id, status="accepted", idempotent=idempotent)


@app.post("/internal/events/replay/{event_id}", response_model=PipelineResponse)
def replay(event_id: str) -> PipelineResponse:
    try:
        return replay_event(event_id)
    except ValueError as ex:
        raise HTTPException(status_code=404, detail=str(ex)) from ex


@app.post("/internal/decisions/evaluate", response_model=DecisionPackage)
def evaluate_decision(payload: dict) -> DecisionPackage:
    return process_webhook(payload).decision


@app.post("/internal/actions/execute", response_model=ActionResult)
def execute_action(payload: dict) -> ActionResult:
    event_id = str(payload.get("event_id") or "").strip()
    if not event_id:
        raise HTTPException(status_code=400, detail="event_id is required.")

    cached = get_cached_pipeline(event_id)
    if cached is None:
        try:
            cached = process_event(event_id)
        except ValueError as ex:
            raise HTTPException(status_code=404, detail=str(ex)) from ex
    return cached.action


@app.post("/approvals/{approval_id}/approve", response_model=ApprovalState)
def approve(approval_id: str, payload: dict) -> ApprovalState:
    try:
        return resolve_approval_action(
            approval_id,
            decision="approve",
            actor=str(payload.get("actor") or "pm_user_1"),
            note=str(payload.get("note") or "").strip() or None,
        )
    except ValueError as ex:
        raise HTTPException(status_code=404, detail=str(ex)) from ex


@app.post("/approvals/{approval_id}/reject", response_model=ApprovalState)
def reject(approval_id: str, payload: dict) -> ApprovalState:
    try:
        return resolve_approval_action(
            approval_id,
            decision="reject",
            actor=str(payload.get("actor") or "pm_user_1"),
            note=str(payload.get("note") or "").strip() or None,
        )
    except ValueError as ex:
        raise HTTPException(status_code=404, detail=str(ex)) from ex


@app.get("/internal/bus/events")
def bus_events() -> list[dict]:
    return list_bus_events()


@app.post("/meetings/focus", response_model=PipelineResponse)
def meeting_focus(payload: dict) -> PipelineResponse:
    normalized_payload = dict(payload)
    normalized_payload.setdefault("type", "meeting.focus")
    return process_webhook(normalized_payload)


@app.post("/meeting/focus", response_model=PipelineResponse)
def meeting_focus_alias(payload: dict) -> PipelineResponse:
    return meeting_focus(payload)


@app.post("/meetings/revit-location-marked/mom")
def revit_location_marked_mom(payload: dict) -> dict:
    return generate_meeting_completed_mom(payload)


@app.post("/voice/command", response_model=PipelineResponse)
def voice_command(payload: dict) -> PipelineResponse:
    normalized_input = dict(payload)
    transcript = str(normalized_input.get("transcript") or normalized_input.get("voice_text") or "").strip()
    if not transcript:
        try:
            fireflies_transcript, fireflies_metadata = resolve_fireflies_transcript(normalized_input)
        except FirefliesIntegrationError as ex:
            raise HTTPException(status_code=400, detail=str(ex)) from ex

        if fireflies_transcript:
            transcript = fireflies_transcript
            normalized_input["transcript"] = transcript
            normalized_input.update(fireflies_metadata)

    if not transcript:
        raise HTTPException(
            status_code=400,
            detail=(
                "transcript is required. "
                "Or send fireflies_latest=true / fireflies_transcript_id with Fireflies enabled."
            ),
        )

    normalized_payload = build_voice_focus_payload(normalized_input)
    return process_webhook(normalized_payload)


@app.post("/system/e2e/simulate")
def simulate_end_to_end(payload: dict) -> dict:
    transcript = str(payload.get("transcript") or payload.get("voice_text") or "").strip()
    if not transcript:
        raise HTTPException(status_code=400, detail="transcript is required.")

    project_id = str(payload.get("project_id") or payload.get("projectId") or "project_alpha").strip() or "project_alpha"
    meeting_id = str(payload.get("meeting_id") or "meet_simulated").strip() or "meet_simulated"
    assigned_architect = str(payload.get("assign_to") or "architect_1").strip() or "architect_1"

    voice_payload = {
        "projectId": project_id,
        "transcript": transcript,
        "available_spaces": payload.get("available_spaces") or [],
        "drawing_context": payload.get("drawing_context") if isinstance(payload.get("drawing_context"), dict) else {},
        "notification_emails": payload.get("notification_emails") if isinstance(payload.get("notification_emails"), list) else [],
        "participants": payload.get("participants") if isinstance(payload.get("participants"), list) else [],
    }

    normalized_payload = build_voice_focus_payload(voice_payload)
    pipeline = process_webhook(normalized_payload)

    revision_payload = {
        "revision_id": f"rev_{pipeline.event.event_id[-8:]}",
        "meeting_id": meeting_id,
        "project_id": project_id,
        "space_name": pipeline.event.focus_space or str(payload.get("space_name") or "Unknown Space"),
        "element_type": str(payload.get("element_type") or "architectural_element"),
        "action": "REVISION_MARKED",
        "comment_text": pipeline.decision.proposal,
        "applied_by": str(payload.get("applied_by") or "GigAI"),
        "notification_emails": voice_payload["notification_emails"],
    }
    revision_result = revit_revision_marked(revision_payload)

    mom_payload = {
        "event_type": "Revit Location Marked",
        "project": {
            "name": project_id,
            "assigned_team": assigned_architect,
            "related_revisions": [revision_payload["revision_id"]],
        },
        "meeting": {
            "date_time": pipeline.event.occurred_at.isoformat(),
            "participants": voice_payload["participants"],
            "transcript": transcript,
        },
        "bim": {
            "marked_location": revision_payload["space_name"],
            "element_categories": [revision_payload["element_type"]],
            "model_version": "GigAI-Sim",
        },
        "detected_changes": {
            "key_discussions": [pipeline.decision.proposal],
            "decisions": [pipeline.action.reason],
            "action_items": [
                {
                    "task": pipeline.decision.proposal,
                    "responsible": assigned_architect,
                    "deadline": str(payload.get("deadline") or "Not specified"),
                }
            ],
        },
    }
    mom = generate_meeting_completed_mom(mom_payload)

    action_outputs = dict(pipeline.action.outputs)
    bus_tail = list_bus_events(limit=25)
    checklist = {
        "speech_recognized": bool(transcript),
        "llm_understood": bool(pipeline.event.focus_space or pipeline.event.focus_reason),
        "intent_structured": bool(pipeline.decision.proposal),
        "event_engine_executed": pipeline.action.status in {"executed", "approval_required"},
        "revit_revision_logged": revision_result.get("status") == "recorded",
        "dashboard_updated": revision_result.get("dashboard") == "updated",
        "email_attempted": revision_result.get("email", {}).get("status") in {"sent", "skipped", "disabled"},
        "calendar_attempted": action_outputs.get("google_calendar") in {"event_created", "skipped", "disabled"},
        "audit_logged": any(event.get("topic") == "revit.revision_marked" for event in bus_tail),
    }

    return {
        "status": "ok",
        "architecture": "GigAI Event-Driven Construction Coordination AI",
        "assigned_architect": assigned_architect,
        "pipeline": pipeline.model_dump(mode="json"),
        "revision": revision_result,
        "mom": {
            "subject": mom.get("subject", ""),
            "email_body": mom.get("email_body", ""),
            "to": mom.get("to", []),
        },
        "checklist": checklist,
        "event_log_tail": bus_tail,
    }


@app.post("/revit/revision-marked")
def revit_revision_marked(payload: dict) -> dict:
    revision_id = str(payload.get("revision_id") or "").strip() or "rev_unknown"
    meeting_id = str(payload.get("meeting_id") or "").strip() or "meeting_unknown"
    project_id = str(payload.get("project_id") or payload.get("projectId") or "").strip() or "project_alpha"
    space_name = str(payload.get("space_name") or payload.get("space") or "").strip() or "Unknown Space"
    element_type = str(payload.get("element_type") or payload.get("element") or "").strip() or "element"
    action = str(payload.get("action") or "REVISION_MARKED").strip()
    comment_text = str(payload.get("comment_text") or payload.get("comment") or "").strip()
    applied_by = str(payload.get("applied_by") or "Revit User").strip()

    event_payload = {
        "revision_id": revision_id,
        "meeting_id": meeting_id,
        "project_id": project_id,
        "space_name": space_name,
        "element_type": element_type,
        "action": action,
        "comment_text": comment_text,
        "applied_by": applied_by,
    }
    publish_bus_event("revit.revision_marked", event_payload)

    recipients = payload.get("notification_emails")
    if not isinstance(recipients, list):
        recipients = []
    recipients = [str(item).strip() for item in recipients if str(item).strip()]

    email_subject = f"GigAI Revit Revision Completed — {space_name}"
    email_body = (
        "Revit revision bubble was marked successfully.\n\n"
        f"Project: {project_id}\n"
        f"Meeting: {meeting_id}\n"
        f"Revision ID: {revision_id}\n"
        f"Space: {space_name}\n"
        f"Element: {element_type}\n"
        f"Action: {action}\n"
        f"Applied By: {applied_by}\n"
        f"Comment: {comment_text or '(none)'}\n"
    )

    google_config = GoogleIntegrationConfig.from_env()
    google_client = GoogleWorkspaceClient(google_config)
    resolved_recipients = recipients or list(google_config.default_recipients)
    email_result = google_client.send_email(
        to_emails=resolved_recipients,
        subject=email_subject,
        body=email_body,
    )

    return {
        "status": "recorded",
        "dashboard": "updated",
        "event_topic": "revit.revision_marked",
        "revision_id": revision_id,
        "email": {
            "status": email_result.status,
            "payload": email_result.payload,
        },
    }


@app.post("/coordination/voice", response_model=CoordinationPlanResponse)
def create_coordination_plan(request: CoordinationRequest) -> CoordinationPlanResponse:
    plan = coordination_service.create_plan(request)
    return CoordinationPlanResponse(plan=plan)


@app.get("/coordination/voice/{plan_id}", response_model=CoordinationPlanResponse)
def get_coordination_plan(plan_id: str) -> CoordinationPlanResponse:
    plan = coordination_service.get_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"Coordination plan '{plan_id}' was not found.")
    return CoordinationPlanResponse(plan=plan)


@app.post("/coordination/voice/{plan_id}/decision", response_model=CoordinationPlanResponse)
def decide_coordination_plan(plan_id: str, update: CoordinationDecisionUpdate) -> CoordinationPlanResponse:
    try:
        plan = coordination_service.decide_plan(plan_id, update)
    except ValueError as ex:
        raise HTTPException(status_code=404, detail=str(ex)) from ex
    return CoordinationPlanResponse(plan=plan)


@app.post("/coordination/voice/stream/start", response_model=VoiceStreamSessionResponse)
def start_voice_stream(payload: VoiceStreamStartRequest) -> VoiceStreamSessionResponse:
    return voice_ingest_service.start_session(payload)


@app.get("/coordination/voice/stream/{session_id}", response_model=VoiceStreamSessionResponse)
def get_voice_stream(session_id: str) -> VoiceStreamSessionResponse:
    session = voice_ingest_service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Voice stream session '{session_id}' was not found.")
    return session


@app.post("/coordination/voice/stream/{session_id}/chunk", response_model=VoiceStreamSessionResponse)
def append_voice_stream_chunk(session_id: str, payload: VoiceStreamChunkRequest) -> VoiceStreamSessionResponse:
    try:
        return voice_ingest_service.append_chunk(session_id, payload)
    except ValueError as ex:
        message = str(ex)
        status_code = 404 if "was not found" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from ex


@app.post("/coordination/voice/stream/{session_id}/finalize", response_model=VoiceStreamFinalizeResponse)
def finalize_voice_stream(session_id: str, payload: VoiceStreamFinalizeRequest) -> VoiceStreamFinalizeResponse:
    try:
        return voice_ingest_service.finalize(session_id, payload)
    except ValueError as ex:
        message = str(ex)
        status_code = 404 if "was not found" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from ex


@app.post("/coordination/voice/stream/{session_id}/close", response_model=VoiceStreamSessionResponse)
def close_voice_stream(session_id: str) -> VoiceStreamSessionResponse:
    try:
        return voice_ingest_service.close(session_id)
    except ValueError as ex:
        raise HTTPException(status_code=404, detail=str(ex)) from ex


def run() -> None:
    uvicorn.run("gigai.main:app", host="127.0.0.1", port=8000, reload=False)
