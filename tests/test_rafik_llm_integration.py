from gigai.rafik_llm import infer_space_focus_from_rafik
from gigai.voice import build_voice_focus_payload


def test_rafik_llm_disabled_returns_none(monkeypatch) -> None:
    monkeypatch.delenv("GIGAI_RAFIK_LLM_ENABLED", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    result = infer_space_focus_from_rafik(
        transcript="focus on East Lobby",
        available_spaces=["East Lobby", "West Lobby"],
    )

    assert result is None


def test_voice_payload_uses_rafik_result_when_available(monkeypatch) -> None:
    class _Inference:
        space_name = "East Lobby"
        reason = "rafik_llm_space_match"
        confidence = 0.94
        provider = "rafik_claude:claude-haiku-4-5-20251001"

    monkeypatch.setattr("gigai.voice.infer_space_focus_from_rafik", lambda *args, **kwargs: _Inference())

    payload = {
        "projectId": "project_alpha",
        "transcript": "please focus on east lobby",
        "available_spaces": ["East Lobby", "West Lobby"],
    }

    normalized = build_voice_focus_payload(payload)

    assert normalized["llm_space_name"] == "East Lobby"
    assert normalized["llm_reason"] == "rafik_llm_space_match"
    assert normalized["llm_confidence"] == 0.94
    assert normalized["llm_provider"].startswith("rafik_claude")


def test_voice_payload_falls_back_to_local_llm_when_rafik_unavailable(monkeypatch) -> None:
    monkeypatch.setattr("gigai.voice.infer_space_focus_from_rafik", lambda *args, **kwargs: None)

    payload = {
        "projectId": "project_alpha",
        "transcript": "go to east loby and mark revision",
        "available_spaces": ["East Lobby", "West Lobby"],
    }

    normalized = build_voice_focus_payload(payload)

    assert normalized.get("llm_space_name") == "East Lobby"
    assert normalized.get("llm_provider") in {"gigai_local", "rafik_claude:claude-haiku-4-5-20251001"}
