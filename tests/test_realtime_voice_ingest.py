from __future__ import annotations

import base64
from fastapi.testclient import TestClient

from gigai.coordination import CoordinationService
from gigai.coordination.models import RevitElementInput, TeamContact
from gigai.coordination.realtime import (
    RealTimeSTTService,
    RealTimeVoiceIngestService,
    VoiceStreamChunkRequest,
    VoiceStreamFinalizeRequest,
    VoiceStreamStartRequest,
)
from gigai.main import app


client = TestClient(app)


def _build_elements(count: int) -> list[RevitElementInput]:
    return [
        RevitElementInput(
            element_id=f"win_{index:03d}",
            category="window",
            level="3rd Floor",
            material="aluminum",
        )
        for index in range(1, count + 1)
    ]


def test_stream_text_chunks_finalize_to_coordination_plan() -> None:
    ingest = RealTimeVoiceIngestService(CoordinationService())

    session = ingest.start_session(
        VoiceStreamStartRequest(
            project_id="project_alpha",
            drawing_id="A-301",
            available_revit_elements=_build_elements(15),
            team_contacts=[TeamContact(name="Alice", email="alice@example.com")],
        )
    )

    ingest.append_chunk(
        session.session_id,
        VoiceStreamChunkRequest(text_chunk="Change all 3rd floor windows"),
    )
    state = ingest.append_chunk(
        session.session_id,
        VoiceStreamChunkRequest(text_chunk="from aluminum to wood, around 12 units"),
    )

    assert state.chunk_count == 2
    assert "3rd floor" in state.transcript.lower()

    result = ingest.finalize(
        session.session_id,
        VoiceStreamFinalizeRequest(auto_accept=False, execute_actions=False),
    )

    assert result.plan.normalized_change.change_type == "material change"
    assert result.plan.normalized_change.quantity == 12
    assert len(result.plan.matched_targets) == 12
    assert result.plan.status == "pending"


def test_stream_auto_accept_executes_plan() -> None:
    ingest = RealTimeVoiceIngestService(CoordinationService())
    session = ingest.start_session(
        VoiceStreamStartRequest(
            project_id="project_alpha",
            available_revit_elements=_build_elements(12),
        )
    )

    ingest.append_chunk(
        session.session_id,
        VoiceStreamChunkRequest(
            text_chunk="Window material substitution 3rd floor windows aluminum to wood 12 units"
        ),
    )

    result = ingest.finalize(
        session.session_id,
        VoiceStreamFinalizeRequest(auto_accept=True, execute_actions=True, actor="pm_auto"),
    )

    assert result.plan.status == "executed"
    assert result.plan.execution_results


class _StubSTTService(RealTimeSTTService):
    def transcribe(self, audio_bytes: bytes, language: str = "en") -> str:
        if audio_bytes and language == "en":
            return "Change room 204 glazing to laminated glass"
        return ""


def test_stream_audio_chunk_uses_stt_service() -> None:
    ingest = RealTimeVoiceIngestService(CoordinationService(), stt_service=_StubSTTService())
    session = ingest.start_session(
        VoiceStreamStartRequest(
            project_id="project_alpha",
            available_revit_elements=_build_elements(20),
        )
    )

    encoded_audio = base64.b64encode(b"fake_wav_bytes").decode("utf-8")
    state = ingest.append_chunk(
        session.session_id,
        VoiceStreamChunkRequest(audio_base64=encoded_audio),
    )

    assert state.chunk_count == 1
    assert "room 204" in state.transcript.lower()


class _ReferenceAwareStubSTTService(RealTimeSTTService):
    def transcribe(self, audio_bytes: bytes, language: str = "en") -> str:
        if audio_bytes and language == "en":
            return "focus on stdo unit five zero four"
        return ""


def test_stream_audio_chunk_applies_reference_correction() -> None:
    ingest = RealTimeVoiceIngestService(CoordinationService(), stt_service=_ReferenceAwareStubSTTService())
    session = ingest.start_session(
        VoiceStreamStartRequest(
            project_id="project_alpha",
            available_spaces=["504 - Studio Unit", "406 - Two Story Studio Unit"],
        )
    )

    encoded_audio = base64.b64encode(b"fake_wav_bytes").decode("utf-8")
    state = ingest.append_chunk(
        session.session_id,
        VoiceStreamChunkRequest(audio_base64=encoded_audio),
    )

    assert state.chunk_count == 1
    assert "504" in state.transcript
    assert "studio" in state.transcript.lower()


def test_stream_invalid_audio_base64_returns_error() -> None:
    ingest = RealTimeVoiceIngestService(CoordinationService(), stt_service=_StubSTTService())
    session = ingest.start_session(VoiceStreamStartRequest(project_id="project_alpha"))

    try:
        ingest.append_chunk(
            session.session_id,
            VoiceStreamChunkRequest(audio_base64="not_base64!!"),
        )
    except ValueError as ex:
        assert "Invalid audio_base64" in str(ex)
        return

    raise AssertionError("Expected ValueError for invalid audio_base64 payload")


def test_live_view_returns_sectioned_blocks() -> None:
    ingest = RealTimeVoiceIngestService(CoordinationService())
    session = ingest.start_session(VoiceStreamStartRequest(project_id="project_alpha"))

    ingest.append_chunk(
        session.session_id,
        VoiceStreamChunkRequest(text_chunk="We approved the window update for room 204."),
    )
    ingest.append_chunk(
        session.session_id,
        VoiceStreamChunkRequest(text_chunk="Please change glazing to laminated glass by Friday."),
    )
    ingest.append_chunk(
        session.session_id,
        VoiceStreamChunkRequest(text_chunk="Can we clarify if this affects corridor B?"),
    )

    live = ingest.get_live_view(session.session_id)
    assert live is not None
    assert live.merge_ready is True
    assert live.chunk_count == 3
    sections = {block.section: block.items for block in live.blocks}
    assert "transcript" in sections
    assert "decisions" in sections
    assert "actions" in sections
    assert "open_questions" in sections
    assert any("approved" in item.lower() for item in sections["decisions"])
    assert any("change" in item.lower() for item in sections["actions"])
    assert any("clarify" in item.lower() or "?" in item for item in sections["open_questions"])


def test_live_view_endpoint_contract() -> None:
    start_response = client.post(
        "/coordination/voice/stream/start",
        json={"project_id": "project_alpha"},
    )
    assert start_response.status_code == 200
    session_id = start_response.json()["session_id"]

    chunk_response = client.post(
        f"/coordination/voice/stream/{session_id}/chunk",
        json={"text_chunk": "We approved and will change room 204 glazing. Clarify final material?"},
    )
    assert chunk_response.status_code == 200

    live_response = client.get(f"/coordination/voice/stream/{session_id}/live")
    assert live_response.status_code == 200
    payload = live_response.json()
    assert payload["session_id"] == session_id
    assert payload["merge_ready"] is True
    assert isinstance(payload["blocks"], list)
    section_names = {block["section"] for block in payload["blocks"]}
    assert section_names == {"transcript", "decisions", "actions", "open_questions"}
