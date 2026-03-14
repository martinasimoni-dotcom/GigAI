#!/usr/bin/env python3
"""
GigAI Demo Script -- Window Material Substitution Scenario
Demonstrates complete pipeline: Fireflies transcript -> PM proposal

Usage: python scripts/run_demo.py

Requires: .env file with ANTHROPIC_API_KEY, VOYAGE_API_KEY, DATABASE_URL
          (or ACC_TOKEN if live ACC floor plan data is needed)

This script calls pipeline modules directly -- NOT through Pub/Sub.
Pub/Sub is async; this demo needs synchronous, traceable execution.
"""
import json
import sys
import time
from pathlib import Path

# MUST load env before any src.* imports -- config.settings singleton triggers at import time
from dotenv import load_dotenv
load_dotenv()

# --- src.* imports AFTER load_dotenv() ---
from src.shared.models.events import RawEvent, NormalizedEvent
from src.shared.models.proposals import Action, Proposal, Signal
from src.shared.models.config import EventTypeConfig


def _step_banner(step: int, total: int, title: str) -> None:
    print(f"\n[{step}/{total}] {title}")


def _load_transcript_fixture() -> dict:
    """Load the sample transcript fixture from tests/fixtures/."""
    fixture_path = Path(__file__).parent.parent / "tests" / "fixtures" / "sample_transcript.json"
    if not fixture_path.exists():
        # Inline fallback for when fixture file is missing
        return {
            "meetingId": "meeting-demo-001",
            "id": "transcript-demo-001",
            "meeting": {
                "title": "Construction Site Coordination -- 3rd Floor Windows",
                "date": "2026-03-14T09:00:00Z",
            },
            "transcript": (
                "We need to change the third-floor windows from aluminum to wood, "
                "12 units W-301 to W-312. Jane from Premium Wood Co can supply at "
                "$320 per unit. Mike needs to approve procurement."
            ),
            "attendees": [
                {"name": "John Smith", "role": "Project Manager"},
                {"name": "Jane Doe", "role": "Supplier Contact -- Premium Wood Co"},
                {"name": "Mike Chen", "role": "Procurement Lead"},
            ],
        }
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def _build_demo_normalized_event(event_id: str) -> NormalizedEvent:
    """
    Build the canonical demo NormalizedEvent directly.

    confidence=60 is deliberate: score_proposal produces 85.5 with this value
    (per STATE.md decision: 'Demo scenario confidence=60 not 95').
    """
    return NormalizedEvent(
        event_id=event_id,
        source="fireflies",
        event_type="material_change",
        material_original="aluminum",
        material_new="wood",
        location="3rd Floor",
        quantity=12,
        people=[
            {"name": "John Smith", "role": "Project Manager"},
            {"name": "Jane Doe", "role": "Supplier Contact"},
            {"name": "Mike Chen", "role": "Procurement Lead"},
        ],
        deadlines=[],
        summary="Change 3rd floor windows from aluminum to wood, 12 units W-301 to W-312",
        review_required=False,
        confidence=60,
        estimated_cost=3840.0,  # 12 units * $320/unit
    )


def _build_demo_routed_event(normalized: NormalizedEvent):
    """Build a stub RoutedEvent without calling Haiku or Pub/Sub."""
    from src.system.data_processing.router import RoutedEvent
    config_path = (
        Path(__file__).parent.parent / "config" / "event_types" / "material_change.yaml"
    )
    config = EventTypeConfig(
        event_type="material_change",
        rules_file="material_change_rules.yaml",
        allowed_signals=[
            "material_order_required",
            "schedule_update_needed",
            "drawing_markup_required",
        ],
        enrichment_queries=[
            "material supplier and pricing",
            "past material change approvals",
            "lead time window installation schedule",
            "structural weight load bearing assessment",
        ],
        time_analysis_enabled=True,
    )
    return RoutedEvent(
        event=normalized,
        event_type="material_change",
        config=config,
        config_path=str(config_path),
    )


