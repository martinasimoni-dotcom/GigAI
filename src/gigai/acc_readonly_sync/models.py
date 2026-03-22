from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(slots=True)
class NormalizedLocation:
    x: float | None = None
    y: float | None = None
    z: float | None = None
    elementId: str | None = None
    viewId: str | None = None
    modelUrn: str | None = None
    sourceUrl: str | None = None

    def has_mapping_data(self) -> bool:
        return self.elementId is not None or any(value is not None for value in (self.x, self.y, self.z))


@dataclass(slots=True)
class NormalizedAccRecord:
    id: str
    type: str
    title: str
    description: str
    status: str
    createdBy: str | None
    assignedUser: str | None
    dueDate: str | None
    location: NormalizedLocation
    sourceUpdatedAt: str | None = None
    sourcePayload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SnapshotMetadata:
    generatedAt: str
    projectId: str
    itemsWritten: int
    ignoredWithoutLocation: int
    sources: list[str]
    newItems: int = 0
    updatedItems: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SnapshotPayload:
    metadata: SnapshotMetadata
    items: list[NormalizedAccRecord]

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "items": [item.to_dict() for item in self.items],
        }
