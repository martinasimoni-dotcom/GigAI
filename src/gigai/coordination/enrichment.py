from __future__ import annotations

from gigai.coordination.models import BIMTarget, CoordinationRequest, NormalizedChange


def _normalize_level(value: str) -> str:
    return " ".join((value or "").lower().split())


def _normalize_category(value: str) -> str:
    value = (value or "").strip().lower()
    if value.endswith("s"):
        return value[:-1]
    return value


def map_to_bim_targets(request: CoordinationRequest, change: NormalizedChange) -> list[BIMTarget]:
    wanted_level = _normalize_level(change.location)
    wanted_category = _normalize_category(change.element)

    matches: list[BIMTarget] = []
    for element in request.available_revit_elements:
        level_match = not wanted_level or wanted_level in _normalize_level(element.level)
        category_match = wanted_category == _normalize_category(element.category)
        if level_match and category_match:
            matches.append(
                BIMTarget(
                    element_id=element.element_id,
                    category=element.category,
                    level=element.level,
                    material=element.material,
                    x=element.x,
                    y=element.y,
                    z=element.z,
                )
            )

    if change.quantity > 0 and matches:
        return matches[: change.quantity]
    return matches
