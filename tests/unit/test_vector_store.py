"""
Unit tests for src/shared/db/vector_store.py
FOUND-03: pgvector embed-and-store + cosine similarity search.

Note: vector_store.py imports postgres.py which imports config.settings at module level.
All tests use the autouse env fixture to ensure env vars are set before import.
"""
import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch):
    """Ensure required env vars are set for all tests in this module."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("VOYAGE_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    # Remove cached modules so they reimport with the new env
    sys.modules.pop("config.settings", None)
    sys.modules.pop("src.shared.db.postgres", None)
    sys.modules.pop("src.shared.db.vector_store", None)
    sys.modules.pop("src.shared.llm.voyage", None)


def test_embed_and_store_calls_embed_batch(mock_db_conn):
    """embed_and_store() must call embed_batch with input_type='document'."""
    from src.shared.db import vector_store

    with patch.object(vector_store, "embed_batch") as mock_embed, \
         patch.object(vector_store, "get_connection", return_value=mock_db_conn), \
         patch.object(vector_store, "release_connection"), \
         patch.object(vector_store, "execute_values"):
        mock_embed.return_value = [[0.1] * 1024]

        vector_store.embed_and_store(["text chunk"], "test_source")

        mock_embed.assert_called_once()
        call_args = mock_embed.call_args
        # Check input_type="document" was passed as keyword arg
        assert call_args[1].get("input_type") == "document" or \
               (len(call_args[0]) > 1 and call_args[0][1] == "document")


def test_embed_and_store_inserts_into_db(mock_db_conn):
    """embed_and_store() must execute an INSERT into knowledge_chunks."""
    from src.shared.db import vector_store

    with patch.object(vector_store, "embed_batch") as mock_embed, \
         patch.object(vector_store, "get_connection", return_value=mock_db_conn), \
         patch.object(vector_store, "release_connection"), \
         patch.object(vector_store, "execute_values") as mock_exec_values:
        mock_embed.return_value = [[0.1] * 1024]

        vector_store.embed_and_store(["text chunk"], "test_source")

        # Check that execute_values was called with a query targeting knowledge_chunks
        mock_exec_values.assert_called_once()
        call_args = mock_exec_values.call_args
        query_str = call_args[0][1].lower()  # second positional arg is the query string
        assert "knowledge_chunks" in query_str, \
            f"Expected INSERT into knowledge_chunks, got: {query_str}"


def test_search_embeds_query_with_query_type(mock_db_conn):
    """search() must call embed_text with input_type='query'."""
    mock_db_conn.cursor().__enter__().fetchall.return_value = []

    from src.shared.db import vector_store

    with patch.object(vector_store, "embed_text") as mock_embed, \
         patch.object(vector_store, "get_connection", return_value=mock_db_conn), \
         patch.object(vector_store, "release_connection"):
        mock_embed.return_value = [0.1] * 1024

        vector_store.search("test query", top_k=3)

        mock_embed.assert_called_once()
        call_args = mock_embed.call_args
        assert call_args[1].get("input_type") == "query" or \
               (len(call_args[0]) > 1 and call_args[0][1] == "query")


def test_search_returns_list(mock_db_conn):
    """search() must always return a list."""
    mock_db_conn.cursor().__enter__().fetchall.return_value = []

    from src.shared.db import vector_store

    with patch.object(vector_store, "embed_text") as mock_embed, \
         patch.object(vector_store, "get_connection", return_value=mock_db_conn), \
         patch.object(vector_store, "release_connection"):
        mock_embed.return_value = [0.1] * 1024

        result = vector_store.search("test query", top_k=3)

        assert isinstance(result, list)


def test_search_uses_cosine_operator(mock_db_conn):
    """search() SQL must use the pgvector <=> cosine distance operator."""
    mock_db_conn.cursor().__enter__().fetchall.return_value = []

    from src.shared.db import vector_store

    with patch.object(vector_store, "embed_text") as mock_embed, \
         patch.object(vector_store, "get_connection", return_value=mock_db_conn), \
         patch.object(vector_store, "release_connection"):
        mock_embed.return_value = [0.1] * 1024

        vector_store.search("test query")

        cursor = mock_db_conn.cursor().__enter__()
        executed_queries = [
            str(c.args[0])
            for c in cursor.execute.call_args_list
            if c.args
        ]
        assert any("<=>" in q for q in executed_queries), \
            f"Expected <=> cosine operator in SQL, got: {executed_queries}"
