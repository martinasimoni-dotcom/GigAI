from functools import lru_cache
import re
from typing import Any

from gigai.language_reference import correct_transcript_with_reference
from gigai.llm import infer_space_focus
from gigai.meeting_intelligence.architectural_parser import ArchitecturalNLPParser
from gigai.rafik_llm import infer_space_focus_from_rafik


FOCUS_PATTERNS = [
    r"\bfocus on\s+(?P<space>[\w\s\-]+)",
    r"\bgo to\s+(?P<space>[\w\s\-]+)",
    r"\bfind\s+(?P<space>[\w\s\-]+)",
    r"\bshow\s+(?P<space>[\w\s\-]+)",
    r"\bselect\s+(?P<space>[\w\s\-]+)",
    r"\bmark\s+(?P<space>[\w\s\-]+)",
    r"\bcheck\s+(?P<space>[\w\s\-]+)",
    r"\b(?:in|at)\s+(?P<space>(?:studio|office|unit|room|flat|apartment)[\w\s\-]*\d{2,4}[a-z]?)",
    r"\b(?:studio|office)?\s*unit\s+(?P<space>[a-z]?\d{2,4}[a-z]?)",
    r"\broom\s+(?P<space>[a-z]?\d{2,4}[a-z]?)",
]


def _clean_candidate(space: str) -> str:
    # Trim common trailing filler words from spoken commands.
    trimmed = re.split(r"\s+(for|and|with|about|issue|issues|please)\b", space, maxsplit=1)[0]
    cleaned = trimmed.strip(" .,!?:;")
    if not cleaned:
        return cleaned

    # Keep readable casing for UI/annotations (e.g., north wing -> North Wing).
    words = []
    for token in cleaned.split():
        if any(ch.isdigit() for ch in token):
            words.append(token.upper() if token.isalpha() else token)
        elif len(token) <= 2 and token.isupper():
            words.append(token)
        else:
            words.append(token.capitalize())
    return " ".join(words)


def extract_space_candidate(transcript: str) -> str | None:
    text = transcript.strip()
    if not text:
        return None

    for pattern in FOCUS_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            candidate = _clean_candidate(match.group("space"))
            if candidate:
                return candidate
    return None


@lru_cache(maxsize=1)
def _get_architectural_parser() -> ArchitecturalNLPParser:
    return ArchitecturalNLPParser()


def _transcript_has_space_signal(transcript: str) -> bool:
    normalized = transcript.lower()
    if re.search(r"\b[a-z]?\d{2,4}[a-z]?\b", normalized):
        return True
    if extract_space_candidate(transcript):
        return True

    cue_words = {
        "room",
        "unit",
        "studio",
        "lobby",
        "corridor",
        "elevator",
        "stair",
        "office",
        "wing",
        "block",
        "tower",
        "floor",
    }
    tokens = set(re.findall(r"[a-z0-9]+", normalized))
    return bool(tokens & cue_words)


def _should_accept_space_inference(reason: str, confidence: float, transcript: str) -> bool:
    trusted_reasons = {
        "llm_exact_phrase_match",
        "llm_glossary_alias_match",
        "llm_room_number_match",
        "llm_visible_space_decoder_match",
    }
    if reason in trusted_reasons:
        return True

    if not _transcript_has_space_signal(transcript):
        return False

    if reason.startswith("rafik_"):
        return confidence >= 0.8

    if reason == "llm_semantic_fuzzy_match":
        return confidence >= 0.6

    return confidence >= 0.75


def _enrich_with_architectural_change(
    normalized_payload: dict[str, Any],
    transcript: str,
    project_id: str,
    available_spaces: list[str],
) -> None:
    if not transcript:
        return

    parser = _get_architectural_parser()
    changes = parser.parse_transcript(
        transcript_text=transcript,
        project_id=project_id or "project_alpha",
        meeting_id="voice_command",
        available_spaces=available_spaces,
    )
    if not changes:
        return

    primary_change = changes[0]
    if not normalized_payload.get("building_element") and primary_change.element_type:
        normalized_payload["building_element"] = primary_change.element_type
    if not normalized_payload.get("issue") and primary_change.description:
        normalized_payload["issue"] = primary_change.description
    if (
        not normalized_payload.get("space_name")
        and primary_change.space
        and primary_change.space != "Unknown"
    ):
        normalized_payload["space_name"] = primary_change.space
    if primary_change.extracted_properties:
        normalized_payload["architectural_properties"] = primary_change.extracted_properties


