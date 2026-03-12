"""
Unit tests for src/shared/db/vector_store.py
FOUND-03: pgvector embed-and-store + cosine similarity search.
"""
from unittest.mock import MagicMock, patch, call


def test_embed_and_store_calls_embed_batch(mock_db_conn):
    """embed_and_store() must call embed_batch with input_type='document'."""
    with patch("src.shared.db.vector_store.embed_batch") as mock_embed, \
         patch("src.shared.db.vector_store.get_connection", return_value=mock_db_conn), \
         patch("src.shared.db.vector_store.release_connection"):
        mock_embed.return_value = [[0.1] * 1024]

        from src.shared.db import vector_store
        vector_store.embed_and_store(["text chunk"], "test_source")

        mock_embed.assert_called_once()
        call_kwargs = mock_embed.call_args
        # Check input_type="document" was passed
        assert call_kwargs[1].get("input_type") == "document" or \
               (len(call_kwargs[0]) > 1 and call_kwargs[0][1] == "document")


def test_embed_and_store_inserts_into_db(mock_db_conn):
    """embed_and_store() must execute an INSERT into knowledge_chunks."""
    with patch("src.shared.db.vector_store.embed_batch") as mock_embed, \
         patch("src.shared.db.vector_store.get_connection", return_value=mock_db_conn), \
         patch("src.shared.db.vector_store.release_connection"):
        mock_embed.return_value = [[0.1] * 1024]

        from src.shared.db import vector_store
        vector_store.embed_and_store(["text chunk"], "test_source")

        # Check that cursor.execute was called with an INSERT targeting knowledge_chunks
        cursor = mock_db_conn.cursor().__enter__()
        executed_queries = [
            str(c.args[0]).lower()
            for c in cursor.execute.call_args_list
            if c.args
        ]
        assert any("knowledge_chunks" in q for q in executed_queries), \
            f"Expected INSERT into knowledge_chunks, got: {executed_queries}"


def test_search_embeds_query_with_query_type(mock_db_conn):
    """search() must call embed_text with input_type='query'."""
    mock_db_conn.cursor().__enter__().fetchall.return_value = []

    with patch("src.shared.db.vector_store.embed_text") as mock_embed, \
         patch("src.shared.db.vector_store.get_connection", return_value=mock_db_conn), \
         patch("src.shared.db.vector_store.release_connection"):
        mock_embed.return_value = [0.1] * 1024

        from src.shared.db import vector_store
        vector_store.search("test query", top_k=3)

        mock_embed.assert_called_once()
        call_kwargs = mock_embed.call_args
        assert call_kwargs[1].get("input_type") == "query" or \
               (len(call_kwargs[0]) > 1 and call_kwargs[0][1] == "query")


def test_search_returns_list(mock_db_conn):
    """search() must always return a list."""
    mock_db_conn.cursor().__enter__().fetchall.return_value = []

    with patch("src.shared.db.vector_store.embed_text") as mock_embed, \
         patch("src.shared.db.vector_store.get_connection", return_value=mock_db_conn), \
         patch("src.shared.db.vector_store.release_connection"):
        mock_embed.return_value = [0.1] * 1024

        from src.shared.db import vector_store
        result = vector_store.search("test query", top_k=3)

        assert isinstance(result, list)


def test_search_uses_cosine_operator(mock_db_conn):
    """search() SQL must use the pgvector <=> cosine distance operator."""
    mock_db_conn.cursor().__enter__().fetchall.return_value = []

    with patch("src.shared.db.vector_store.embed_text") as mock_embed, \
         patch("src.shared.db.vector_store.get_connection", return_value=mock_db_conn), \
         patch("src.shared.db.vector_store.release_connection"):
        mock_embed.return_value = [0.1] * 1024

        from src.shared.db import vector_store
        vector_store.search("test query")

        cursor = mock_db_conn.cursor().__enter__()
        executed_queries = [
            str(c.args[0])
            for c in cursor.execute.call_args_list
            if c.args
        ]
        assert any("<=>" in q for q in executed_queries), \
            f"Expected <=> cosine operator in SQL, got: {executed_queries}"
