"""
Domain processor orchestrator — DOM-06.

process_event(routed_event: RoutedEvent) -> ProcessingResult

Runs the domain processing pipeline in sequence:
  1. enrich_event (context enrichment — ACC floor plan + pgvector)
  2. analyze_time (temporal conflict detection against real ACC schedule)
  3. evaluate_policies (YAML rule evaluation)
  4. generate_signals (typed signal output)

Uses routed_event.config (EventTypeConfig already loaded by router.py).
DOM-07 satisfied: no redundant YAML loading here.
No LLM calls. No config.settings import.
"""
from __future__ import annotations

import logging
import os

from pydantic import BaseModel, ConfigDict, Field

from src.shared.models.proposals import Signal
from src.system.context.enrichment import EnrichedEvent, enrich_event
from src.system.data_processing.router import RoutedEvent
from src.system.domain_processing.policy_engine import PolicyResult, evaluate_policies
from src.system.domain_processing.signal_generator import generate_signals
from src.system.domain_processing.time_analysis import TimeAnalysisResult, analyze_time

logger = logging.getLogger(__name__)


class ProcessingResult(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    event: EnrichedEvent
    signals: list[Signal] = Field(default_factory=list)
    policy_result: PolicyResult
    time_result: TimeAnalysisResult


def _fetch_acc_schedule(project_id: str) -> list[dict]:
    """
    Fetch project schedule activities from ACC Schedule API.

    Returns an empty list (and logs a warning) if credentials are unavailable,
    so time analysis still runs — it just reports no schedule conflicts.
    This is the only place in the pipeline where missing ACC credentials
    degrade gracefully rather than raising, because schedule data is
    supplementary to policy evaluation (the primary decision driver).
    """
    from src.shared.clients.acc import get_schedule_activities
    try:
        activities = get_schedule_activities(project_id)
        logger.info(
            "ACC schedule fetched: project=%s activities=%d",
            project_id, len(activities),
        )
        return activities
    except RuntimeError as exc:
        logger.warning("ACC schedule unavailable (%s) — time analysis will run without schedule", exc)
        return []
    except Exception as exc:
        logger.warning("ACC schedule fetch failed (%s) — time analysis will run without schedule", exc)
        return []


def process_event(routed_event: RoutedEvent) -> ProcessingResult:
    """
    Run the full domain processing pipeline for a routed event.

    Args:
        routed_event: RoutedEvent from router.py with event and pre-loaded config.
                      DOM-07: config is consumed directly — no YAML reload.

    Returns:
        ProcessingResult with enriched event, signals, policy result, time result.

    Raises:
        RuntimeError if ACC credentials are not configured (propagated from enrich_event).
    """
    logger.info({
        "event": "domain_processing_start",
        "event_id": routed_event.event.event_id,
        "event_type": routed_event.event_type,
    })

    # Step 1: Context enrichment — ACC floor plan + pgvector (raises if creds absent)
    enriched = enrich_event(routed_event.event)

    # Step 2: Time analysis — fetch real ACC schedule, pass to analyze_time
    project_id = os.getenv("ACC_PROJECT_ID", "")
    acc_schedule = _fetch_acc_schedule(project_id) if project_id else []
    time_result = analyze_time(enriched, schedule=acc_schedule or None)

    # Step 3: Policy evaluation (DOM-04)
    policy_result = evaluate_policies(enriched, routed_event.config)

    # Step 4: Signal generation (DOM-05)
    signals = generate_signals(enriched, policy_result, time_result, routed_event.config)

    logger.info({
        "event": "domain_processing_complete",
        "event_id": routed_event.event.event_id,
        "triggered_rules": policy_result.triggered_rules,
        "signals": [s.signal_type for s in signals],
        "has_time_conflict": time_result.has_conflict,
    })

    return ProcessingResult(
        event=enriched,
        signals=signals,
        policy_result=policy_result,
        time_result=time_result,
    )
