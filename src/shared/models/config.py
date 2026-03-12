"""
Pydantic v2 model for event type configuration.
FOUND-08
"""
from pydantic import BaseModel, ConfigDict, Field


class EventTypeConfig(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    event_type: str
    rules_file: str
    allowed_signals: list[str] = Field(default_factory=list)
    enrichment_queries: list[str] = Field(default_factory=list)
    time_analysis_enabled: bool = False
