"""
Thread-safe in-memory store for RFIs.
"""
import threading
from typing import Optional

from src.rfi.models import RFI


class RFIStore:
    def __init__(self) -> None:
        self._items: list[RFI] = []
        self._lock = threading.Lock()

    def add(self, rfi: RFI) -> None:
        with self._lock:
            self._items.append(rfi)

    def get(self, rfi_id: str) -> Optional[RFI]:
        with self._lock:
            return next((r for r in self._items if r.rfi_id == rfi_id), None)

    def list_rfis(
        self,
        project_id: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        assignee: str | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[RFI], int]:
        with self._lock:
            results = list(self._items)

        if project_id:
            results = [r for r in results if r.project_id == project_id]
        if status:
            results = [r for r in results if r.status == status]
        if priority:
            results = [r for r in results if r.priority == priority]
        if assignee:
            a = assignee.lower()
            results = [r for r in results if r.assignee and a in r.assignee.lower()]
        if search:
            q = search.lower()
            results = [
                r for r in results
                if q in r.title.lower()
                or q in r.question.lower()
                or (r.category and q in r.category.lower())
            ]

        # Sort: open/drafted first, then by priority, then by creation date
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        status_order = {"open": 0, "drafted": 1, "reviewed": 2, "sent": 3, "responded": 4, "closed": 5}
        results.sort(key=lambda r: (
            status_order.get(r.status, 9),
            priority_order.get(r.priority, 9),
            -r.created_at.timestamp(),
        ))

        total = len(results)
        return results[offset:offset + limit], total

    def update(self, rfi_id: str, **kwargs) -> Optional[RFI]:
        with self._lock:
            for idx, rfi in enumerate(self._items):
                if rfi.rfi_id == rfi_id:
                    self._items[idx] = rfi.model_copy(update=kwargs)
                    return self._items[idx]
        return None

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._items)


rfi_store = RFIStore()
