"""
Thread-safe in-memory store for inbox items.

Provides CRUD operations with multi-field filtering, urgency+recency sorting,
and a module-level singleton for use across the application.
"""
import threading
from typing import Optional

from src.inbox.models import InboxItem


class InboxStore:
    def __init__(self) -> None:
        self._items: list[InboxItem] = []
        self._lock = threading.Lock()

    def add(self, item: InboxItem) -> None:
        with self._lock:
            self._items.append(item)

    def get(self, item_id: str) -> Optional[InboxItem]:
        with self._lock:
            return next((i for i in self._items if i.item_id == item_id), None)

    def list_items(
        self,
        project_id: str | None = None,
        comm_type: str | None = None,
        min_urgency: int = 1,
        max_urgency: int = 5,
        unread_only: bool = False,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[InboxItem], int]:
        with self._lock:
            results = list(self._items)

        if project_id:
            results = [i for i in results if i.project_id == project_id]
        if comm_type:
            results = [i for i in results if i.comm_type == comm_type]
        results = [i for i in results if min_urgency <= i.urgency <= max_urgency]
        if unread_only:
            results = [i for i in results if not i.is_read]
        if search:
            q = search.lower()
            results = [
                i for i in results
                if q in i.summary.lower()
                or q in i.sender.lower()
                or (i.subject and q in i.subject.lower())
            ]

        # Sort by urgency desc, then received_at desc
        results.sort(key=lambda x: (-x.urgency, -x.received_at.timestamp()))
        total = len(results)
        return results[offset:offset + limit], total

    def mark_read(self, item_id: str) -> bool:
        with self._lock:
            for idx, item in enumerate(self._items):
                if item.item_id == item_id:
                    self._items[idx] = item.model_copy(update={"is_read": True})
                    return True
        return False

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._items)


inbox_store = InboxStore()
