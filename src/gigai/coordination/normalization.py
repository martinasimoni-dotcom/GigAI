from __future__ import annotations

import re

from gigai.coordination.models import CoordinationRequest, NormalizedChange


_ELEMENT_PATTERNS = [
    (r"\bwindows?\b", "window"),
    (r"\bdoors?\b", "door"),
    (r"\bwalls?\b", "wall"),
    (r"\bcolumns?\b", "column"),
    (r"\bbeams?\b", "beam"),
]

_MATERIAL_ALIASES = {
    "aluminum": "aluminum",
    "aluminium": "aluminum",
    "aluminum": "aluminum",
    "wood": "wood",
    "timber": "wood",
    "steel": "steel",
    "glass": "glass",
    "concrete": "concrete",
    "brick": "brick",
    "stone": "stone",
    "pvc": "pvc",
}


def _extract_location(transcript: str) -> str:
    patterns = [
        r"\b(\d+(?:st|nd|rd|th)\s+floor)\b",
        r"\b(level\s+\d+)\b",
        r"\b(floor\s+\d+)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, transcript, flags=re.IGNORECASE)
        if match:
            location = " ".join(match.group(1).strip().split())
            normalized = location.lower()
            normalized = normalized.replace("floor", "Floor")
            normalized = normalized.replace("level", "Level")
            return normalized
    return "Unknown"


def _extract_element(transcript: str) -> str:
    for pattern, canonical in _ELEMENT_PATTERNS:
        if re.search(pattern, transcript, flags=re.IGNORECASE):
            return canonical
    return "element"


def _extract_quantity(transcript: str) -> int:
    match = re.search(r"\b(\d{1,4})\s*(?:units?|nos?|items?)\b", transcript, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))

    fallback = re.search(r"\b(\d{1,4})\b", transcript)
    if fallback:
        return int(fallback.group(1))
    return 0


def _extract_material_pair(transcript: str) -> tuple[str | None, str | None]:
    match = re.search(
        r"\bfrom\s+([a-z][a-z\s\-]{1,40}?)\s+to\s+([a-z][a-z\s\-]{1,40}?)(?:\b|[,.])",
        transcript,
        flags=re.IGNORECASE,
    )
    if not match:
        fallback = re.search(
            r"\b([a-z]{3,20})\s+to\s+([a-z]{3,20})\b",
            transcript,
            flags=re.IGNORECASE,
        )
        if not fallback:
            return None, None
        source_raw = fallback.group(1).strip().lower()
        target_raw = fallback.group(2).strip().lower()
        source = _MATERIAL_ALIASES.get(source_raw)
        target = _MATERIAL_ALIASES.get(target_raw)
        if source and target:
            return source, target
        return None, None

    source_raw = match.group(1).strip().lower()
    target_raw = match.group(2).strip().lower()
    source = _MATERIAL_ALIASES.get(source_raw, source_raw)
    target = _MATERIAL_ALIASES.get(target_raw, target_raw)
    return source, target


def normalize_voice_command(request: CoordinationRequest) -> NormalizedChange:
    transcript = request.transcript.strip()
    element = _extract_element(transcript)
    location = _extract_location(transcript)
    quantity = _extract_quantity(transcript)
    from_material, to_material = _extract_material_pair(transcript)

    change_type = "design change"
    if from_material and to_material:
        change_type = "material change"
    elif re.search(r"\b(move|shift|relocate)\b", transcript, flags=re.IGNORECASE):
        change_type = "location adjustment"

    confidence = 0.45
    if element != "element":
        confidence += 0.15
    if location != "Unknown":
        confidence += 0.15
    if quantity > 0:
        confidence += 0.1
    if from_material and to_material:
        confidence += 0.15

    confidence = max(0.0, min(1.0, confidence))

    return NormalizedChange(
        element=element,
        location=location,
        change_type=change_type,
        from_material=from_material,
        to_material=to_material,
        quantity=quantity,
        confidence=round(confidence, 2),
    )
