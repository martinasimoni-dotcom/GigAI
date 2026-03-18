import pytest

from gigai.fireflies_stt import FirefliesIntegrationError, resolve_fireflies_transcript


class _FakeFirefliesClient:
    def __init__(self, api_key):  # noqa: ANN001
        self.api_key = api_key

    def get_recent_transcripts(self, limit=1):  # noqa: ANN001
        return [
            {
                "id": "ff_latest_1",
                "title": "Latest Meeting",
                "transcript_url": "https://app.fireflies.ai/view/1",
                "sentences": [
                    {"text": "please focus on east lobby"},
                    {"raw_text": "and check the issue"},
                ],
            }
        ]

    def get_transcript_by_id(self, transcript_id):  # noqa: ANN001
        return {
            "id": transcript_id,
            "title": "By ID Meeting",
            "transcript_url": "https://app.fireflies.ai/view/2",
            "sentences": [{"text": "focus on room 204"}],
        }

    def format_transcript(self, transcript):  # noqa: ANN001
        return "formatted transcript fallback"


def test_fireflies_disabled_returns_none(monkeypatch) -> None:
    monkeypatch.delenv("GIGAI_FIREFLIES_ENABLED", raising=False)
    text, metadata = resolve_fireflies_transcript({"fireflies_latest": True})
    assert text is None
    assert metadata == {}


def test_fireflies_latest_transcript_resolution(monkeypatch) -> None:
    monkeypatch.setenv("GIGAI_FIREFLIES_ENABLED", "true")
    monkeypatch.setenv("FIREFLIES_API_KEY", "test_key")
    monkeypatch.setattr("gigai.fireflies_stt._load_fireflies_api_class", lambda repo_path: _FakeFirefliesClient)

    text, metadata = resolve_fireflies_transcript({"fireflies_latest": True})

    assert "east lobby" in text
    assert metadata["fireflies_transcript_id"] == "ff_latest_1"
    assert metadata["fireflies_transcript_title"] == "Latest Meeting"


def test_fireflies_transcript_id_resolution(monkeypatch) -> None:
    monkeypatch.setenv("GIGAI_FIREFLIES_ENABLED", "true")
    monkeypatch.setenv("FIREFLIES_API_KEY", "test_key")
    monkeypatch.setattr("gigai.fireflies_stt._load_fireflies_api_class", lambda repo_path: _FakeFirefliesClient)

    text, metadata = resolve_fireflies_transcript({"fireflies_transcript_id": "ff_123"})

    assert "room 204" in text
    assert metadata["fireflies_transcript_id"] == "ff_123"


def test_fireflies_requires_api_key(monkeypatch) -> None:
    monkeypatch.setenv("GIGAI_FIREFLIES_ENABLED", "true")
    monkeypatch.delenv("FIREFLIES_API_KEY", raising=False)
    monkeypatch.setattr("gigai.fireflies_stt._load_fireflies_api_class", lambda repo_path: _FakeFirefliesClient)

    with pytest.raises(FirefliesIntegrationError, match="FIREFLIES_API_KEY"):
        resolve_fireflies_transcript({"fireflies_latest": True})


def test_fireflies_max_chars_limit(monkeypatch) -> None:
    monkeypatch.setenv("GIGAI_FIREFLIES_ENABLED", "true")
    monkeypatch.setenv("FIREFLIES_API_KEY", "test_key")
    monkeypatch.setenv("GIGAI_FIREFLIES_MAX_CHARS", "10")
    monkeypatch.setattr("gigai.fireflies_stt._load_fireflies_api_class", lambda repo_path: _FakeFirefliesClient)

    text, _ = resolve_fireflies_transcript({"fireflies_latest": True})

    assert text.endswith("...")
    assert len(text) <= 13
