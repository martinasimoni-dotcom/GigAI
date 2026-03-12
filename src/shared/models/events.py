"""
Pydantic v2 models for raw and normalized pipeline events.
FOUND-06
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RawEvent(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    event_id: str
    source: Literal["fireflies", "acc", "gmail", "calendar"]
    raw_payload: dict
    received_at: datetime = Field(default_factory=datetime.utcnow)


class NormalizedEvent(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    event_id: str
    source: Literal["fireflies", "acc", "gmail", "calendar"]
    event_type: str
    material_original: Optional[str] = None
    material_new: Optional[str] = None
    location: Optional[str] = None
    quantity: Optional[int] = None
    people: list[dict] = Field(default_factory=list)   # [{name: str, role: str}]
    deadlines: list[datetime] = Field(default_factory=list)
    summary: str
    extracted_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("summary")
    @classmethod
    def summary_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("summary must not be empty")
        return v
