"""Tests for inbox Pydantic models."""
import pytest
from pydantic import ValidationError
from src.inbox.models import InboxItem, ActionItem


def test_inbox_item_defaults():
    item = InboxItem(source="gmail", comm_type="FYI", summary="Test", raw_text="Test body", sender="John")
    assert item.item_id  # auto-generated UUID
    assert item.is_read is False
    assert item.urgency == 3
    assert item.action_items == []


def test_summary_validator_rejects_empty():
    with pytest.raises(ValidationError):
        InboxItem(source="gmail", comm_type="FYI", summary="   ", raw_text="body", sender="John")


def test_action_item_priority_default():
    ai = ActionItem(assignee="Mike", description="Get quote")
    assert ai.priority == "medium"


def test_urgency_bounds():
    with pytest.raises(ValidationError):
        InboxItem(source="gmail", comm_type="FYI", summary="Test", raw_text="body", sender="John", urgency=0)
    with pytest.raises(ValidationError):
        InboxItem(source="gmail", comm_type="FYI", summary="Test", raw_text="body", sender="John", urgency=6)
