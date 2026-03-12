"""
Unit tests for src/shared/llm/claude.py
FOUND-04: Claude Sonnet 4 + Haiku 4.5 client wrappers.

Note: claude.py creates anthropic.Anthropic() at module level. This is OK
since Anthropic() does not fail without an API key (it fails on API calls only).
Tests patch _client at the module level using patch.object.
"""
from unittest.mock import MagicMock, patch

import pytest


def test_call_sonnet_returns_string(mock_anthropic_client):
    """call_sonnet() must return a string."""
    from src.shared.llm import claude

    with patch.object(claude, "_client", mock_anthropic_client):
        result = claude.call_sonnet("hello", "system prompt")
        assert isinstance(result, str)


def test_call_haiku_returns_string(mock_anthropic_client):
    """call_haiku() must return a string."""
    from src.shared.llm import claude

    with patch.object(claude, "_client", mock_anthropic_client):
        result = claude.call_haiku("hello", "system prompt")
        assert isinstance(result, str)


def test_call_sonnet_uses_correct_model(mock_anthropic_client):
    """call_sonnet() must call messages.create with model='claude-sonnet-4-20250514'."""
    from src.shared.llm import claude

    with patch.object(claude, "_client", mock_anthropic_client):
        claude.call_sonnet("hello", "system prompt")
        call_kwargs = mock_anthropic_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-sonnet-4-20250514"


def test_call_haiku_uses_correct_model(mock_anthropic_client):
    """call_haiku() must call messages.create with model='claude-haiku-4-5-20251001'."""
    from src.shared.llm import claude

    with patch.object(claude, "_client", mock_anthropic_client):
        claude.call_haiku("hello", "system prompt")
        call_kwargs = mock_anthropic_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-haiku-4-5-20251001"


def test_call_sonnet_passes_system_prompt(mock_anthropic_client):
    """call_sonnet() must pass system='system prompt' to messages.create."""
    from src.shared.llm import claude

    with patch.object(claude, "_client", mock_anthropic_client):
        claude.call_sonnet("hello", "system prompt")
        call_kwargs = mock_anthropic_client.messages.create.call_args[1]
        assert call_kwargs["system"] == "system prompt"


def test_call_sonnet_with_output_schema(mock_anthropic_client):
    """call_sonnet() with output_schema must call messages.create without raising."""
    from src.shared.llm import claude

    with patch.object(claude, "_client", mock_anthropic_client):
        # Should not raise any exception
        claude.call_sonnet("prompt", "system", output_schema={"type": "object"})
        mock_anthropic_client.messages.create.assert_called()
