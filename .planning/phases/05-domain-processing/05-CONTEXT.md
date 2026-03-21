# Phase 5: Domain Processing — Context

**Gathered:** 2026-03-13
**Status:** Ready for planning
**Source:** PRD Express Path (CLAUDE_PLAN.md)

<domain>
## Phase Boundary

Phase 5 delivers the three steps of the SYSTEM domain processing pipeline — analyzing enriched events for time impacts and policy compliance, then producing a typed set of signals:

1. **material_change.yaml full config** (DOM-01): Completes the stub from Phase 3 — adds full rules, signal types, and enrichment queries for the demo scenario.
2. **Event type config stubs** (DOM-02): `schedule_update.yaml` and `rfi_request.yaml` — load without errors.
3. **Time Analysis** (DOM-03): `time_analysis.py` — dateutil-based temporal reasoning, cross-references an ACC schedule for conflicts (lead time overlap detection).
4. **Policy Engine** (DOM-04): `policy_engine.py` — loads YAML rules from `rules_file` in EventTypeConfig, evaluates conditions, returns triggered rules.
5. **Signal Generator** (DOM-05): `signal_generator.py` — outputs typed signals from the allowed set in EventTypeConfig.
6. **Domain Processor Orchestrator** (DOM-06): `processor.py` — runs time analysis → policy engine → signal generator with loaded EventTypeConfig.
7. **Routing integration** (DOM-07): Already done in Phase 3 — just needs validation that routing prompt and configs are wired to domain processor.

Also delivers:
- `src/system/domain_processing/__init__.py`
- Unit tests for all five modules
</domain>

<decisions>
## Implementation Decisions

### material_change.yaml full config (DOM-01)
- File: `config/event_types/material_change.yaml`
- Already has working stub from Phase 3 with: event_type, rules_file, allowed_signals (3), enrichment_queries (2), time_analysis_enabled: true
- Phase 5 enriches it further but it already validates against EventTypeConfig — no breaking changes
- Add more enrichment_queries to support demo: "lead time window installation schedule", "structural weight load bearing"
- Keep existing structure, just expand content

### Event Type Config Stubs (DOM-02)
- `config/event_types/schedule_update.yaml` — already exists from Phase 3
- `config/event_types/rfi_request.yaml` — already exists from Phase 3
- Must validate against EventTypeConfig schema — check if they already do
- Phase 5 should verify these load cleanly and potentially improve them

### Time Analysis Module (DOM-03)
- File: `src/system/domain_processing/time_analysis.py`
- Function: `analyze_time(event: EnrichedEvent, schedule: list[dict] | None = None) -> TimeAnalysisResult`
- TimeAnalysisResult: Pydantic v2 model with `has_conflict: bool`, `conflict_details: str | None`, `lead_time_days: int | None`, `critical_path_affected: bool`, `schedule_conflicts: list[dict]`
- Uses `python-dateutil` for date parsing from event deadlines
- Cross-references `schedule` list (list of dicts with `date`, `activity`, `location`) for overlap
- Lead time logic: if quantity > 10 → 42 days (6 weeks, per RULE-005); else → 21 days
- Conflict detection: if any schedule entry falls within lead_time_days window
- Schedule comes from ACC (stub for now — same pattern as enrichment ACC stub)
- Does NOT call any LLM

### Policy Engine (DOM-04)
- File: `src/system/domain_processing/policy_engine.py`
- Function: `evaluate_policies(event: EnrichedEvent, config: EventTypeConfig) -> PolicyResult`
- PolicyResult: Pydantic v2 model with `triggered_rules: list[str]`, `rule_details: list[dict]`, `escalate: bool`, `alert_pm: bool`
- Loads rules YAML from `config.rules_file` (path relative to project root)
- Each rule in YAML has: rule_id, description, condition, action, stakeholders, priority
- Evaluates each rule's condition against the event fields using simple Python logic (not eval())
- Conditions are string templates like "quantity > 10", "estimated_cost > 50000", "change_type == 'material'"
- Parses condition strings with safe evaluation (no exec/eval — use explicit comparisons)
- Returns list of triggered rule IDs and whether escalation is needed

### Signal Generator (DOM-05)
- File: `src/system/domain_processing/signal_generator.py`
- Function: `generate_signals(event: EnrichedEvent, policy_result: PolicyResult, time_result: TimeAnalysisResult, config: EventTypeConfig) -> list[Signal]`
- Signal model is in `src/shared/models/proposals.py` — check its fields before implementing
- Only generates signals from `config.allowed_signals` list
- Maps triggered rules → signals using a lookup table (e.g., quantity > 5 → material_order_required)
- Maps time conflict → schedule_update_needed if `time_result.has_conflict`
- Maps any structural rule → drawing_markup_required
- Returns typed Signal objects (not strings)

### Domain Processor Orchestrator (DOM-06)
- File: `src/system/domain_processing/processor.py`
- Function: `process_event(routed_event: RoutedEvent) -> ProcessingResult`
- ProcessingResult: Pydantic v2 model with `event: EnrichedEvent`, `signals: list[Signal]`, `policy_result: PolicyResult`, `time_result: TimeAnalysisResult`
- Imports EnrichedEvent from `src/system/context/enrichment.py`
- Calls `enrich_event()` then runs the three sub-modules in sequence
- Uses `routed_event.config` (already loaded EventTypeConfig) — no redundant YAML loading
- Package init: `src/system/domain_processing/__init__.py`

### DOM-07 Routing Integration
- Already implemented in Phase 3 (router.py calls Haiku, loads YAML config)
- Phase 5 only needs to verify: router output (RoutedEvent.config) is consumed by processor.py
- No new code for DOM-07, just wiring in processor.py

### Claude's Discretion
- Exact condition evaluation strategy for policy engine (simple field comparison vs. more sophisticated)
- Whether TimeAnalysisResult and PolicyResult live inline or in shared models
- Signal mapping table location (inline dict in signal_generator.py)
- Logging strategy for triggered rules and signals

</decisions>

<specifics>
## Specific Requirements

- Demo scenario signals: `material_order_required`, `schedule_update_needed`, `drawing_markup_required`
- Policy engine must evaluate ≥5 rules from demo_project.yaml for the demo scenario
- Time analysis: quantity=12 > 10 → 42-day lead time → likely conflicts with installation events
- EventTypeConfig already defined in `src/shared/models/config.py` with: event_type, rules_file, allowed_signals, enrichment_queries, time_analysis_enabled
- Signal model already in `src/shared/models/proposals.py` — read it before implementing
- RoutedEvent already in `src/system/data_processing/router.py` — read it before implementing
- EnrichedEvent already in `src/system/context/enrichment.py` — use as input to processor
- All secrets in .env, no OpenAI, no spaCy, Pydantic v2
- Rules YAML file: `knowledge_folder/rules/demo_project.yaml` — 18 rules already written
- Tests must mock file reads and not require live DB or ACC API

</specifics>

<deferred>
## Deferred Ideas

- Async domain processing — Phase 7
- LLM-based condition evaluation for complex rules — v2
- Multi-event batch processing — v2
- Real ACC schedule integration — Phase 7+
</deferred>

---

*Phase: 05-domain-processing*
*Context gathered: 2026-03-13 via PRD Express Path*
