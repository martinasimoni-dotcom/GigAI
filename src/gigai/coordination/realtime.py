from __future__ import annotations

import binascii
import base64
from dataclasses import dataclass, field
from datetime import UTC, datetime
import os
from pathlib import Path
import re
import time
from threading import Lock
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from gigai.coordination.models import CoordinationDecisionUpdate
from gigai.coordination.models import CoordinationPlan, CoordinationRequest, RevitElementInput, TeamContact
from gigai.language_reference import correct_transcript_with_reference
from gigai.coordination.service import CoordinationService
from gigai.storage import publish_bus_event, save_stt_metric


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


class LiveTranscriptBlock(BaseModel):
    section: Literal["transcript", "decisions", "actions", "open_questions"]
    items: list[str] = Field(default_factory=list)


class LiveTranscriptViewResponse(BaseModel):
    session_id: str
    status: Literal["active", "finalized", "closed"]
    chunk_count: int
    transcript: str
    blocks: list[LiveTranscriptBlock] = Field(default_factory=list)
    merge_ready: bool = False
    created_at: datetime
    updated_at: datetime


class VoiceStreamFinalizeResponse(BaseModel):
    session_id: str
    transcript: str
    plan: CoordinationPlan


def _split_sentences(text: str) -> list[str]:
    if not text:
        return []
    raw = re.split(r"(?<=[.!?])\s+", text.strip())
    return [sentence.strip() for sentence in raw if sentence.strip()]