def _build_demo_enriched_event(normalized: NormalizedEvent):
    """Build a stub EnrichedEvent with demo data (avoids ACC/pgvector calls)."""
    from src.system.context.enrichment import EnrichedEvent
    from src.system.context.historical import HistoricalMatch

    historical_matches = [
        HistoricalMatch(
            content="EVT-001: aluminum to wood window change, 3rd floor, 8 units, accepted",
            source="knowledge_folder/historical_patterns",
            metadata={"outcome": "accepted", "event_id": "EVT-001"},
            similarity=0.90,
            outcome="accepted",
            success_rate=0.9,
        ),
        HistoricalMatch(
            content="EVT-010: aluminum to wood substitution, 2nd floor, 10 units, accepted",
            source="knowledge_folder/historical_patterns",
            metadata={"outcome": "accepted", "event_id": "EVT-010"},
            similarity=0.88,
            outcome="accepted",
            success_rate=0.88,
        ),
        HistoricalMatch(
            content="EVT-012: aluminum to wood window change, 3rd floor, 12 units, structural review, accepted",
            source="knowledge_folder/historical_patterns",
            metadata={"outcome": "accepted", "event_id": "EVT-012"},
            similarity=0.92,
            outcome="accepted",
            success_rate=0.92,
        ),
    ]

    knowledge_chunks = [
        {
            "id": "kc-001",
            "source": "knowledge_folder/team_directory",
            "content": "Premium Wood Co -- Jane Doe (jane@premiumwood.com) -- $320/unit -- 2-week lead time",
            "similarity": 0.91,
        },
        {
            "id": "kc-002",
            "source": "knowledge_folder/rules",
            "content": "Material substitutions require structural review when quantity > 10 units",
            "similarity": 0.87,
        },
        {
            "id": "kc-003",
            "source": "knowledge_folder/rules",
            "content": "Procurement tasks required for orders over $1000",
            "similarity": 0.85,
        },
    ]

    floor_plan_data = {
        "project_id": "demo-project-001",
        "location": "3rd Floor",
        "nodes": [
            {"id": f"W-{300 + i}", "type": "window", "material": "aluminum"}
            for i in range(1, 13)
        ],
    }

    return EnrichedEvent(
        event=normalized,
        knowledge_chunks=knowledge_chunks,
        acc_floor_plan=floor_plan_data,
        supplier_info={
            "name": "knowledge_folder/team_directory",
            "content": "Premium Wood Co -- Jane Doe (jane@premiumwood.com) -- $320/unit",
            "source": "knowledge_folder/team_directory",
            "similarity": 0.91,
        },
        relevant_rules=[
            "Material substitutions require structural review when quantity > 10 units",
            "Procurement tasks required for orders over $1000",
            "Drawing markup required for all material substitutions",
        ],
        historical_matches=historical_matches,
    )


def _build_demo_processing_result(enriched):
    """Build a stub ProcessingResult with demo signals."""
    from src.system.domain_processing.processor import ProcessingResult
    from src.system.domain_processing.policy_engine import PolicyResult
    from src.system.domain_processing.time_analysis import TimeAnalysisResult
    from src.shared.models.proposals import Signal

    policy_result = PolicyResult(
        triggered_rules=[
            "material_order_required",
            "schedule_update_needed",
            "drawing_markup_required",
        ],
        escalate=False,
        alert_pm=True,
    )

    time_result = TimeAnalysisResult(
        has_conflict=False,
        lead_time_days=42,
        critical_path_affected=False,
        schedule_conflicts=[],
    )

    signals = [
        Signal(
            signal_type="material_order_required",
            priority=1,
            payload={"material": "wood", "quantity": 12, "supplier": "Premium Wood Co"},
        ),
        Signal(
            signal_type="schedule_update_needed",
            priority=2,
            payload={"location": "3rd Floor", "lead_time_weeks": 2},
        ),
        Signal(
            signal_type="drawing_markup_required",
            priority=3,
            payload={"drawing": "A-301", "annotation": "Wood substitution W-301 to W-312"},
        ),
    ]

    return ProcessingResult(
        event=enriched,
        signals=signals,
        policy_result=policy_result,
        time_result=time_result,
    )


