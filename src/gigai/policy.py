from gigai.models import NormalizedEvent, PolicyResult


CLASSIFICATION_MAP = {
    "issue.updated": "issue_management",
    "rfi.created": "rfi_management",
    "schedule.changed": "schedule_management",
}


def apply_policy(event: NormalizedEvent) -> PolicyResult:
    classification = CLASSIFICATION_MAP.get(event.type, "general_project_event")

    base_priority = {
        "issue_management": 70,
        "rfi_management": 80,
        "schedule_management": 85,
        "general_project_event": 50,
    }[classification]

    blockers: list[str] = []
    if not event.project_id or event.project_id == "unknown_project":
        blockers.append("missing_project_id")

    security_passed = True
    if event.payload.get("restricted") is True:
        blockers.append("security_restricted_event")
        security_passed = False

    priority_score = min(100, base_priority + (10 if event.payload.get("urgent") else 0))

    return PolicyResult(
        classification=classification,
        priority_score=priority_score,
        security_passed=security_passed,
        blockers=blockers,
    )
