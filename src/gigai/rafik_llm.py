from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
from typing import Any


DEFAULT_RAFIK_MODEL = "claude-haiku-4-5-20251001"


@dataclass
class RafikSpaceInference:
    space_name: str | None
    confidence: float
    reason: str
    provider: str = "rafik_claude"


def _env_truthy(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _extract_json(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if not text:
        return None

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)

    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < 0 or end <= start:
        return None

    candidate = text[start : end + 1]
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _map_space_name(space_name: str, available_spaces: list[str]) -> str | None:
    space_name = (space_name or "").strip()
    if not space_name:
        return None

    # Exact match first.
    for candidate in available_spaces:
        if candidate == space_name:
            return candidate

    # Normalized fallback.
    wanted = _normalize(space_name)
    if not wanted:
        return None

    for candidate in available_spaces:
        if _normalize(candidate) == wanted:
            return candidate

    return None


def infer_space_focus_from_rafik(
    transcript: str,
    available_spaces: list[str],
    drawing_context: dict | None = None,
) -> RafikSpaceInference | None:
    if not _env_truthy("GIGAI_RAFIK_LLM_ENABLED", default=False):
        return None

    cleaned_transcript = (transcript or "").strip()
    cleaned_spaces = [s.strip() for s in available_spaces if isinstance(s, str) and s.strip()]
    if not cleaned_transcript or not cleaned_spaces:
        return None

    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return None

    try:
        import anthropic
    except ModuleNotFoundError:
        return None

    model = os.getenv("GIGAI_RAFIK_LLM_MODEL", DEFAULT_RAFIK_MODEL).strip() or DEFAULT_RAFIK_MODEL
    max_tokens_raw = os.getenv("GIGAI_RAFIK_LLM_MAX_TOKENS", "350")
    try:
        max_tokens = max(128, int(max_tokens_raw))
    except ValueError:
        max_tokens = 350

    system_prompt = (
        "You are a BIM voice-command resolver. Choose exactly one space from the provided available_spaces list "
        "that best matches the transcript. Prefer spaces listed in drawing_context.visible_spaces when that list is present, "
        "especially for short commands that only contain a room number. If no reliable match exists, return null for space_name. "
        "Respond with JSON only: {\"space_name\": string|null, \"confidence\": number, \"reason\": string}."
    )

    user_payload = {
        "transcript": cleaned_transcript,
        "available_spaces": cleaned_spaces,
        "drawing_context": drawing_context or {},
    }

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)}],
        )
    except Exception:
        return None

    text_chunks: list[str] = []
    for block in getattr(response, "content", []) or []:
        block_type = getattr(block, "type", None)
        if block_type == "text":
            text_value = getattr(block, "text", "")
            if isinstance(text_value, str) and text_value.strip():
                text_chunks.append(text_value)

    llm_text = "\n".join(text_chunks).strip()
    parsed = _extract_json(llm_text)
    if parsed is None:
        return None

    selected = _map_space_name(str(parsed.get("space_name") or ""), cleaned_spaces)
    if not selected:
        return RafikSpaceInference(
            space_name=None,
            confidence=0.0,
            reason="rafik_llm_no_match",
            provider=f"rafik_claude:{model}",
        )

    confidence_raw = parsed.get("confidence", 0.75)
    try:
        confidence = float(confidence_raw)
    except (TypeError, ValueError):
        confidence = 0.75
    confidence = max(0.0, min(1.0, confidence))

    reason = str(parsed.get("reason") or "rafik_llm_space_match").strip() or "rafik_llm_space_match"
    if not reason.startswith("rafik_"):
        reason = f"rafik_{reason}"

    return RafikSpaceInference(
        space_name=selected,
        confidence=round(confidence, 2),
        reason=reason,
        provider=f"rafik_claude:{model}",
    )