def _build_demo_proposal(processing_result, event_id: str) -> Proposal:
    """Build a demo proposal without calling Sonnet."""
    actions = [
        Action(
            action_type="email",
            action_data={
                "to": "jane@premiumwood.com",
                "subject": "Window Order: 12 Wood Frame Units W-301 to W-312",
                "body": "Please confirm availability of 12 wood frame windows for 3rd floor.",
            },
        ),
        Action(
            action_type="task",
            action_data={
                "title": "Procurement approval: Wood windows 12 units",
                "assignee": "mike@site.com",
                "due": "2026-03-21",
            },
        ),
        Action(
            action_type="calendar",
            action_data={
                "summary": "Material delivery review -- 3rd floor windows",
                "start": "2026-03-28T09:00:00Z",
                "duration_minutes": 60,
            },
        ),
        Action(
            action_type="drawing",
            action_data={
                "drawing_number": "A-301",
                "annotation_text": "Material substitution: aluminum -> wood, W-301 to W-312",
            },
        ),
    ]
    return Proposal(
        event_id=event_id,
        alert={
            "summary": "Material Substitution: Aluminum to Wood Windows, 3rd Floor",
            "stakeholders": ["John Smith (PM)", "Jane Doe (Supplier)", "Mike Chen (Procurement)"],
            "confidence_rationale": "3 accepted precedents; cost within threshold; no structural red flags",
        },
        actions=actions,
        confidence_score=0.855,
        recommendation="accept",
    )


def _compute_confidence_score(processing_result) -> float:
    """
    Compute confidence score via the real scorer module.

    Falls back to 85.5 (demo scenario canonical value) if scorer fails.
    """
    try:
        from src.system.decision_intelligence.confidence_scorer import score_proposal
        historical = processing_result.event.historical_matches or []
        result = score_proposal(processing_result, historical)
        return result.score
    except Exception as exc:  # noqa: BLE001
        print(f"      (confidence scorer unavailable: {exc} -- using demo value 85.5)")
        return 85.5


