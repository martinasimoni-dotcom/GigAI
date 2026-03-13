"""
Normalizer module — PROC-01, PROC-02.

normalize_event(raw_event: RawEvent) -> NormalizedEvent

Calls Haiku with the normalization prompt (config/prompts/normalization.txt),
validates the response with Pydantic NormalizedEvent, and flags low-confidence
extractions (< 70) with review_required=True.

Uses tenacity retry (3 attempts) on Pydantic ValidationError.
"""
import json
import logging
from pathlib import Path

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from pydantic import ValidationError

from src.shared.llm.claude import call_haiku
from src.shared.models.events import NormalizedEvent, RawEvent

logger = logging.getLogger(__name__)

_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "config" / "prompts" / "normalization.txt"
)

_NORMALIZATION_SCHEMA = {
    "type": "object",
    "properties": {
        "event_id": {"type": "string"},
        "source": {"type": "string"},
        "event_type": {"type": "string"},
        "material_original": {"type": ["string", "null"]},
        "material_new": {"type": ["string", "null"]},
        "location": {"type": ["string", "null"]},
        "quantity": {"type": ["integer", "null"]},
        "people": {"type": "array", "items": {"type": "object"}},
        "deadlines": {"type": "array", "items": {"type": "string"}},
        "change_type": {"type": ["string", "null"]},
        "summary": {"type": "string"},
        "confidence": {"type": "integer"},
        "estimated_cost": {"type": ["number", "null"]},
    },
    "required": ["event_id", "source", "event_type", "summary", "confidence"],
}

_SYSTEM = (
    "You are a construction project data extractor. "
    "Respond ONLY with valid JSON matching the schema provided. "
    "Use flat field names exactly as specified. Do NOT use nested objects."
)


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((ValidationError, ValueError, json.JSONDecodeError)),
    reraise=True,
)
def _extract_with_retry(prompt: str, raw_event: RawEvent) -> NormalizedEvent:
    """Call Haiku and validate; retried up to 3 times on validation failure."""
    raw_json = call_haiku(prompt=prompt, system=_SYSTEM, output_schema=_NORMALIZATION_SCHEMA)
    data = json.loads(raw_json)
    # Inject authoritative metadata from RawEvent (Haiku may hallucinate these)
    data["event_id"] = raw_event.event_id
    data["source"] = raw_event.source
    # change_type is not a NormalizedEvent field — remove if present to avoid extra="forbid" error
    data.pop("change_type", None)
    return NormalizedEvent(**data)


def normalize_event(raw_event: RawEvent) -> NormalizedEvent:
    """
    Normalize a RawEvent into a structured NormalizedEvent.

    Calls Haiku with the normalization prompt. Validates output with Pydantic.
    Flags confidence < 70 with review_required=True (does NOT reject the event).
    Retries up to 3 times on Pydantic ValidationError via tenacity.

    Returns:
        NormalizedEvent — validated and populated from Haiku extraction.

    Raises:
        ValidationError / json.JSONDecodeError — after 3 failed attempts.
    """
    base_prompt = _load_prompt()
    # Append the raw payload text to the prompt
    raw_text = json.dumps(raw_event.raw_payload, ensure_ascii=False)
    full_prompt = f"{base_prompt}\n\n{raw_text}"

    event = _extract_with_retry(full_prompt, raw_event)

    if event.confidence < 70:
        event = event.model_copy(update={"review_required": True})
        logger.warning({
            "event": "low_confidence_extraction",
            "event_id": event.event_id,
            "confidence": event.confidence,
            "review_required": True,
        })
    else:
        logger.info({
            "event": "normalized",
            "event_id": event.event_id,
            "event_type": event.event_type,
            "confidence": event.confidence,
        })

    return event