def build_voice_focus_payload(payload: dict[str, Any]) -> dict[str, Any]:
    transcript_raw = str(payload.get("transcript") or payload.get("voice_text") or "").strip()
    project_id = payload.get("projectId") or payload.get("project_id") or ""
    available_spaces = payload.get("available_spaces") or payload.get("spaces") or []
    visible_spaces = payload.get("visible_spaces") or []
    drawing_context = payload.get("drawing_context") if isinstance(payload.get("drawing_context"), dict) else {}
    if not visible_spaces and isinstance(drawing_context.get("visible_spaces"), list):
        visible_spaces = drawing_context.get("visible_spaces") or []

    reference_spaces = visible_spaces or available_spaces
    transcript = correct_transcript_with_reference(transcript_raw, reference_spaces) if transcript_raw else ""
    if not transcript:
        transcript = transcript_raw

    normalized_payload: dict[str, Any] = {
        "projectId": project_id,
        "type": "meeting.focus",
        "meeting_utterance": transcript,
        "available_spaces": available_spaces,
        "visible_spaces": visible_spaces,
        "status": payload.get("status", "open"),
        "due_overrun_days": payload.get("due_overrun_days", 0),
        "drawing_context": drawing_context,
    }
    if transcript_raw and transcript_raw != transcript:
        normalized_payload["transcript_original"] = transcript_raw
        normalized_payload["transcript_corrected"] = transcript

    # Include extracted architecture information if available
    if payload.get("building_element"):
        normalized_payload["building_element"] = payload["building_element"]
    if payload.get("issue"):
        normalized_payload["issue"] = payload["issue"]
    if payload.get("discipline"):
        normalized_payload["discipline"] = payload["discipline"]
    if payload.get("fireflies_transcript_id"):
        normalized_payload["fireflies_transcript_id"] = payload["fireflies_transcript_id"]
    if payload.get("fireflies_transcript_title"):
        normalized_payload["fireflies_transcript_title"] = payload["fireflies_transcript_title"]
    if payload.get("fireflies_transcript_url"):
        normalized_payload["fireflies_transcript_url"] = payload["fireflies_transcript_url"]

    _enrich_with_architectural_change(normalized_payload, transcript, str(project_id), available_spaces)

    if available_spaces:
        rafik_inference = infer_space_focus_from_rafik(
            transcript,
            available_spaces,
            drawing_context={**drawing_context, "visible_spaces": visible_spaces},
        )
        if (
            rafik_inference
            and rafik_inference.space_name
            and _should_accept_space_inference(
                rafik_inference.reason,
                float(rafik_inference.confidence),
                transcript,
            )
        ):
            normalized_payload["llm_space_name"] = rafik_inference.space_name
            normalized_payload["llm_reason"] = rafik_inference.reason
            normalized_payload["llm_confidence"] = rafik_inference.confidence
            normalized_payload["llm_provider"] = rafik_inference.provider
        else:
            llm_inference = infer_space_focus(
                transcript,
                available_spaces,
                drawing_context={**drawing_context, "visible_spaces": visible_spaces},
                preferred_spaces=visible_spaces,
            )
            if (
                llm_inference.space_name
                and _should_accept_space_inference(
                    llm_inference.reason,
                    float(llm_inference.confidence),
                    transcript,
                )
            ):
                normalized_payload["llm_space_name"] = llm_inference.space_name
                normalized_payload["llm_reason"] = llm_inference.reason
                normalized_payload["llm_confidence"] = llm_inference.confidence
                normalized_payload["llm_provider"] = "gigai_local"
            else:
                # LLM could not map to provided catalog. Keep a best-effort explicit
                # candidate so API still returns a focus space instead of empty.
                candidate = extract_space_candidate(transcript)
                if candidate:
                    normalized_payload["space_name"] = candidate
    else:
        # If no space catalog is provided, fall back to phrase extraction.
        candidate = extract_space_candidate(transcript)
        if candidate:
            normalized_payload["space_name"] = candidate

    return normalized_payload
