"""
SQL migration tests (FOUND-09): verify infra/sql/*.sql files exist and have correct DDL.
"""
import pathlib

import pytest

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent
SQL_001 = PROJECT_ROOT / "infra" / "sql" / "001_create_tables.sql"
SQL_002 = PROJECT_ROOT / "infra" / "sql" / "002_create_indexes.sql"


def test_001_file_exists():
    """001_create_tables.sql must exist."""
    assert SQL_001.exists(), f"Missing: {SQL_001}"


def test_002_file_exists():
    """002_create_indexes.sql must exist."""
    assert SQL_002.exists(), f"Missing: {SQL_002}"


def test_001_has_extension():
    """001 file must contain CREATE EXTENSION for pgvector."""
    content = SQL_001.read_text(encoding="utf-8")
    assert "CREATE EXTENSION" in content


def test_001_has_all_tables():
    """001 file must define all 6 required tables."""
    content = SQL_001.read_text(encoding="utf-8")
    for table in ["events", "proposals", "actions", "feedback", "past_changes", "knowledge_chunks"]:
        assert table in content, f"Table '{table}' not found in 001_create_tables.sql"


def test_001_has_vector_column():
    """001 file must contain vector(1024) column type."""
    content = SQL_001.read_text(encoding="utf-8")
    assert "vector(1024)" in content


def test_002_has_hnsw():
    """002 file must contain HNSW index definition."""
    content = SQL_002.read_text(encoding="utf-8")
    assert "hnsw" in content.lower()


def test_002_has_cosine_ops():
    """002 file must use vector_cosine_ops operator class."""
    content = SQL_002.read_text(encoding="utf-8")
    assert "vector_cosine_ops" in content
