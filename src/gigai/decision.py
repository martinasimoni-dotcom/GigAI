from uuid import uuid4

from gigai.models import AgentOutput, DecisionPackage, NormalizedEvent, PolicyResult


HIGH_RISK_SIGNALS = {"cost_overrun", "regulatory_block"}
MEDIUM_RISK_SIGNALS = {"deadline_slip", "blocking_dependency"}


def build_decision(
    event: NormalizedEvent,
    policy: PolicyResult,
    agent_outputs: list[AgentOutput],
) -> DecisionPackage:
    if event.type == "meeting.focus":
        return _build_meeting_decision(event, policy, agent_outputs)

    confidence = sum(a.confidence for a in agent_outputs) / max(1, len(agent_outputs))
    if policy.blockers:
        confidence = max(0.1, confidence - 0.2)

    all_signals = {signal for output in agent_outputs for signal in output.risk_signals}
    if all_signals & HIGH_RISK_SIGNALS:
        risk_level = "high"
    elif all_signals & MEDIUM_RISK_SIGNALS:
        risk_level = "medium"
    else:
        risk_level = "low"

    proposal = "assign_to_owner"
    alternatives = ["request_pm_review", "post_team_notification"]
    if risk_level == "high":
        proposal = "request_pm_review"
    elif event.payload.get("status") == "blocked":
        proposal = "resequence_task"
    elif event.focus_space:
        proposal = "focus_space_triage"
        alternatives = ["assign_space_owner", "post_space_update"]

    evidence: list[dict[str, str]] = []
    for output in agent_outputs:
        for citation in output.citations:
            evidence.append({"source": output.agent, "ref": citation})

    return DecisionPackage(
        decision_id=f"dec_{uuid4().hex[:10]}",
        event_id=event.event_id,
        proposal=proposal,
        alternatives=alternatives,
        confidence=round(confidence, 2),
        risk_level=risk_level,
        constraints=policy.blockers,
        evidence=evidence,
    )


def _build_meeting_decision(
    event: NormalizedEvent,
    policy: PolicyResult,
    agent_outputs: list[AgentOutput],
) -> DecisionPackage:
    confidence = sum(a.confidence for a in agent_outputs) / max(1, len(agent_outputs))
    risk_level = "low"

    proposal = "log_meeting_note"
    alternatives = ["create_issue", "notify_team"]
    if event.focus_space:
        proposal = "focus_space_triage"
        alternatives = ["assign_space_owner", "post_space_update"]

    for output in agent_outputs:
        if "create_issue_note" in output.proposals:
            proposal = "create_issue_note"
            alternatives = ["assign_to_discipline", "focus_space"]

    evidence: list[dict[str, str]] = []
    for output in agent_outputs:
        for citation in output.citations:
            evidence.append({"source": output.agent, "ref": citation})

    return DecisionPackage(
        decision_id=f"dec_{uuid4().hex[:10]}",
        event_id=event.event_id,
        proposal=proposal,
        alternatives=alternatives,
        confidence=round(confidence, 2),
        risk_level=risk_level,
        constraints=policy.blockers,
        evidence=evidence,
    )
