"""
Voyage-3 embedding client.
FOUND-05

Uses voyageai.Client with model="voyage-3" (1024-dimensional vectors).

IMPORTANT: embed() returns an EmbeddingsObject, not a list.
Always access result.embeddings[0] (single) or result.embeddings (batch).
Never use result[0] — that is a TypeError.

input_type asymmetry:
- "document" for embedding text chunks being stored in pgvector
- "query"    for embedding search queries at retrieval time
This asymmetry improves retrieval recall quality.
"""
import logging

import voyageai

logger = logging.getLogger(__name__)

# Locked model identifier
VOYAGE_MODEL = "voyage-3"

# Lazy client — initialized on first call to avoid import-time failure when
# VOYAGE_API_KEY is not set (e.g., during pytest collection or in test environments
# that patch the client). Call _get_client() instead of using _client directly.
_client: voyageai.Client | None = None


def _get_client() -> voyageai.Client:
    """Get or create the Voyage AI client (lazy init)."""
    global _client
    if _client is None:
        _client = voyageai.Client()
    return _client


def embed_text(text: str, input_type: str = "query") -> list[float]:
    """
    Embed a single text string using Voyage-3.

    Args:
        text: The text to embed.
        input_type: "query" for search queries (default), "document" for storage.
                    Using the correct type improves retrieval recall.

    Returns:
        List of 1024 floats representing the embedding.
    """
    result = _get_client().embed(
        texts=[text],
        model=VOYAGE_MODEL,
        input_type=input_type,
    )
    # result is EmbeddingsObject — access .embeddings[0], NOT result[0]
    return result.embeddings[0]


def embed_batch(texts: list[str], input_type: str = "document") -> list[list[float]]:
    """
    Embed multiple text strings using Voyage-3.

    Args:
        texts: List of texts to embed. Voyage-3 supports up to 128 per call.
        input_type: "document" for storage chunks (default), "query" for search.

    Returns:
        List of embedding vectors (each a list of 1024 floats).
    """
    if not texts:
        return []

    result = _get_client().embed(
        texts=texts,
        model=VOYAGE_MODEL,
        input_type=input_type,
    )
    # result is EmbeddingsObject — access .embeddings, NOT result directly
    return result.embeddings
