"""
Shared pytest fixtures for all GigAI unit tests.
"""
import os
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client that returns a fixed response."""
    client = MagicMock()
    content_mock = MagicMock()
    content_mock.text = '{"result": "ok"}'
    response_mock = MagicMock()
    response_mock.content = [content_mock]
    client.messages.create.return_value = response_mock
    return client


@pytest.fixture
def mock_voyage_client():
    """Mock Voyage AI client that returns a fixed embedding."""
    client = MagicMock()
    embed_response = MagicMock()
    embed_response.embeddings = [[0.1] * 1024]
    client.embed.return_value = embed_response
    return client


@pytest.fixture
def mock_db_conn():
    """Mock psycopg2 connection with a cursor."""
    cursor_mock = MagicMock()
    cursor_mock.fetchone = MagicMock(return_value=None)
    cursor_mock.fetchall = MagicMock(return_value=[])
    cursor_mock.execute = MagicMock(return_value=None)

    conn_mock = MagicMock()
    conn_mock.cursor.return_value = cursor_mock
    return conn_mock


@pytest.fixture
def test_env(monkeypatch):
    """Set required environment variables for testing."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("VOYAGE_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")


@pytest.fixture
def mock_pubsub_publisher():
    """Mock google.cloud.pubsub_v1.PublisherClient."""
    publisher = MagicMock()
    future = MagicMock()
    future.result.return_value = "test-message-id"
    publisher.publish.return_value = future
    publisher.topic_path.return_value = "projects/test-project/topics/raw-events"
    return publisher


@pytest.fixture
def mock_gmail_service():
    """Mock Google Gmail API service."""
    service = MagicMock()
    return service


@pytest.fixture
def mock_calendar_service():
    """Mock Google Calendar API service."""
    service = MagicMock()
    return service
