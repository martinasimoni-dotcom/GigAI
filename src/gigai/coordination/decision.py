from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from gigai.coordination.models import (
    ACCAction,
    BIMTarget,
    CalendarAction,
    CoordinationPlan,
    CoordinationRequest,
    DomainValidation,
    EmailAction,
    NormalizedChange,
    RevitAction,
    TaskAction,
)


def _recommendation(change: NormalizedChange, validation: DomainValidation) -> str:
    if not validation.valid:
        return "reject"
    if change.confidence >= 0.85:
        return "accept"
    return "review"


def build_coordination_plan(
    request: CoordinationRequest,
    change: NormalizedChange,
    targets: list[BIMTarget],
    validation: DomainValidation,
) -> CoordinationPlan:
    element_ids = [item.element_id for item in targets]
    due_at = request.due_at or (datetime.now(UTC) + timedelta(days=3))

    to_material = change.to_material or "updated_material"
    from_material = change.from_material or "current_material"

    revit_action = RevitAction(
        highlight_element_ids=element_ids,
        revision_bubble_element_ids=element_ids,
        parameter_updates=[
            {
                "element_id": element_id,
                "parameter": "Material",
                "from": from_material,
                "to": to_material,
            }
            for element_id in element_ids
        ],
    )

    acc_action = ACCAction(
        drawing_id=request.drawing_id,
        markup_title=f"{change.element.title()} material change - {change.location}",
        markup_body=(
            f"Requested change: {change.element} in {change.location}. "
            f"Material {from_material} -> {to_material}. "
            f"Target quantity: {change.quantity}."
        ),
    )

    recipients = [contact.email for contact in request.team_contacts if contact.email]
    email_subject = f"Material Change – {change.element.title()} Update ({change.location})"
    email_body = (
        "Hello team,\n\n"
        "GigAI detected and prepared a BIM coordination action plan.\n"
        f"Project: {request.project_id}\n"
        f"Change: {change.change_type}\n"
        f"Element: {change.element}\n"
        f"Location: {change.location}\n"
        f"Material: {from_material} -> {to_material}\n"
        f"Quantity: {change.quantity}\n"
        f"Matched Elements: {', '.join(element_ids) if element_ids else 'None'}\n\n"
        "Please review and approve execution.\n"
    )

    email_action = EmailAction(subject=email_subject, body=email_body, recipients=recipients)

    assignee = recipients[0] if recipients else None
    task_action = TaskAction(
        title=f"Update {change.location} {change.element} materials",
        assignee=assignee,
        due_at=due_at,
        description=(
            f"Apply material update {from_material} -> {to_material} for "
            f"{len(element_ids)} BIM elements and verify revision clouds."
        ),
    )

    calendar_action = CalendarAction(
        summary=f"GigAI Task: {task_action.title}",
        description=task_action.description,
        start_at=due_at,
        end_at=due_at + timedelta(hours=1),
        attendees=recipients,
    )

    recommendation = _recommendation(change, validation)

    return CoordinationPlan(
        plan_id=f"coord_{uuid4().hex[:10]}",
        project_id=request.project_id,
        meeting_id=request.meeting_id,
        transcript=request.transcript,
        normalized_change=change,
        matched_targets=targets,
        validation=validation,
        revit_action=revit_action,
        acc_action=acc_action,
        email_action=email_action,
        task_action=task_action,
        calendar_action=calendar_action,
        recommendation=recommendation,
    )
