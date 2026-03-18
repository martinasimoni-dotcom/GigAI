from __future__ import annotations

from gigai.coordination import CoordinationDecisionUpdate, CoordinationRequest, CoordinationService
from gigai.coordination.models import RevitElementInput, TeamContact


def _build_window_elements(total: int) -> list[RevitElementInput]:
    return [
        RevitElementInput(
            element_id=f"win_{index:03d}",
            category="window",
            level="3rd Floor",
            material="aluminum",
            x=float(index),
            y=1.0,
            z=9.0,
        )
        for index in range(1, total + 1)
    ]


def test_voice_material_change_generates_expected_plan() -> None:
    service = CoordinationService()
    request = CoordinationRequest(
        project_id="project_alpha",
        project_name="GigAI Demo Tower",
        transcript="Window material substitution, 3rd floor windows, aluminum to wood, 12 units",
        drawing_id="A-301",
        available_revit_elements=_build_window_elements(15),
        team_contacts=[
            TeamContact(name="Alice", email="alice@example.com", role="architect"),
            TeamContact(name="Bob", email="bob@example.com", role="pm"),
        ],
        execute_actions=False,
    )

    plan = service.create_plan(request)

    assert plan.normalized_change.element == "window"
    assert plan.normalized_change.location == "3rd Floor"
    assert plan.normalized_change.change_type == "material change"
    assert plan.normalized_change.from_material == "aluminum"
    assert plan.normalized_change.to_material == "wood"
    assert plan.normalized_change.quantity == 12
    assert len(plan.matched_targets) == 12
    assert len(plan.revit_action.revision_bubble_element_ids) == 12
    assert plan.acc_action.markup_title.lower().startswith("window material change")
    assert "Material Change" in plan.email_action.subject
    assert plan.task_action.title.lower().startswith("update 3rd")
    assert plan.status == "pending"


def test_accept_plan_executes_and_records_feedback() -> None:
    service = CoordinationService()
    request = CoordinationRequest(
        project_id="project_alpha",
        transcript="Change all 3rd floor windows from aluminum to wood around 12 units",
        available_revit_elements=_build_window_elements(12),
        team_contacts=[TeamContact(name="Alice", email="alice@example.com", role="architect")],
    )
    plan = service.create_plan(request)

    decided = service.decide_plan(
        plan.plan_id,
        CoordinationDecisionUpdate(decision="accept", actor="pm_1", execute_actions=True),
    )

    assert decided.status == "executed"
    assert decided.execution_results
    assert decided.execution_results.get("revit") in {"simulated", "executed", "failed"}
    assert decided.execution_results.get("gmail") in {"simulated", "sent", "failed", "disabled", "skipped"}


def test_reject_plan_updates_status() -> None:
    service = CoordinationService()
    request = CoordinationRequest(
        project_id="project_alpha",
        transcript="change 3rd floor windows from aluminum to wood 12 units",
        available_revit_elements=_build_window_elements(12),
    )
    plan = service.create_plan(request)

    decided = service.decide_plan(
        plan.plan_id,
        CoordinationDecisionUpdate(decision="reject", actor="pm_2", note="Need manual review"),
    )

    assert decided.status == "rejected"
