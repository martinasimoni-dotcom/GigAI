"""
Unit tests for src/shared/db/postgres.py
FOUND-02: PostgreSQL connection pool with query helpers.

Note: postgres.py imports config.settings at module level (fail-fast pattern).
All tests use the test_env fixture to ensure env vars are set before import.
"""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch):
    """Ensure required env vars are set for all tests in this module."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("VOYAGE_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    # Remove cached settings module so it reimports with the new env
    sys.modules.pop("config.settings", None)
    sys.modules.pop("src.shared.db.postgres", None)


def test_get_connection_calls_register_vector(mock_db_conn):
    """get_connection() must call register_vector with the returned connection."""
    from src.shared.db import postgres

    mock_pool = MagicMock()
    mock_pool.getconn.return_value = mock_db_conn

    with patch.object(postgres, "get_pool", return_value=mock_pool), \
         patch.object(postgres, "register_vector") as mock_reg:
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
