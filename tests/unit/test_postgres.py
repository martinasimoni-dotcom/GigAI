"""
Unit tests for src/shared/db/postgres.py
FOUND-02: PostgreSQL connection pool with query helpers.
"""
from unittest.mock import MagicMock, patch


def test_get_connection_calls_register_vector(mock_db_conn):
    """get_connection() must call register_vector with the returned connection."""
    with patch("psycopg2.pool.ThreadedConnectionPool") as mock_pool_cls, \
         patch("pgvector.psycopg2.register_vector") as mock_reg:
        mock_pool = MagicMock()
        mock_pool.getconn.return_value = mock_db_conn
        mock_pool_cls.return_value = mock_pool

        # Force module reimport so pool is reset
        import importlib
        import sys
        sys.modules.pop("src.shared.db.postgres", None)

        from src.shared.db import postgres
        postgres._pool = None  # reset the module-level pool

        with patch.object(postgres, "get_pool", return_value=mock_pool), \
             patch("src.shared.db.postgres.register_vector", mock_reg):
            conn = postgres.get_connection()
            mock_reg.assert_called_once_with(conn)


def test_execute_runs_query(mock_db_conn):
    """execute() must call cursor.execute with the provided query."""
    from src.shared.db import postgres

    postgres.execute(mock_db_conn, "SELECT 1", [])
    mock_db_conn.cursor().__enter__().execute.assert_called()


def test_fetch_one_returns_row(mock_db_conn):
    """fetch_one() must return the result of cursor.fetchone()."""
    from src.shared.db import postgres

    expected = {"id": 1}
    mock_db_conn.cursor().__enter__().fetchone.return_value = expected

    result = postgres.fetch_one(mock_db_conn, "SELECT 1")
    assert result == expected


def test_fetch_all_returns_rows(mock_db_conn):
    """fetch_all() must return the result of cursor.fetchall()."""
    from src.shared.db import postgres

    expected = [{"id": 1}, {"id": 2}]
    mock_db_conn.cursor().__enter__().fetchall.return_value = expected

    result = postgres.fetch_all(mock_db_conn, "SELECT 1")
    assert len(result) == 2


def test_execute_many_calls_executemany(mock_db_conn):
    """execute_many() must call cursor.executemany."""
    from src.shared.db import postgres

    postgres.execute_many(mock_db_conn, "INSERT INTO t VALUES (%s)", [(1,), (2,)])
    mock_db_conn.cursor().__enter__().executemany.assert_called()
