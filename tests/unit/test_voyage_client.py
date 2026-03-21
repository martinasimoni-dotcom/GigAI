"""
Unit tests for src/shared/llm/voyage.py
FOUND-05: Voyage-3 embedding client.

CRITICAL: voyageai.Client().embed() returns EmbeddingsObject with .embeddings attribute.
Access result.embeddings[0] (single) or result.embeddings (batch). Never result[0].

Note: voyage.py uses lazy init (_get_client()) to avoid import-time failure when
VOYAGE_API_KEY is not set. Tests patch _client directly.
"""
import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def reset_voyage_client():
    """Reset the voyage module's lazy-initialized client before each test."""
    sys.modules.pop("src.shared.llm.voyage", None)


def test_embed_text_returns_list_float(mock_voyage_client):
    """embed_text() must return a list of 1024 floats."""
    from src.shared.llm import voyage

    with patch.object(voyage, "_client", mock_voyage_client):
        result = voyage.embed_text("test text")
        assert isinstance(result, list)
        assert len(result) == 1024
        assert all(isinstance(x, float) for x in result)


def test_embed_text_uses_query_input_type(mock_voyage_client):
    """embed_text() must call client.embed with input_type='query' by default."""
    from src.shared.llm import voyage

    with patch.object(voyage, "_client", mock_voyage_client):
        voyage.embed_text("test text")
        call_kwargs = mock_voyage_client.embed.call_args[1]
        assert call_kwargs.get("input_type") == "query"


def test_embed_batch_returns_list_of_lists(mock_voyage_client):
    """embed_batch() must return a list of 2 items when given 2 texts."""
    # Update fixture to return 2 embeddings
    embed_response = MagicMock()
    embed_response.embeddings = [[0.1] * 1024, [0.2] * 1024]
    mock_voyage_client.embed.return_value = embed_response

    from src.shared.llm import voyage

    with patch.object(voyage, "_client", mock_voyage_client):
        result = voyage.embed_batch(["text1", "text2"])
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(item, list) for item in result)


def test_embed_batch_uses_document_input_type(mock_voyage_client):
    """embed_batch() must call client.embed with input_type='document' by default."""
    from src.shared.llm import voyage

    with patch.object(voyage, "_client", mock_voyage_client):
        voyage.embed_batch(["text1"])
        call_kwargs = mock_voyage_client.embed.call_args[1]
        assert call_kwargs.get("input_type") == "document"


def test_embed_text_accesses_embeddings_attribute(mock_voyage_client):
    """embed_text() must access result.embeddings[0], not result[0]."""
    embed_response = MagicMock(spec=["embeddings"])
    embed_response.embeddings = [[0.5] * 1024]
    mock_voyage_client.embed.return_value = embed_response

    from src.shared.llm import voyage

    with patch.object(voyage, "_client", mock_voyage_client):
        result = voyage.embed_text("test text")
        # If the code uses result[0] instead of result.embeddings[0],
        # MagicMock with spec=["embeddings"] will raise TypeError.
        assert result == [0.5] * 1024


def test_embed_batch_uses_voyage_3_model(mock_voyage_client):
    """embed_batch() must call client.embed with model='voyage-3'."""
    from src.shared.llm import voyage

    with patch.object(voyage, "_client", mock_voyage_client):
        voyage.embed_batch(["text1"])
        call_kwargs = mock_voyage_client.embed.call_args[1]
        assert call_kwargs.get("model") == "voyage-3"
