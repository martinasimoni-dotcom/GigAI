"""
Integration tests — pgvector semantic search via real Voyage-3 embeddings.
Requires: .env with VOYAGE_API_KEY, DATABASE_URL and seeded knowledge_chunks table.
Tests skip automatically if DB is empty or credentials are absent.
Run: pytest tests/integration/test_knowledge_retrieval.py -m integration -v
"""
from dotenv import load_dotenv

load_dotenv()

import os  # noqa: E402

import pytest  # noqa: E402

pytestmark = [pytest.mark.integration, pytest.mark.requires_db, pytest.mark.requires_api]


def _get_knowledge_chunks_count() -> int:
    """Query knowledge_chunks row count from the real DB. Returns 0 on any error."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return 0
    try:
        import psycopg2  # lazy import — avoids triggering settings singleton at collection time

        conn = psycopg2.connect(database_url)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM knowledge_chunks")
                row = cur.fetchone()
                return row[0] if row else 0
        finally:
            conn.close()
    except Exception:
        return 0


# Module-level skip: skip entire module if knowledge_chunks table is empty
_CHUNK_COUNT = _get_knowledge_chunks_count()
if _CHUNK_COUNT == 0:
    pytestmark = [
        pytest.mark.integration,
        pytest.mark.requires_db,
        pytest.mark.requires_api,
        pytest.mark.skip(
            reason=(
                "knowledge_chunks table is empty or unreachable — "
                "run scripts/seed_knowledge.py to populate before integration tests"
            )
        ),
    ]


class TestKnowledgeRetrieval:
    """Real pgvector semantic search integration tests."""

    def test_supplier_query_returns_team_directory_result(self):
        """Semantic search for wood supplier returns team_directory source."""
        if not os.getenv("VOYAGE_API_KEY"):
            pytest.skip("VOYAGE_API_KEY not set — real Voyage embeddings required")

        from src.shared.db.vector_store import search  # lazy import

        results = search("wood frame supplier pricing contact", top_k=1)

        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        source = results[0]["source"]
        assert "team_directory" in source, (
            f"Expected top result from team_directory, got source: {source!r}"
        )
        similarity = results[0]["similarity"]
        assert similarity > 0.7, (
            f"Expected similarity > 0.7 for supplier query, got {similarity:.4f}"
        )

    def test_rules_query_returns_rules_result(self):
        """Semantic search for approval rules returns rules source."""
        if not os.getenv("VOYAGE_API_KEY"):
            pytest.skip("VOYAGE_API_KEY not set — real Voyage embeddings required")

        from src.shared.db.vector_store import search  # lazy import

        results = search("material change approval cost threshold", top_k=1)

        assert len(results) >= 1, f"Expected at least 1 result, got {len(results)}"
        source = results[0]["source"]
        assert "rules" in source, (
            f"Expected top result from rules source, got source: {source!r}"
        )
        similarity = results[0]["similarity"]
        assert similarity > 0.7, (
            f"Expected similarity > 0.7 for rules query, got {similarity:.4f}"
        )

    def test_historical_pattern_query_returns_historical_result(self):
        """Semantic search for past approvals returns historical_patterns source."""
        if not os.getenv("VOYAGE_API_KEY"):
            pytest.skip("VOYAGE_API_KEY not set — real Voyage embeddings required")

        from src.shared.db.vector_store import search  # lazy import

        results = search("past aluminum to wood window change approved", top_k=1)

        assert len(results) >= 1, f"Expected at least 1 result, got {len(results)}"
        source = results[0]["source"]
        assert "historical_patterns" in source, (
            f"Expected top result from historical_patterns source, got source: {source!r}"
        )
        similarity = results[0]["similarity"]
        assert similarity > 0.7, (
            f"Expected similarity > 0.7 for historical query, got {similarity:.4f}"
        )

    def test_search_returns_ranked_by_similarity(self):
        """Search results are returned in descending similarity order."""
        if not os.getenv("VOYAGE_API_KEY"):
            pytest.skip("VOYAGE_API_KEY not set — real Voyage embeddings required")

        from src.shared.db.vector_store import search  # lazy import

        results = search("wood frame supplier", top_k=3)

        assert len(results) >= 1, f"Expected at least 1 result for supplier query"
        # Verify descending sort: first result similarity >= last result similarity
        first_similarity = results[0]["similarity"]
        last_similarity = results[-1]["similarity"]
        assert first_similarity >= last_similarity, (
            f"Expected results sorted descending by similarity: "
            f"first={first_similarity:.4f}, last={last_similarity:.4f}"
        )
