"""
Time analysis for domain processing — DOM-03.

analyze_time(event: EnrichedEvent, schedule: list[dict] | None = None) -> TimeAnalysisResult

Calculates lead time based on quantity (RULE-005: >10 units = 42 days, else 21 days)
and detects schedule conflicts within the lead time window.
No LLM calls. No config.settings import.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from dateutil import parser as dateutil_parser
from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from src.system.context.enrichment import EnrichedEvent


class TimeAnalysisResult(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    has_conflict: bool = False
    conflict_details: str | None = None
    lead_time_days: int = 21
    critical_path_affected: bool = False
    schedule_conflicts: list[dict] = Field(default_factory=list)


def analyze_time(
    event: EnrichedEvent,
    schedule: list[dict] | None = None,
) -> TimeAnalysisResult:
    """
    Analyze temporal impact of a material change event.

    Args:
        event: EnrichedEvent with event.quantity used for lead time calculation.
        schedule: Optional list of schedule entries with 'date' and 'activity' keys.
                  Entries with unparseable dates are skipped silently.

    Returns:
        TimeAnalysisResult with lead_time_days, has_conflict, schedule_conflicts.
    """
    quantity = event.event.quantity or 0
    # RULE-005: window orders > 10 units require 6-week (42-day) lead time
    lead_time_days = 42 if quantity > 10 else 21

    today = datetime.now(timezone.utc).date()
    deadline = today + timedelta(days=lead_time_days)

    conflicts: list[dict] = []
    for entry in (schedule or []):
        raw_date = entry.get("date", "")
        try:
            parsed = dateutil_parser.parse(str(raw_date)).date()
        except (ValueError, OverflowError, TypeError):
            continue
        if today <= parsed <= deadline:
            conflicts.append({
                "date": str(parsed),
                "activity": entry.get("activity", "unknown"),
                "location": entry.get("location", ""),
            })

    has_conflict = len(conflicts) > 0
    conflict_details: str | None = None
    if has_conflict:
        conflict_details = (
            f"{len(conflicts)} schedule conflict(s) within "
            f"{lead_time_days}-day lead time window"
        )

    return TimeAnalysisResult(
        has_conflict=has_conflict,
        conflict_details=conflict_details,
        lead_time_days=lead_time_days,
        schedule_conflicts=conflicts,
    )
