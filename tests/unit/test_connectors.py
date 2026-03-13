"""
Wave 0 test stubs for INPUT-03 (Gmail connector) and INPUT-04 (Calendar connector).
All tests are skipped until implementation is complete.
"""
import pytest

try:
    from src.input.connectors.gmail import poll_gmail
    from src.input.connectors.calendar import poll_calendar
    IMPORT_OK = True
except (ImportError, Exception):
    IMPORT_OK = False

pytestmark = pytest.mark.skipif(not IMPORT_OK, reason="connectors not implemented yet")


def test_poll_gmail():
    """poll_gmail with a matching email calls publish_fn once."""
    pytest.skip("not implemented")


def test_poll_gmail_no_match():
    """poll_gmail with no matching emails calls publish_fn zero times."""
    pytest.skip("not implemented")


def test_poll_calendar():
    """poll_calendar with one delivery calendar event calls publish_fn once."""
    pytest.skip("not implemented")


def test_poll_calendar_no_match():
    """poll_calendar with a non-delivery event calls publish_fn zero times."""
    pytest.skip("not implemented")
