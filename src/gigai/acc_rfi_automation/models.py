from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class NormalizedRfi:
    id: str
    subject: str
    question: str
    status: str
    due_date: str | None
    assigned_to: list[str] = field(default_factory=list)
    created_by: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)

    @property
    def normalized_status(self) -> str:
        return self.status.strip().lower()

