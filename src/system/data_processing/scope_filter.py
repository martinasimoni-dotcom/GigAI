"""
Scope filter module — PROC-03.

filter_event(event: NormalizedEvent, project_scope: dict) -> FilterResult

Validates the normalized event against the project scope dict.
Rejects events with locations not in project_scope["locations"].
Escalates events with estimated_cost > $50,000 immediately.
Never raises exceptions — always returns a FilterResult.
"""
import logging

from pydantic import BaseModel, ConfigDict

from src.shared.models.events import NormalizedEvent

logger = logging.getLogger(__name__)

def _cost_escalation_threshold() -> float:
    from config.settings import settings
    return settings.cost_escalation_threshold


class FilterResult(BaseModel):
    """Result of scope filter evaluation."""
    model_config = ConfigDict(str_strip_whitespace=True)

    passed: bool
    reason: str
    escalate_immediately: bool = False
    alert_pm: bool = False


def filter_event(event: NormalizedEvent, project_scope: dict) -> FilterResult:
    """
    Validate a NormalizedEvent against the project scope.

    Args:
        event: The normalized event to validate.
        project_scope: Dict with keys:
            - "locations": list[str] — known in-scope location strings (case-insensitive)
            - "project_id": str — project identifier (for logging)

    Returns:
        FilterResult — never raises. Check result.passed to continue pipeline.
    """
    known_locations = [loc.lower() for loc in project_scope.get("locations", [])]
    event_location = (event.location or "").lower().strip()

    # --- Scope check ---
    # If no locations are configured, pass all events (no restriction)
    if known_locations:
        location_in_scope = event_location in known_locations
        if not location_in_scope:
            logger.warning({
                "event": "out_of_scope",
                "event_id": event.event_id,
                "location": event.location,
                "project_id": project_scope.get("project_id"),
            })
            return FilterResult(
                passed=False,
                reason=f"Location '{event.location}' is not in project scope.",
                escalate_immediately=False,
                alert_pm=True,
            )

    # --- Cost escalation check (only for in-scope events) ---
    escalate = False
    if event.estimated_cost is not None and event.estimated_cost > _cost_escalation_threshold():
        escalate = True
        logger.warning({
            "event": "cost_escalation",
            "event_id": event.event_id,
            "estimated_cost": event.estimated_cost,
            "threshold": _COST_ESCALATION_THRESHOLD,
        })

    return FilterResult(
        passed=True,
        reason="Event is within project scope.",
        escalate_immediately=escalate,
        alert_pm=False,
    )
