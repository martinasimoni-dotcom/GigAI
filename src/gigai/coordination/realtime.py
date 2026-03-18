from __future__ import annotations

import base64
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from gigai.coordination.models import CoordinationDecisionUpdate
from gigai.coordination.models import CoordinationPlan, CoordinationRequest, RevitElementInput, TeamContact
from gigai.coordination.service import CoordinationService
from gigai.storage import publish_bus_event


class VoiceStreamStartRequest(BaseModel):
    project_id: str
    project_name: str | None = None
    meeting_id: str | None = None
    drawing_id: str | None = None
    fireflies_transcript_id: str | None = None
    source: Literal["voice", "fireflies", "mixed"] = "voice"
    language: str = "en"
    available_spaces: list[str] = Field(default_factory=list)
    available_revit_elements: list[RevitElementInput] = Field(default_factory=list)
    team_contacts: list[TeamContact] = Field(default_factory=list)


class VoiceStreamChunkRequest(BaseModel):
    text_chunk: str | None = None
    audio_base64: str | None = None
    mime_type: str | None = None


class VoiceStreamFinalizeRequest(BaseModel):
    execute_actions: bool = False
    auto_accept: bool = False
    actor: str = "pm_user_1"
    note: str | None = None


class VoiceStreamSessionResponse(BaseModel):
    session_id: str
    status: Literal["active", "finalized", "closed"]
    chunk_count: int
    transcript: str
    created_at: datetime
    updated_at: datetime


class VoiceStreamFinalizeResponse(BaseModel):
    session_id: str
    transcript: str
    plan: CoordinationPlan


@dataclass
class _VoiceSession:
    session_id: str
    payload: VoiceStreamStartRequest
    chunks: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    status: str = "active"

    def append_chunk(self, text: str) -> None:
        normalized = text.strip()
        if not normalized:
            return
        self.chunks.append(normalized)
        self.updated_at = datetime.now(UTC)

    @property
    def transcript(self) -> str:
        return " ".join(self.chunks).strip()


class RealTimeSTTService:
    def transcribe(self, audio_bytes: bytes, language: str = "en") -> str:
        text = self._transcribe_faster_whisper(audio_bytes, language=language)
        if text:
            return text
        text = self._transcribe_openai_whisper(audio_bytes, language=language)
        if text:
            return text
        return ""

    def _transcribe_faster_whisper(self, audio_bytes: bytes, language: str) -> str:
        try:
            from faster_whisper import WhisperModel
            import tempfile
        except ModuleNotFoundError:
            return ""

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_file.flush()
            model = WhisperModel("base", device="cpu", compute_type="int8")
            segments, _ = model.transcribe(tmp_file.name, language=language)
            parts = [segment.text.strip() for segment in segments if segment.text.strip()]
            return " ".join(parts).strip()

    def _transcribe_openai_whisper(self, audio_bytes: bytes, language: str) -> str:
        try:
            import whisper
            import tempfile
        except ModuleNotFoundError:
            return ""

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_file.flush()
            model = whisper.load_model("base")
            result = model.transcribe(tmp_file.name, language=language)
            return str(result.get("text") or "").strip()


class RealTimeVoiceIngestService:
    def __init__(
        self,
        coordination_service: CoordinationService,
        stt_service: RealTimeSTTService | None = None,
    ):
        self._coordination = coordination_service
        self._stt = stt_service or RealTimeSTTService()
        self._sessions: dict[str, _VoiceSession] = {}
        self._lock = Lock()

    def start_session(self, payload: VoiceStreamStartRequest) -> VoiceStreamSessionResponse:
        session = _VoiceSession(session_id=f"vstr_{uuid4().hex[:12]}", payload=payload)
        with self._lock:
            self._sessions[session.session_id] = session

        publish_bus_event(
            "coordination.voice.stream.started",
            {
                "session_id": session.session_id,
                "project_id": payload.project_id,
                "meeting_id": payload.meeting_id,
                "source": payload.source,
            },
        )
        return self._to_response(session)

    def get_session(self, session_id: str) -> VoiceStreamSessionResponse | None:
        with self._lock:
            session = self._sessions.get(session_id)
        if session is None:
            return None
        return self._to_response(session)

    def append_chunk(self, session_id: str, payload: VoiceStreamChunkRequest) -> VoiceStreamSessionResponse:
        session = self._require_session(session_id)
        if session.status != "active":
            raise ValueError(f"Session '{session_id}' is not active.")

        chunk_text = str(payload.text_chunk or "").strip()
        if not chunk_text and payload.audio_base64:
            audio_bytes = base64.b64decode(payload.audio_base64)
            chunk_text = self._stt.transcribe(audio_bytes, language=session.payload.language)

        if not chunk_text:
            raise ValueError("No transcript chunk detected. Send text_chunk or valid audio_base64 with STT available.")

        session.append_chunk(chunk_text)
        publish_bus_event(
            "coordination.voice.stream.chunk",
            {
                "session_id": session.session_id,
                "project_id": session.payload.project_id,
                "chunk_index": len(session.chunks),
                "chunk_text": chunk_text,
            },
        )
        return self._to_response(session)

    def finalize(self, session_id: str, payload: VoiceStreamFinalizeRequest) -> VoiceStreamFinalizeResponse:
        session = self._require_session(session_id)
        transcript = session.transcript.strip()
        if not transcript:
            raise ValueError("Cannot finalize an empty voice stream session.")

        coordination_request = CoordinationRequest(
            project_id=session.payload.project_id,
            project_name=session.payload.project_name,
            meeting_id=session.payload.meeting_id,
            transcript=transcript,
            drawing_id=session.payload.drawing_id,
            fireflies_transcript_id=session.payload.fireflies_transcript_id,
            source=session.payload.source,
            available_spaces=session.payload.available_spaces,
            available_revit_elements=session.payload.available_revit_elements,
            team_contacts=session.payload.team_contacts,
            execute_actions=payload.execute_actions,
        )
        plan = self._coordination.create_plan(coordination_request)

        if payload.auto_accept:
            plan = self._coordination.decide_plan(
                plan.plan_id,
                CoordinationDecisionUpdate(
                    decision="accept",
                    actor=payload.actor,
                    note=payload.note,
                    execute_actions=payload.execute_actions,
                ),
            )

        session.status = "finalized"
        session.updated_at = datetime.now(UTC)

        publish_bus_event(
            "coordination.voice.stream.finalized",
            {
                "session_id": session.session_id,
                "project_id": session.payload.project_id,
                "plan_id": plan.plan_id,
                "auto_accept": payload.auto_accept,
                "execute_actions": payload.execute_actions,
            },
        )

        return VoiceStreamFinalizeResponse(
            session_id=session.session_id,
            transcript=transcript,
            plan=plan,
        )

    def close(self, session_id: str) -> VoiceStreamSessionResponse:
        session = self._require_session(session_id)
        session.status = "closed"
        session.updated_at = datetime.now(UTC)
        publish_bus_event(
            "coordination.voice.stream.closed",
            {
                "session_id": session.session_id,
                "project_id": session.payload.project_id,
            },
        )
        return self._to_response(session)

    def _require_session(self, session_id: str) -> _VoiceSession:
        with self._lock:
            session = self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Voice stream session '{session_id}' was not found.")
        return session

    def _to_response(self, session: _VoiceSession) -> VoiceStreamSessionResponse:
        return VoiceStreamSessionResponse(
            session_id=session.session_id,
            status=session.status,
            chunk_count=len(session.chunks),
            transcript=session.transcript,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
