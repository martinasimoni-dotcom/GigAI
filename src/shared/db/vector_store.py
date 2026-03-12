"""
pgvector operations: embed text chunks and perform cosine similarity search.
FOUND-03

Storage uses input_type="document" (Voyage-3 asymmetric embedding).
Search uses input_type="query" (different embedding space for better recall).
"""
import logging
from typing import Any

from psycopg2.extras import execute_values

from src.shared.db.postgres import get_connection, release_connection
from src.shared.llm.voyage import embed_text, embed_batch

logger = logging.getLogger(__name__)

KNOWLEDGE_CHUNKS_TABLE = "knowledge_chunks"


def embed_and_store(
    texts: list[str],
    source: str,
    metadata: dict | None = None,
) -> int:
    """
    Embed text chunks via Voyage-3 and store in knowledge_chunks table.

    Uses input_type="document" for storage — Voyage-3 asymmetric embeddings
    improve retrieval quality when query uses input_type="query".

    Returns the number of chunks stored.
    """
    if not texts:
        return 0

    metadata = metadata or {}
    embeddings = embed_batch(texts, input_type="document")

    conn = get_connection()
    try:
        rows = [
            (text, embedding, source, metadata)
            for text, embedding in zip(texts, embeddings)
        ]
        with conn.cursor() as cur:
            execute_values(
                cur,
                f"INSERT INTO {KNOWLEDGE_CHUNKS_TABLE} (content, embedding, source, metadata) VALUES %s",
                rows,
            )
        conn.commit()
        logger.info(f"Stored {len(rows)} chunks from source='{source}'")
        return len(rows)
    finally:
        release_connection(conn)


def search(
    query_text: str,
    top_k: int = 5,
    source_filter: str | None = None,
) -> list[dict]:
    """
    Embed query_text and return top_k most similar knowledge chunks.

    Uses input_type="query" for the search embedding — asymmetric
    to the "document" embeddings stored during embed_and_store().

    Uses the pgvector <=> cosine distance operator.
    Lower <=> distance = more similar (cosine distance, not similarity).
    The SELECT converts to similarity: 1 - (embedding <=> query_vec).
    """
    query_embedding = embed_text(query_text, input_type="query")

    conn = get_connection()
    try:
        base_query = """
            SELECT id, content, source, metadata,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM knowledge_chunks
            {where}
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """
        if source_filter:
            where = "WHERE source = %s"
            params = (query_embedding, source_filter, query_embedding, top_k)
            query = base_query.format(where=where)
        else:
            where = ""
            params = (query_embedding, query_embedding, top_k)
            query = base_query.format(where=where)

        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall() or []
        return [dict(row) for row in rows]
    finally:
        release_connection(conn)
