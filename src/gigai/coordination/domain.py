from __future__ import annotations

from gigai.coordination.models import BIMTarget, DomainValidation, NormalizedChange


def validate_change_targets(change: NormalizedChange, targets: list[BIMTarget]) -> DomainValidation:
    blockers: list[str] = []
    warnings: list[str] = []

    if change.element == "element":
        blockers.append("element_type_not_detected")

    if change.location == "Unknown":
        warnings.append("location_not_detected")

    if change.quantity > 0 and len(targets) < change.quantity:
        blockers.append("insufficient_matching_bim_elements")

    if not targets:
        blockers.append("no_bim_targets_matched")

    if change.change_type == "material change" and not change.to_material:
        blockers.append("target_material_missing")

    return DomainValidation(valid=not blockers, blockers=blockers, warnings=warnings)
