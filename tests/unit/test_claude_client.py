"""
Unit tests for src/shared/llm/claude.py
FOUND-04: Claude Sonnet 4 + Haiku 4.5 client wrappers.
"""
from unittest.mock import MagicMock, patch


def test_call_sonnet_returns_string(mock_anthropic_client):
    """call_sonnet() must return a string."""
    with patch("src.shared.llm.claude._client", mock_anthropic_client):
        from src.shared.llm import claude
        result = claude.call_sonnet("hello", "system prompt")
        assert isinstance(result, str)


def test_call_haiku_returns_string(mock_anthropic_client):
    """call_haiku() must return a string."""
    with patch("src.shared.llm.claude._client", mock_anthropic_client):
        from src.shared.llm import claude
        result = claude.call_haiku("hello", "system prompt")
        assert isinstance(result, str)


def test_call_sonnet_uses_correct_model(mock_anthropic_client):
    """call_sonnet() must call messages.create with model='claude-sonnet-4-20250514'."""
    with patch("src.shared.llm.claude._client", mock_anthropic_client):
        from src.shared.llm import claude
        claude.call_sonnet("hello", "system prompt")
        call_kwargs = mock_anthropic_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-sonnet-4-20250514"


def test_call_haiku_uses_correct_model(mock_anthropic_client):
    """call_haiku() must call messages.create with model='claude-haiku-4-5-20251001'."""
    with patch("src.shared.llm.claude._client", mock_anthropic_client):
        from src.shared.llm import claude
        claude.call_haiku("hello", "system prompt")
        call_kwargs = mock_anthropic_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-haiku-4-5-20251001"


def test_call_sonnet_passes_system_prompt(mock_anthropic_client):
    """call_sonnet() must pass system='system prompt' to messages.create."""
    with patch("src.shared.llm.claude._client", mock_anthropic_client):
        from src.shared.llm import claude
        claude.call_sonnet("hello", "system prompt")
        call_kwargs = mock_anthropic_client.messages.create.call_args[1]
        assert call_kwargs["system"] == "system prompt"


def test_call_sonnet_with_output_schema(mock_anthropic_client):
    """call_sonnet() with output_schema must call messages.create without raising."""
    with patch("src.shared.llm.claude._client", mock_anthropic_client):
        from src.shared.llm import claude
        # Should not raise any exception
        claude.call_sonnet("prompt", "system", output_schema={"type": "object"})
        mock_anthropic_client.messages.create.assert_called()
