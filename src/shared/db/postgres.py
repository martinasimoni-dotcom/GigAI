"""
PostgreSQL connection pool with query helpers.
FOUND-02

Critical: register_vector() is called per-connection (not globally).
With ThreadedConnectionPool, each connection is a separate psycopg2
connection object. register_vector must be invoked on each one.
"""
import logging
from typing import Any

import psycopg2
import psycopg2.pool
import psycopg2.extras
from pgvector.psycopg2 import register_vector

from config.settings import settings

logger = logging.getLogger(__name__)

_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    """Get or create the module-level connection pool."""
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=settings.database_url,
            cursor_factory=psycopg2.extras.RealDictCursor,
        )
        logger.info("PostgreSQL connection pool created (min=1, max=10)")
    return _pool


def get_connection():
    """
    Get a connection from the pool and register pgvector type adapter.

    register_vector(conn) must be called on every connection retrieved
    from the pool. It registers the psycopg2 type adapters that allow
    Python lists/numpy arrays to be sent as PostgreSQL vector() types.
    Failing to call this causes: psycopg2.ProgrammingError: can't adapt type 'list'
    """
    conn = get_pool().getconn()
    register_vector(conn)  # must call per-connection — not once globally
    return conn


def release_connection(conn) -> None:
    """Return a connection to the pool."""
    get_pool().putconn(conn)


def execute(conn, query: str, params: list | tuple = ()) -> None:
    """Execute a write query (INSERT, UPDATE, DELETE, DDL)."""
    with conn.cursor() as cur:
        cur.execute(query, params)
    conn.commit()


def fetch_one(conn, query: str, params: list | tuple = ()) -> dict | None:
    """Execute a SELECT query and return the first row as a dict, or None."""
    with conn.cursor() as cur:
        cur.execute(query, params)
        return cur.fetchone()


def fetch_all(conn, query: str, params: list | tuple = ()) -> list[dict]:
    """Execute a SELECT query and return all rows as a list of dicts."""
    with conn.cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall() or []


def execute_many(conn, query: str, params_list: list[tuple]) -> None:
    """Execute a parameterized query for multiple rows efficiently."""
    with conn.cursor() as cur:
        cur.executemany(query, params_list)
    conn.commit()


def close_pool() -> None:
    """Close all connections in the pool. Call at application shutdown."""
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None
        logger.info("PostgreSQL connection pool closed")