def _extract_live_blocks(transcript: str) -> list[LiveTranscriptBlock]:
    sentences = _split_sentences(transcript)
    decisions: list[str] = []
    actions: list[str] = []
    open_questions: list[str] = []

    for sentence in sentences:
        lowered = sentence.lower()
        if any(keyword in lowered for keyword in {"approved", "decided", "we will", "confirmed"}):
            decisions.append(sentence)
        if any(keyword in lowered for keyword in {"change", "update", "replace", "add", "remove", "mark"}):
            actions.append(sentence)
        if "?" in sentence or any(keyword in lowered for keyword in {"unclear", "clarify", "open"}):
            open_questions.append(sentence)

    return [
        LiveTranscriptBlock(section="transcript", items=sentences),
        LiveTranscriptBlock(section="decisions", items=list(dict.fromkeys(decisions))),
        LiveTranscriptBlock(section="actions", items=list(dict.fromkeys(actions))),
        LiveTranscriptBlock(section="open_questions", items=list(dict.fromkeys(open_questions))),
    ]


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
    def __init__(self) -> None:
        provider = str(os.getenv("GIGAI_STT_PROVIDER", "auto") or "auto").strip().lower()
        if provider not in {"auto", "faster-whisper", "openai-whisper"}:
            provider = "auto"
        self._provider = provider
        self._model_name = str(os.getenv("GIGAI_STT_MODEL", "base") or "base").strip()
        self._device = str(os.getenv("GIGAI_STT_DEVICE", "cpu") or "cpu").strip()
        self._compute_type = str(os.getenv("GIGAI_STT_COMPUTE_TYPE", "int8") or "int8").strip()
        self._max_audio_bytes = self._int_env("GIGAI_STT_MAX_AUDIO_BYTES", 10_000_000)
        self._faster_model = None
        self._openai_model = None
        self._cache_dir = self._resolve_cache_dir()

    def transcribe(self, audio_bytes: bytes, language: str = "en") -> str:
        if not audio_bytes:
            return ""
        if len(audio_bytes) > self._max_audio_bytes:
            return ""

        providers = (
            ["faster-whisper", "openai-whisper"]
            if self._provider == "auto"
            else [self._provider]
        )
        for provider in providers:
            text = (
                self._transcribe_faster_whisper(audio_bytes, language=language)
                if provider == "faster-whisper"
                else self._transcribe_openai_whisper(audio_bytes, language=language)
            )
            if text:
                return text
        return ""

    def normalize_transcript(self, transcript: str, reference_spaces: list[str] | None = None) -> str:
        text = " ".join(str(transcript or "").split())
        if not text:
            return ""

        spaces = [
            str(space).strip()
            for space in (reference_spaces or [])
            if isinstance(space, str) and str(space).strip()
        ]
        if not spaces:
            return text

        corrected = correct_transcript_with_reference(text, spaces)
        return corrected or text

    def _transcribe_faster_whisper(self, audio_bytes: bytes, language: str) -> str:
        try:
            from faster_whisper import WhisperModel
            import tempfile
        except ModuleNotFoundError:
            return ""
        except Exception:
            return ""

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_file.flush()
            if self._faster_model is None:
                model_kwargs = {
                    "device": self._device,
                    "compute_type": self._compute_type,
                }
                if self._cache_dir is not None:
                    model_kwargs["download_root"] = str(self._cache_dir)
                self._faster_model = WhisperModel(self._model_name, **model_kwargs)
            model = self._faster_model
            segments, _ = model.transcribe(tmp_file.name, language=language)
            parts = [segment.text.strip() for segment in segments if segment.text.strip()]
            return " ".join(parts).strip()

    def _transcribe_openai_whisper(self, audio_bytes: bytes, language: str) -> str:
        try:
            import whisper
            import tempfile
        except ModuleNotFoundError:
            return ""
        except Exception:
            return ""

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_file.flush()
            if self._openai_model is None:
                model_kwargs = {}
                if self._device:
                    model_kwargs["device"] = self._device
                if self._cache_dir is not None:
                    model_kwargs["download_root"] = str(self._cache_dir)
                self._openai_model = whisper.load_model(self._model_name, **model_kwargs)
            model = self._openai_model
            result = model.transcribe(tmp_file.name, language=language)
            return str(result.get("text") or "").strip()

    @staticmethod
    def _resolve_cache_dir() -> Path | None:
        configured = str(os.getenv("GIGAI_STT_CACHE_DIR") or "").strip()
        candidate = Path(configured) if configured else Path(__file__).resolve().parents[3] / "wisper"
        try:
            if candidate.exists() and candidate.is_dir():
                return candidate
            if configured:
                candidate.mkdir(parents=True, exist_ok=True)
                return candidate
        except OSError:
            return None
        return None

    @staticmethod
    def _int_env(name: str, default_value: int) -> int:
        raw = os.getenv(name)
        if raw is None:
            return default_value
        try:
            value = int(raw)
        except ValueError:
            return default_value
        return value if value > 0 else default_value


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

    def get_live_view(self, session_id: str) -> LiveTranscriptViewResponse | None:
        with self._lock:
            session = self._sessions.get(session_id)
        if session is None:
            return None
        transcript = session.transcript
        return LiveTranscriptViewResponse(
            session_id=session.session_id,
            status=session.status,
            chunk_count=len(session.chunks),
            transcript=transcript,
            blocks=_extract_live_blocks(transcript),
            merge_ready=bool(transcript.strip()),
            created_at=session.created_at,
            updated_at=session.updated_at,
        )

    def append_chunk(self, session_id: str, payload: VoiceStreamChunkRequest) -> VoiceStreamSessionResponse:
        session = self._require_session(session_id)
        if session.status != "active":
            raise ValueError(f"Session '{session_id}' is not active.")

        chunk_text = str(payload.text_chunk or "").strip()
        if not chunk_text and payload.audio_base64:
            started_at = time.perf_counter()
            metric_error: str | None = None
            try:
                audio_bytes = base64.b64decode(payload.audio_base64, validate=True)
            except (binascii.Error, ValueError) as ex:
                raise ValueError("Invalid audio_base64 payload.") from ex
            try:
                chunk_text = self._stt.transcribe(audio_bytes, language=session.payload.language)
            except Exception as ex:
                metric_error = str(ex)
                chunk_text = ""
            if chunk_text:
                chunk_text = self._stt.normalize_transcript(
                    chunk_text,
                    reference_spaces=session.payload.available_spaces,
                )
            latency_ms = (time.perf_counter() - started_at) * 1000.0
            save_stt_metric(
                transcript_id=session.session_id,
                provider=self._stt._provider,
                model=self._stt._model_name,
                latency_ms=latency_ms,
                transcript_length=len(chunk_text),
                error=metric_error,
                metadata={
                    "language": session.payload.language,
                    "source": session.payload.source,
                    "audio_size_bytes": len(audio_bytes),
                },
            )
        chunk_text = " ".join(chunk_text.split())

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
