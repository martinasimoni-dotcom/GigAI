"""
Thread-safe in-memory store for decisions.
Supports full-text search, filtering, and contradiction detection.
"""
import threading
from datetime import datetime
from typing import Optional

from src.decisions.models import Decision


class DecisionStore:
    def __init__(self) -> None:
        self._items: list[Decision] = []
        self._lock = threading.Lock()

    def add(self, decision: Decision) -> None:
        with self._lock:
            self._items.append(decision)

    def get(self, decision_id: str) -> Optional[Decision]:
        with self._lock:
            return next((d for d in self._items if d.decision_id == decision_id), None)

    def list_decisions(
        self,
        project_id: str | None = None,
        decided_by: str | None = None,
        source: str | None = None,
        search: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        tag: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Decision], int]:
        with self._lock:
            results = list(self._items)

        if project_id:
            results = [d for d in results if d.project_id == project_id]
        if decided_by:
            q = decided_by.lower()
            results = [d for d in results if q in d.decided_by.lower()]
        if source:
            results = [d for d in results if d.source == source]
        if tag:
            t = tag.lower()
            results = [d for d in results if any(t in tg.lower() for tg in d.tags)]
        if date_from:
            dt = datetime.fromisoformat(date_from)
            results = [d for d in results if d.decided_at >= dt]
        if date_to:
            dt = datetime.fromisoformat(date_to)
            results = [d for d in results if d.decided_at <= dt]
        if search:
            q = search.lower()
            results = [
                d for d in results
                if q in d.title.lower()
                or q in d.description.lower()
                or q in d.decided_by.lower()
                or q in d.context.lower()
                or any(q in tg.lower() for tg in d.tags)
            ]

        # Sort by decided_at descending (newest first)
        results.sort(key=lambda d: -d.decided_at.timestamp())
        total = len(results)
        return results[offset:offset + limit], total

    def find_contradictions(self, new_decision: Decision) -> list[dict]:
        """
        Find existing decisions that may contradict a new decision.
        Uses keyword overlap and same-project matching.
        """
        contradictions = []
        new_words = set(new_decision.title.lower().split() + new_decision.description.lower().split())
        # Remove common words
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "to", "for", "of", "and", "in", "on", "at", "by", "with"}
        new_words -= stop_words

        with self._lock:
            candidates = [d for d in self._items if d.decision_id != new_decision.decision_id]

        for existing in candidates:
            # Must be same project or one is company-wide
            if existing.project_id and new_decision.project_id and existing.project_id != new_decision.project_id:
                continue

            existing_words = set(existing.title.lower().split() + existing.description.lower().split()) - stop_words
            overlap = new_words & existing_words
            overlap_ratio = len(overlap) / max(len(new_words), 1)

            if overlap_ratio > 0.3:
                contradictions.append({
                    "existing_decision": existing.decision_id,
                    "existing_title": existing.title,
                    "existing_decided_by": existing.decided_by,
                    "existing_decided_at": existing.decided_at.isoformat(),
                    "overlap_score": round(overlap_ratio, 2),
                    "common_terms": sorted(overlap)[:10],
                    "warning": f"Decision '{existing.title}' by {existing.decided_by} may conflict with this new decision.",
                })

        contradictions.sort(key=lambda c: -c["overlap_score"])
        return contradictions[:5]

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._items)


decision_store = DecisionStore()
