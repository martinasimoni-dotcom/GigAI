"""
Smart notification engine — urgency + relevance scoring and routing.

Scores each notification by:
1. Urgency (0-100): deadline proximity, financial impact, dependency analysis
2. Relevance per recipient: based on role, project assignments, and expertise

Critical notifications (urgency > 80) deliver immediately.
Lower-priority items are batched into configurable digests.
"""
import logging
import threading
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class NotificationItem:
    """A scored notification ready for routing."""
    __slots__ = (
        "notif_id", "title", "body", "source_type", "source_id",
        "project_id", "project_name", "urgency_score", "relevance_scores",
        "tier", "created_at", "read", "delivered",
    )

    def __init__(self, **kwargs):
        self.notif_id = kwargs.get("notif_id", "")
        self.title = kwargs.get("title", "")
        self.body = kwargs.get("body", "")
        self.source_type = kwargs.get("source_type", "system")
        self.source_id = kwargs.get("source_id")
        self.project_id = kwargs.get("project_id")
        self.project_name = kwargs.get("project_name")
        self.urgency_score = kwargs.get("urgency_score", 50)
        self.relevance_scores = kwargs.get("relevance_scores", {})
        self.tier = kwargs.get("tier", "normal")
        self.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
        self.read = kwargs.get("read", False)
        self.delivered = kwargs.get("delivered", False)

    def to_dict(self) -> dict:
        return {
            "notif_id": self.notif_id,
            "title": self.title,
            "body": self.body,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "project_id": self.project_id,
            "project_name": self.project_name,
            "urgency_score": self.urgency_score,
            "relevance_scores": self.relevance_scores,
            "tier": self.tier,
            "created_at": self.created_at.isoformat(),
            "read": self.read,
            "delivered": self.delivered,
        }


class NotificationCenter:
    """Central notification store with scoring and routing."""

    def __init__(self) -> None:
        self._items: list[NotificationItem] = []
        self._lock = threading.Lock()
        self._config = {
            "immediate_threshold": 80,
            "digest_frequency": "daily",
            "channels": ["dashboard"],
        }

    def add(self, item: NotificationItem) -> None:
        # Score and tier the notification
        item.tier = self._determine_tier(item.urgency_score)
        with self._lock:
            self._items.append(item)

    def list_notifications(
        self,
        tier: str | None = None,
        unread_only: bool = False,
        project_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[NotificationItem], int]:
        with self._lock:
            results = list(self._items)

        if tier:
            results = [n for n in results if n.tier == tier]
        if unread_only:
            results = [n for n in results if not n.read]
        if project_id:
            results = [n for n in results if n.project_id == project_id]

        results.sort(key=lambda n: (-n.urgency_score, -n.created_at.timestamp()))
        total = len(results)
        return results[offset:offset + limit], total

    def mark_read(self, notif_id: str) -> bool:
        with self._lock:
            for n in self._items:
                if n.notif_id == notif_id:
                    n.read = True
                    return True
        return False

    def get_stats(self) -> dict:
        with self._lock:
            items = list(self._items)
        total = len(items)
        unread = sum(1 for n in items if not n.read)
        by_tier = {}
        by_source = {}
        for n in items:
            by_tier[n.tier] = by_tier.get(n.tier, 0) + 1
            by_source[n.source_type] = by_source.get(n.source_type, 0) + 1
        return {
            "total": total,
            "unread": unread,
            "by_tier": by_tier,
            "by_source": by_source,
        }

    def update_config(self, **kwargs) -> dict:
        self._config.update(kwargs)
        return self._config

    def get_config(self) -> dict:
        return dict(self._config)

    def _determine_tier(self, urgency: int) -> str:
        if urgency >= self._config["immediate_threshold"]:
            return "immediate"
        elif urgency >= 50:
            return "important"
        return "digest"

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


notification_center = NotificationCenter()


def score_urgency(
    item_type: str,
    urgency_hint: int = 3,
    has_deadline: bool = False,
    deadline_days: int = 999,
    financial_impact: float = 0,
    is_critical_path: bool = False,
    is_safety: bool = False,
) -> int:
    """
    Score notification urgency 0-100 using multiple factors.

    Factors:
    - Base urgency from source (1-5 mapped to 0-100)
    - Deadline proximity bonus
    - Financial impact bonus
    - Critical path bonus
    - Safety bonus
    """
    # Base score from urgency hint (1-5 -> 10-90)
    base = min(90, max(10, urgency_hint * 18))

    # Deadline proximity
    if has_deadline:
        if deadline_days <= 0:
            base += 20  # Overdue
        elif deadline_days <= 1:
            base += 15
        elif deadline_days <= 3:
            base += 10
        elif deadline_days <= 7:
            base += 5

    # Financial impact
    if financial_impact > 100_000:
        base += 15
    elif financial_impact > 50_000:
        base += 10
    elif financial_impact > 10_000:
        base += 5

    # Critical path
    if is_critical_path:
        base += 10

    # Safety
    if is_safety:
        base += 20

    return min(100, base)


def score_relevance(
    recipient_role: str,
    notification_type: str,
    recipient_projects: list[str],
    notification_project: str | None,
) -> int:
    """
    Score notification relevance (0-100) for a specific recipient.

    Based on role match, project assignment, and notification type.
    """
    score = 30  # Base relevance

    # Project assignment match
    if notification_project and notification_project in recipient_projects:
        score += 40

    # Role-type match
    role_relevance = {
        ("project manager", "escalation"): 30,
        ("project manager", "decision"): 25,
        ("project manager", "budget"): 25,
        ("superintendent", "safety"): 30,
        ("superintendent", "schedule"): 25,
        ("architect", "design"): 30,
        ("architect", "rfi"): 25,
        ("engineer", "structural"): 30,
        ("procurement", "material"): 30,
        ("procurement", "vendor"): 25,
    }

    role_lower = recipient_role.lower()
    for (role_match, type_match), bonus in role_relevance.items():
        if role_match in role_lower and type_match in notification_type.lower():
            score += bonus
            break

    return min(100, score)


def generate_notifications_from_inbox() -> int:
    """Generate notifications from recent inbox items. Returns count."""
    import uuid
    try:
        from src.inbox.store import inbox_store
        items, _ = inbox_store.list_items(limit=10000)

        existing_source_ids = {n.source_id for n in notification_center._items if n.source_id}
        count = 0

        for item in items:
            if item.item_id in existing_source_ids:
                continue

            urgency = score_urgency(
                item_type=item.comm_type,
                urgency_hint=item.urgency,
                is_safety="safety" in item.raw_text.lower(),
                is_critical_path=item.urgency >= 4,
            )

            notif = NotificationItem(
                notif_id=f"NOTIF-{uuid.uuid4().hex[:8].upper()}",
                title=item.summary,
                body=item.raw_text[:200],
                source_type=item.source,
                source_id=item.item_id,
                project_id=item.project_id,
                project_name=item.project_name,
                urgency_score=urgency,
            )
            notification_center.add(notif)
            count += 1

        return count
    except Exception:
        return 0
