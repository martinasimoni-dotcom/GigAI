from gigai.models import AgentOutput, NormalizedEvent, RetrievedContext


def run_understanding_agents(
    event: NormalizedEvent,
    retrieved_context: list[RetrievedContext] | None = None,
) -> list[AgentOutput]:
    context = retrieved_context or []
    if event.type == "meeting.focus":
        return _run_meeting_understanding_agents(event, context)

    issue_summary = "Issue updated and requires assignment check"
    if event.payload.get("status") == "blocked":
        issue_summary = "Issue is blocked and may impact downstream work"
    if event.focus_space:
        issue_summary = f"Focused on space '{event.focus_space}' for issue review"
    if context:
        issue_summary += f" using {min(3, len(context))} context items"

    issue_citations = _context_citations(context) or ["bim:issue_thread"]
    if event.focus_space:
        issue_citations.append(f"bim:space:{event.focus_space}")

    issue_agent = AgentOutput(
        agent="IssueAgent",
        summary=issue_summary,
        proposals=["assign_to_owner", "add_follow_up_comment"],
        risk_signals=["blocking_dependency"] if event.payload.get("status") == "blocked" else [],
        confidence=0.85,
        citations=issue_citations,
    )

    schedule_summary = "Schedule impact estimated from current artifact timeline"
    if event.focus_space:
        schedule_summary = f"Schedule impact scoped to '{event.focus_space}'"

    schedule_citations = ["bim:schedule_snapshot"]
    if context:
        schedule_citations = _context_citations(context, fallback=schedule_citations)

    schedule_agent = AgentOutput(
        agent="ScheduleAgent",
        summary=schedule_summary,
        proposals=["resequence_task"],
        risk_signals=["deadline_slip"] if event.payload.get("due_overrun_days", 0) > 0 else [],
        confidence=0.80,
        citations=schedule_citations,
    )

    return [issue_agent, schedule_agent]


def _run_meeting_understanding_agents(
    event: NormalizedEvent,
    retrieved_context: list[RetrievedContext],
) -> list[AgentOutput]:
    building_element = event.payload.get("building_element")
    issue = event.payload.get("issue")
    discipline = event.payload.get("discipline")

    summary = f"Meeting discussion about {building_element or 'building element'} in {event.focus_space or 'space'}"
    proposals = []
    if issue:
        proposals.append("create_issue_note")
        summary += f": {issue}"
    if discipline:
        proposals.append("assign_to_discipline")

    meeting_agent = AgentOutput(
        agent="MeetingAgent",
        summary=summary,
        proposals=proposals,
        risk_signals=[],
        confidence=0.90,
        citations=_meeting_citations(event, retrieved_context),
    )

    return [meeting_agent]


def run_forecasting_agents(
    event: NormalizedEvent,
    retrieved_context: list[RetrievedContext] | None = None,
) -> list[AgentOutput]:
    context = retrieved_context or []
    overrun_days = int(event.payload.get("due_overrun_days", 0) or 0)
    risk_signals = ["cost_overrun"] if overrun_days >= 3 else []

    risk_agent = AgentOutput(
        agent="RiskAgent",
        summary=(
            f"Forecasted schedule and cost risk for '{event.focus_space}'"
            if event.focus_space
            else "Forecasted schedule and cost risk"
        ),
        proposals=["escalate_to_pm"] if risk_signals else ["monitor"],
        risk_signals=risk_signals,
        confidence=0.82,
        citations=_context_citations(context, fallback=["forecast:baseline_model_v1"]),
    )

    return [risk_agent]


def _context_citations(
    retrieved_context: list[RetrievedContext],
    fallback: list[str] | None = None,
) -> list[str]:
    citations = [item.ref for item in retrieved_context[:4] if item.ref]
    return citations or (fallback or [])


def _meeting_citations(
    event: NormalizedEvent,
    retrieved_context: list[RetrievedContext],
) -> list[str]:
    citations = ["meeting:transcript"]
    citations.extend(_context_citations(retrieved_context))
    if event.focus_space:
        citations.append(f"bim:space:{event.focus_space}")
    return list(dict.fromkeys(citations))
