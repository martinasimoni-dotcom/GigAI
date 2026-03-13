"""
Unit tests for Gmail and Calendar polling connectors (INPUT-03, INPUT-04).
Google API service clients and publish_event are fully mocked.
"""
import sys
from unittest.mock import MagicMock, patch
import pytest


@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    """Set required env vars and reload connector modules before each test."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("VOYAGE_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    # Pop all relevant modules so they re-import with correct env vars
    for mod in list(sys.modules.keys()):
        if mod.startswith("src.input.connectors") or mod == "config.settings" or mod == "src.input.pubsub":
            sys.modules.pop(mod, None)
    yield
    # Clean up after test
    for mod in list(sys.modules.keys()):
        if mod.startswith("src.input.connectors") or mod == "config.settings" or mod == "src.input.pubsub":
            sys.modules.pop(mod, None)


# --- Gmail tests ---------------------------------------------------------------

def _make_gmail_service_mock(message_ids: list[str]) -> MagicMock:
    """Build a MagicMock Gmail service returning the given message ids."""
    service = MagicMock()
    # list() returns {"messages": [{"id": id, "threadId": "t"} for id in message_ids]}
    list_result = {"messages": [{"id": mid, "threadId": "thread-1"} for mid in message_ids]} if message_ids else {}
    service.users().messages().list().execute.return_value = list_result
    # get() returns a full message dict for any id
    def mock_get(**kwargs):
        mock_exec = MagicMock()
        mock_exec.execute.return_value = {"id": kwargs.get("id", "unknown"), "payload": {"headers": []}}
        return mock_exec
    service.users().messages().get = MagicMock(side_effect=mock_get)
    return service


def test_poll_gmail(mock_gmail_service):
    """poll_gmail publishes one RawEvent per matching email."""
    import src.input.connectors.gmail as gmail_module
    mock_publish = MagicMock(return_value="pub-msg-id-1")
    gmail_service = _make_gmail_service_mock(["msg-1"])
    with patch.object(gmail_module, "_build_gmail_service", return_value=gmail_service):
        result = gmail_module.poll_gmail(publish_fn=mock_publish)
    assert mock_publish.call_count == 1
    raw_event_arg = mock_publish.call_args[0][0]
    assert raw_event_arg.source == "gmail"
    assert "gmail_message_id" in raw_event_arg.raw_payload


def test_poll_gmail_no_match():
    """poll_gmail publishes nothing when no matching emails."""
    import src.input.connectors.gmail as gmail_module
    mock_publish = MagicMock()
    gmail_service = _make_gmail_service_mock([])
    with patch.object(gmail_module, "_build_gmail_service", return_value=gmail_service):
        result = gmail_module.poll_gmail(publish_fn=mock_publish)
    assert mock_publish.call_count == 0
    assert result == []


def test_poll_gmail_returns_message_ids():
    """poll_gmail returns list of published message_ids."""
    import src.input.connectors.gmail as gmail_module
    mock_publish = MagicMock(side_effect=["id-a", "id-b"])
    gmail_service = _make_gmail_service_mock(["msg-1", "msg-2"])
    with patch.object(gmail_module, "_build_gmail_service", return_value=gmail_service):
        result = gmail_module.poll_gmail(publish_fn=mock_publish)
    assert result == ["id-a", "id-b"]


def test_poll_gmail_query_contains_keywords():
    """GMAIL_QUERY contains required material-related keywords."""
    import src.input.connectors.gmail as gmail_module
    for kw in ["material", "substitution"]:
        assert kw in gmail_module.GMAIL_QUERY, f"Expected '{kw}' in GMAIL_QUERY"
    assert "is:unread" in gmail_module.GMAIL_QUERY


# --- Calendar tests ------------------------------------------------------------

def _make_calendar_service_mock(events: list[dict]) -> MagicMock:
    """Build a MagicMock Calendar service returning the given events."""
    service = MagicMock()
    service.events().list().execute.return_value = {"items": events}
    return service


def test_poll_calendar():
    """poll_calendar publishes one RawEvent for a matching event."""
    import src.input.connectors.calendar as calendar_module
    mock_publish = MagicMock(return_value="cal-pub-id-1")
    event = {"id": "cal-1", "summary": "delivery of windows", "description": ""}
    cal_service = _make_calendar_service_mock([event])
    with patch.object(calendar_module, "_build_calendar_service", return_value=cal_service):
        result = calendar_module.poll_calendar(publish_fn=mock_publish)
    assert mock_publish.call_count == 1
    raw_event_arg = mock_publish.call_args[0][0]
    assert raw_event_arg.source == "calendar"
    assert raw_event_arg.raw_payload == event


def test_poll_calendar_no_match():
    """poll_calendar skips events with no matching keywords."""
    import src.input.connectors.calendar as calendar_module
    mock_publish = MagicMock()
    event = {"id": "cal-2", "summary": "birthday party", "description": "celebrate with team"}
    cal_service = _make_calendar_service_mock([event])
    with patch.object(calendar_module, "_build_calendar_service", return_value=cal_service):
        result = calendar_module.poll_calendar(publish_fn=mock_publish)
    assert mock_publish.call_count == 0
    assert result == []


def test_poll_calendar_description_match():
    """poll_calendar matches on description even when summary has no keywords."""
    import src.input.connectors.calendar as calendar_module
    mock_publish = MagicMock(return_value="desc-match-id")
    event = {"id": "cal-3", "summary": "team sync", "description": "material inspection needed for third floor"}
    cal_service = _make_calendar_service_mock([event])
    with patch.object(calendar_module, "_build_calendar_service", return_value=cal_service):
        result = calendar_module.poll_calendar(publish_fn=mock_publish)
    assert mock_publish.call_count == 1


def test_poll_calendar_keywords():
    """CALENDAR_KEYWORDS contains required construction event keywords."""
    import src.input.connectors.calendar as calendar_module
    for kw in ["delivery", "installation", "material", "inspection"]:
        assert kw in calendar_module.CALENDAR_KEYWORDS, f"Expected '{kw}' in CALENDAR_KEYWORDS"
