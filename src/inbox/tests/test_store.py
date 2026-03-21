"""Tests for InboxStore."""
import pytest
from src.inbox.models import InboxItem
from src.inbox.store import InboxStore


@pytest.fixture
def store():
    s = InboxStore()
    yield s
    s.clear()


def _item(**kwargs):
    defaults = {"source": "gmail", "comm_type": "FYI", "summary": "Test", "raw_text": "body", "sender": "John"}
    defaults.update(kwargs)
    return InboxItem(**defaults)


def test_add_and_get(store):
    item = _item()
    store.add(item)
    assert store.get(item.item_id) is not None
    assert store.get(item.item_id).item_id == item.item_id


def test_list_filter_project(store):
    store.add(_item(project_id="PRJ-001"))
    store.add(_item(project_id="PRJ-002"))
    store.add(_item(project_id="PRJ-001"))
    results, total = store.list_items(project_id="PRJ-001")
    assert total == 2
    assert all(i.project_id == "PRJ-001" for i in results)


def test_list_filter_comm_type(store):
    store.add(_item(comm_type="question"))
    store.add(_item(comm_type="FYI"))
    store.add(_item(comm_type="question"))
    results, total = store.list_items(comm_type="question")
    assert total == 2


def test_list_filter_urgency(store):
    store.add(_item(urgency=2))
    store.add(_item(urgency=4))
    store.add(_item(urgency=5))
    results, total = store.list_items(min_urgency=4)
    assert total == 2
    assert all(i.urgency >= 4 for i in results)


def test_mark_read(store):
    item = _item()
    store.add(item)
    assert store.mark_read(item.item_id) is True
    assert store.get(item.item_id).is_read is True


def test_mark_read_not_found(store):
    assert store.mark_read("nonexistent") is False


def test_list_sorted_urgency(store):
    store.add(_item(urgency=1))
    store.add(_item(urgency=5))
    store.add(_item(urgency=3))
    results, _ = store.list_items()
    assert results[0].urgency == 5
    assert results[1].urgency == 3
    assert results[2].urgency == 1


def test_clear(store):
    store.add(_item())
    store.add(_item())
    store.clear()
    results, total = store.list_items()
    assert total == 0
