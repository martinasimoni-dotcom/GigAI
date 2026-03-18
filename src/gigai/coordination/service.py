from __future__ import annotations

from datetime import UTC, datetime

from gigai.coordination.decision import build_coordination_plan
from gigai.coordination.domain import validate_change_targets
from gigai.coordination.enrichment import map_to_bim_targets
from gigai.coordination.execution import execute_plan
from gigai.coordination.models import (
    CoordinationDecisionUpdate,
    CoordinationPlan,
    CoordinationRequest,
)
from gigai.coordination.normalization import normalize_voice_command
from gigai.storage import (
    add_feedback,
    get_coordination_plan,
    publish_bus_event,
    save_coordination_plan,
    update_coordination_plan,
)


class CoordinationService:
    def create_plan(self, request: CoordinationRequest) -> CoordinationPlan:
        normalized = normalize_voice_command(request)
        targets = map_to_bim_targets(request, normalized)
        validation = validate_change_targets(normalized, targets)
        plan = build_coordination_plan(request, normalized, targets, validation)

        save_coordination_plan(
            plan_id=plan.plan_id,
            project_id=plan.project_id,
            meeting_id=plan.meeting_id,
            transcript=plan.transcript,
            plan=plan.model_dump(mode="json"),
            status=plan.status,
        )

        publish_bus_event(
            "coordination.plan.created",
            {
                "plan_id": plan.plan_id,
                "project_id": plan.project_id,
                "meeting_id": plan.meeting_id,
                "recommendation": plan.recommendation,
            },
        )

        publish_bus_event(
            "coordination.transcript.stored",
            {
                "plan_id": plan.plan_id,
                "project_id": plan.project_id,
                "meeting_id": plan.meeting_id,
                "transcript": plan.transcript,
            },
        )

        return plan

    def get_plan(self, plan_id: str) -> CoordinationPlan | None:
        row = get_coordination_plan(plan_id)
        if row is None:
            return None
        return CoordinationPlan(**row["plan_json"])

    def decide_plan(self, plan_id: str, update: CoordinationDecisionUpdate) -> CoordinationPlan:
        stored = self.get_plan(plan_id)
        if stored is None:
            raise ValueError(f"Coordination plan '{plan_id}' was not found.")

        if update.decision == "reject":
            stored.status = "rejected"
            stored.updated_at = datetime.now(UTC)
            add_feedback(
                decision_id=plan_id,
                approval_id=None,
                outcome="rejected",
                feedback={"actor": update.actor, "note": update.note or ""},
            )
            update_coordination_plan(
                plan_id=stored.plan_id,
                status=stored.status,
                plan=stored.model_dump(mode="json"),
            )
            publish_bus_event(
                "coordination.plan.rejected",
                {
                    "plan_id": stored.plan_id,
                    "actor": update.actor,
                    "note": update.note or "",
                },
            )
            return stored

        stored.status = "approved"
        stored.updated_at = datetime.now(UTC)
        if update.execute_actions:
            stored.execution_results = execute_plan(stored)
            stored.status = "executed"

        add_feedback(
            decision_id=plan_id,
            approval_id=None,
            outcome="accepted",
            feedback={
                "actor": update.actor,
                "note": update.note or "",
                "execution_results": stored.execution_results,
            },
        )
        update_coordination_plan(
            plan_id=stored.plan_id,
            status=stored.status,
            plan=stored.model_dump(mode="json"),
        )
        publish_bus_event(
            "coordination.plan.approved",
            {
                "plan_id": stored.plan_id,
                "actor": update.actor,
                "executed": update.execute_actions,
                "status": stored.status,
            },
        )
        return stored
