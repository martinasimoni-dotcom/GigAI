"""
Signal generator for domain processing — DOM-05.

generate_signals(event, policy_result, time_result, config) -> list[Signal]

Maps triggered policy rules and time conflicts to typed Signal objects.
Only generates signals from config.allowed_signals.
No LLM calls. No config.settings import.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.shared.models.config import EventTypeConfig
from src.shared.models.proposals import Signal
from src.system.domain_processing.policy_engine import PolicyResult
from src.system.domain_processing.time_analysis import TimeAnalysisResult

if TYPE_CHECKING:
    from src.system.context.enrichment import EnrichedEvent

logger = logging.getLogger(__name__)

# Rule → signal type mapping table
_RULE_SIGNAL_MAP: dict[str, str] = {
    "RULE-004": "drawing_markup_required",
    "RULE-005": "material_order_required",
    "RULE-006": "material_order_required",
    "RULE-007": "material_order_required",
    "RULE-008": "material_order_required",
    "RULE-011": "drawing_markup_required",
    "RULE-014": "drawing_markup_required",
    "RULE-015": "material_order_required",
    "RULE-017": "material_order_required",
}


def generate_signals(
    event: "EnrichedEvent",
    policy_result: PolicyResult,
    time_result: TimeAnalysisResult,
    config: EventTypeConfig,
) -> list[Signal]:
    """
    Generate typed signals from policy and time analysis results.

    Only emits signal types present in config.allowed_signals.
    Deduplicates by signal_type — one Signal per type.

    Args:
        event: EnrichedEvent used for logging (event_id).
        policy_result: Triggered rules from policy engine.
        time_result: Time analysis result with conflict detection.
        config: EventTypeConfig carrying allowed_signals list.

    Returns:
        List of Signal objects, filtered to allowed_signals, deduplicated by signal_type.
    """
    allowed: set[str] = set(config.allowed_signals)
    candidate_types: set[str] = set()

    # Map triggered rules to signal types
    for rule_id in policy_result.triggered_rules:
        signal_type = _RULE_SIGNAL_MAP.get(rule_id)
        if signal_type:
            candidate_types.add(signal_type)

    # Time conflict → schedule_update_needed
    if time_result.has_conflict:
        candidate_types.add("schedule_update_needed")

    # Filter to allowed signals only
    final_types = candidate_types & allowed

    signals: list[Signal] = []
    for signal_type in sorted(final_types):  # sorted for deterministic output
        payload: dict = {}

        if signal_type == "material_order_required":
            payload = {
                "triggered_by": [
                    r for r in policy_result.triggered_rules
                    if _RULE_SIGNAL_MAP.get(r) == signal_type
                ],
                "lead_time_days": time_result.lead_time_days,
            }
        elif signal_type == "schedule_update_needed":
            payload = {
                "conflict_details": time_result.conflict_details,
                "lead_time_days": time_result.lead_time_days,
                "conflicts": time_result.schedule_conflicts,
            }
        elif signal_type == "drawing_markup_required":
            payload = {
                "triggered_by": [
                    r for r in policy_result.triggered_rules
                    if _RULE_SIGNAL_MAP.get(r) == signal_type
                ],
            }

        signals.append(Signal(
            signal_type=signal_type,
            priority=2 if policy_result.escalate else 1,
            payload=payload,
        ))
        logger.info({
            "event": "signal_generated",
            "signal_type": signal_type,
            "event_id": event.event.event_id,
        })

    return signals
