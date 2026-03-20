from __future__ import annotations

import base64

from fastapi.testclient import TestClient

from gigai.main import app, voice_ingest_service


client = TestClient(app)


class _AudioEndpointStubSTT:
    _provider = "stub"
    _model_name = "stub-whisper"

    def transcribe(self, audio_bytes: bytes, language: str = "en") -> str:
        if audio_bytes and language == "en":
            return "focus on stdo unit five zero four"
        return ""

    def normalize_transcript(self, transcript: str, reference_spaces: list[str] | None = None) -> str:
        return "focus on 504 studio unit"


def test_voice_command_audio_transcribes_and_marks_revit(monkeypatch) -> None:
    monkeypatch.setenv("GIGAI_GOOGLE_INTEGRATION_ENABLED", "false")
    monkeypatch.setattr(voice_ingest_service, "_stt", _AudioEndpointStubSTT())

    response = client.post(
        "/voice/command/audio",
        json={
            "projectId": "project_alpha",
            "meeting_id": "meet_audio_001",
            "audio_base64": base64.b64encode(b"fake_wav_bytes").decode("utf-8"),
            "language": "en",
            "available_spaces": ["504 - Studio Unit", "406 - Two Story Studio Unit"],
            "visible_spaces": ["504 - Studio Unit"],
            "mark_in_revit": True,
            "element_type": "window",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["transcript"] == "focus on 504 studio unit"
    assert payload["pipeline"]["event"]["focus_space"] == "504 - Studio Unit"
    assert payload["revit_revision"]["status"] == "recorded"
    assert payload["revit_revision"]["event_topic"] == "revit.revision_marked"