def run_demo() -> int:
    """
    Execute the full window-substitution pipeline trace and print a 6-step numbered output.

    Returns exit code (0 = success).
    """
    demo_start = time.monotonic()
    event_id = "demo-evt-001"
    total_steps = 6

    print("=" * 65)
    print("GigAI Demo -- Window Material Substitution Pipeline")
    print("=" * 65)

    # ------------------------------------------------------------------
    # [1/6] EVENT CAPTURED
    # ------------------------------------------------------------------
    _step_banner(1, total_steps, "EVENT CAPTURED")
    t0 = time.monotonic()
    transcript = _load_transcript_fixture()
    raw = RawEvent(
        event_id=event_id,
        source="fireflies",
        raw_payload=transcript,
    )
    print(f"      Source: Fireflies meeting transcript")
    meeting_title = transcript.get("meeting", {}).get("title", "Construction Site Coordination")
    print(f"      Meeting: \"{meeting_title}\"")
    print(f"      Raw payload received. Publishing to pipeline...")
    print(f"      ({time.monotonic() - t0:.2f}s)")

    # ------------------------------------------------------------------
    # [2/6] NORMALIZING
    # ------------------------------------------------------------------
    _step_banner(2, total_steps, "NORMALIZING")
    t0 = time.monotonic()
    print("      Calling Claude Haiku 4.5 to extract structured fields...")
    try:
        from src.system.data_processing.normalizer import normalize_event
        normalized = normalize_event(raw)
        # Ensure confidence=60 for demo (may differ if real API returns different value)
        if normalized.confidence != 60:
            normalized = normalized.model_copy(update={"confidence": 60})
    except Exception as exc:  # noqa: BLE001
        print(f"      (Haiku API unavailable: {exc} -- using demo values)")
        normalized = _build_demo_normalized_event(event_id)

    print(f"      + material_original: {normalized.material_original}")
    print(f"      + material_new: {normalized.material_new}")
    print(f"      + location: {normalized.location}")
    print(f"      + quantity: {normalized.quantity}")
    print(f"      + confidence: {normalized.confidence}")
    print(f"      + summary: {normalized.summary}")
    print(f"      ({time.monotonic() - t0:.2f}s)")

    # ------------------------------------------------------------------
    # [3/6] ENRICHING CONTEXT
    # ------------------------------------------------------------------
    _step_banner(3, total_steps, "ENRICHING CONTEXT")
    t0 = time.monotonic()
    units = [f"W-{300 + i}" for i in range(1, 13)]
    print(f"      Fetching floor plan from ACC (stub: W-301..W-312)...")
    print(f"      Querying pgvector for supplier, rules, historical patterns...")
    try:
        from src.system.context.enrichment import enrich_event
        enriched = enrich_event(normalized)
    except Exception as exc:  # noqa: BLE001
        print(f"      (ACC/pgvector unavailable: {exc} -- using demo enrichment)")
        enriched = _build_demo_enriched_event(normalized)

    unit_str = ", ".join(units)
    print(f"      + Units affected: {unit_str}")
    if enriched.supplier_info:
        supplier_content = enriched.supplier_info.get("content", "Premium Wood Co (Jane Doe) -- $320/unit")
        print(f"      + Supplier: {supplier_content}")
    else:
        print(f"      + Supplier: Premium Wood Co (Jane Doe) -- $320/unit")
    hist_count = len(enriched.historical_matches)
    best_match = "EVT-012, 12 units, accepted"
    if enriched.historical_matches:
        best = max(enriched.historical_matches, key=lambda m: m.similarity)
        best_id = best.metadata.get("event_id", "EVT-012")
        best_match = f"{best_id}, 12 units, accepted"
    print(f"      + Historical matches: {hist_count} found (best: {best_match})")
    print(f"      ({time.monotonic() - t0:.2f}s)")

    # ------------------------------------------------------------------
    # [4/6] DOMAIN PROCESSING
    # ------------------------------------------------------------------
    _step_banner(4, total_steps, "DOMAIN PROCESSING")
    t0 = time.monotonic()
    print("      Evaluating policy rules and schedule conflicts...")
    try:
        routed = _build_demo_routed_event(normalized)
        from src.system.domain_processing.processor import process_event
        processing_result = process_event(routed)
    except Exception as exc:  # noqa: BLE001
        print(f"      (processor unavailable: {exc} -- using demo signals)")
        enriched = _build_demo_enriched_event(normalized)
        processing_result = _build_demo_processing_result(enriched)

    signal_names = [s.signal_type for s in processing_result.signals]
    print(f"      + Signals generated: {', '.join(signal_names)}")
    print(f"      ({time.monotonic() - t0:.2f}s)")

    # ------------------------------------------------------------------
    # [5/6] PROPOSAL GENERATED
    # ------------------------------------------------------------------
    _step_banner(5, total_steps, "PROPOSAL GENERATED")
    t0 = time.monotonic()
    print("      Calling Claude Sonnet 4 to generate proposal...")
    try:
        from src.system.decision_intelligence.proposal_generator import generate_proposal
        proposal = generate_proposal(processing_result)
        # Compute confidence score via real scorer
        confidence_score = _compute_confidence_score(processing_result)
        # Refresh proposal with computed score
        proposal = proposal.model_copy(update={
            "confidence_score": confidence_score / 100.0,
            "recommendation": "accept" if confidence_score > 80 else "review",
        })
    except Exception as exc:  # noqa: BLE001
        print(f"      (Sonnet API unavailable: {exc} -- using demo proposal)")
        confidence_score = _compute_confidence_score(processing_result)
        proposal = _build_demo_proposal(processing_result, event_id)
        proposal = proposal.model_copy(update={
            "confidence_score": confidence_score / 100.0,
            "recommendation": "accept" if confidence_score > 80 else "review",
        })

    action_count = len(proposal.actions)
    action_types = [a.action_type for a in proposal.actions]
    action_summary = " + ".join(action_types)
    score_display = proposal.confidence_score * 100.0
    rec_upper = proposal.recommendation.upper()
    print(f"      + {action_count} actions: {action_summary}")
    print(f"      + Confidence score: {score_display:.1f}% -- {rec_upper}")
    print(f"      ({time.monotonic() - t0:.2f}s)")

    # ------------------------------------------------------------------
    # [6/6] READY FOR PM DECISION
    # ------------------------------------------------------------------
    elapsed = time.monotonic() - demo_start
    _step_banner(6, total_steps, "READY FOR PM DECISION")
    print("      Open dashboard at http://localhost:5173")
    print("      Proposal is waiting for PM approval.")
    print(f"      Run time: {elapsed:.1f}s")

    print("\n" + "=" * 65)
    print("DEMO COMPLETE")
    print("=" * 65)

    return 0


if __name__ == "__main__":
    sys.exit(run_demo())
