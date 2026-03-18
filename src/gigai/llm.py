from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re

from gigai.glossary import ProjectGlossary, get_project_glossary
from gigai.language_reference import normalize_speech_text


ARCH_WORD_NORMALIZATION = {
    # ASR misspellings / common spoken variants
    "loby": "lobby",
    "lobi": "lobby",
    "coridor": "corridor",
    "corredor": "corridor",
    "elevater": "elevator",
    "lift": "elevator",
    "staircase": "stair",
    "staires": "stair",
    "toilet": "restroom",
    "washroom": "restroom",
    "wc": "restroom",
    "flat": "unit",
    "apartment": "unit",
    "apt": "unit",
    "foyer": "lobby",
    "hallway": "corridor",
}

COMMAND_PREFIXES = (
    "focus on",
    "go to",
    "select",
    "review",
    "check",
    "mark",
    "show",
    "find",
)


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _build_term_map(glossary: ProjectGlossary) -> dict[str, str]:
    term_map = dict(ARCH_WORD_NORMALIZATION)
    # Project glossary overrides/extends defaults.
    term_map.update(glossary.term_normalization)
    return term_map


def _normalize_arch_text(value: str, term_map: dict[str, str]) -> str:
    normalized = normalize_speech_text(value)
    if not normalized:
        return normalized

    # Split compact grid-like tokens (e.g., d4 -> d 4) to increase matching.
    normalized = re.sub(r"\b([a-z])([0-9]{1,3})\b", r"\1 \2", normalized)

    words = []
    for token in normalized.split():
        words.append(term_map.get(token, token))
    return " ".join(words)


def _tokenize(value: str, term_map: dict[str, str]) -> set[str]:
    normalized = _normalize_arch_text(value, term_map)
    if not normalized:
        return set()
    return set(normalized.split())


def _extract_room_like_tokens(value: str) -> set[str]:
    return set(re.findall(r"\b[a-z]?[0-9]{2,4}[a-z]?\b", _normalize_text(value)))


def _extract_room_roots(value: str) -> set[str]:
    roots: set[str] = set()
    for token in _extract_room_like_tokens(value):
        digits = "".join(ch for ch in token if ch.isdigit())
        if len(digits) >= 2:
            roots.add(digits)
    return roots


def _strip_command_prefix(value: str) -> str:
    normalized = _normalize_text(value)
    for prefix in COMMAND_PREFIXES:
        if normalized == prefix:
            return ""
        if normalized.startswith(prefix + " "):
            return normalized[len(prefix) + 1 :].strip()
    return normalized


def _is_short_numeric_command(value: str) -> bool:
    stripped = _strip_command_prefix(value)
    if not stripped:
        return False

    tokens = stripped.split()
    if len(tokens) > 3:
        return False

    return len(_extract_room_roots(stripped)) == 1


def _room_root_similarity(left: str, right: str) -> float:
    left_digits = "".join(ch for ch in left if ch.isdigit())
    right_digits = "".join(ch for ch in right if ch.isdigit())
    if not left_digits or not right_digits:
        return 0.0

    if left_digits == right_digits:
        return 1.0

    width = max(len(left_digits), len(right_digits))
    left_padded = left_digits.zfill(width)
    right_padded = right_digits.zfill(width)
    positional = sum(1 for l_digit, r_digit in zip(left_padded, right_padded) if l_digit == r_digit) / width
    suffix_bonus = 0.2 if len(left_digits) >= 2 and len(right_digits) >= 2 and left_digits[-2:] == right_digits[-2:] else 0.0
    fuzzy = SequenceMatcher(None, left_digits, right_digits).ratio() * 0.15
    return min(1.0, positional + suffix_bonus + fuzzy)


@dataclass
class SpaceInference:
    space_name: str | None
    confidence: float
    reason: str


class LlmLayer:
    """
    LLM reasoning layer abstraction.

    Current provider uses deterministic semantic/fuzzy scoring so it can run
    locally without external dependencies. The interface is intentionally kept
    stable so a hosted LLM provider can replace this logic later.
    """

    def __init__(self, glossary: ProjectGlossary | None = None):
        self.glossary = glossary or get_project_glossary()

    def infer_space(
        self,
        transcript: str,
        available_spaces: list[str],
        drawing_context: dict | None = None,
        preferred_spaces: list[str] | None = None,
    ) -> SpaceInference:
        text = transcript.strip()
        if not text:
            return SpaceInference(space_name=None, confidence=0.0, reason="empty_transcript")

        candidates = [s.strip() for s in available_spaces if isinstance(s, str) and s.strip()]
        if not candidates:
            return SpaceInference(space_name=None, confidence=0.0, reason="no_space_catalog")

        term_map = _build_term_map(self.glossary)
        context = drawing_context or {}
        preferred_catalog = [
            s.strip()
            for s in (preferred_spaces or context.get("visible_spaces") or [])
            if isinstance(s, str) and s.strip()
        ]
        preferred_set = set(preferred_catalog)
        normalized_text = f" {_normalize_arch_text(text, term_map)} "
        text_tokens = _tokenize(text, term_map)
        text_room_tokens = _extract_room_like_tokens(text)
        text_room_roots = _extract_room_roots(text)
        short_numeric_command = _is_short_numeric_command(text)
        context_tokens = _tokenize(str(context.get("view_name", "")), term_map)
        context_tokens |= _tokenize(str(context.get("view_type", "")), term_map)

        decoded_visible_space = self._decode_visible_space(text, preferred_catalog, term_map)
        if decoded_visible_space is not None:
            return decoded_visible_space

        candidate_root_frequency: dict[str, int] = {}
        for candidate in candidates:
            for root in _extract_room_roots(candidate):
                candidate_root_frequency[root] = candidate_root_frequency.get(root, 0) + 1

        best_space: str | None = None
        best_score = 0.0
        best_reason = "no_match"

        for candidate in candidates:
            aliases = self.glossary.aliases_for(candidate)
            candidate_phrases = [candidate] + aliases

            phrase_hit_reason = "llm_exact_phrase_match"
            if aliases:
                for alias in aliases:
                    alias_norm = _normalize_arch_text(alias, term_map)
                    if alias_norm and f" {alias_norm} " in normalized_text:
                        return SpaceInference(
                            space_name=candidate,
                            confidence=0.99,
                            reason="llm_glossary_alias_match",
                        )

            best_phrase_score = 0.0
            for phrase in candidate_phrases:
                phrase_norm = _normalize_arch_text(phrase, term_map)
                if not phrase_norm:
                    continue

                if f" {phrase_norm} " in normalized_text:
                    return SpaceInference(
                        space_name=candidate,
                        confidence=0.99,
                        reason=phrase_hit_reason,
                    )

                phrase_tokens = _tokenize(phrase, term_map)
                phrase_room_tokens = _extract_room_like_tokens(phrase)
                phrase_room_roots = _extract_room_roots(phrase)

                token_overlap = 0.0
                if phrase_tokens:
                    token_overlap = len(phrase_tokens & text_tokens) / len(phrase_tokens)

                fuzzy_ratio = SequenceMatcher(None, phrase_norm, _normalize_arch_text(text, term_map)).ratio()

                context_overlap = 0.0
                if context_tokens and phrase_tokens:
                    context_overlap = len(phrase_tokens & context_tokens) / len(phrase_tokens)

                room_token_overlap = 0.0
                if phrase_room_tokens and text_room_tokens:
                    room_token_overlap = len(phrase_room_tokens & text_room_tokens) / len(phrase_room_tokens)

                room_root_overlap = 0.0
                if phrase_room_roots and text_room_roots:
                    room_root_overlap = len(phrase_room_roots & text_room_roots) / len(phrase_room_roots)

                unique_room_number_match = False
                if phrase_room_roots and text_room_roots and (phrase_room_roots & text_room_roots):
                    unique_room_number_match = all(
                        candidate_root_frequency.get(root, 0) == 1 for root in (phrase_room_roots & text_room_roots)
                    )

                if unique_room_number_match:
                    if not (preferred_set and short_numeric_command and candidate not in preferred_set):
                        return SpaceInference(
                            space_name=candidate,
                            confidence=0.98,
                            reason="llm_room_number_match",
                        )

                visibility_bonus = 0.18 if candidate in preferred_set else 0.0
                decoder_bonus = 0.0
                if short_numeric_command and candidate in preferred_set and phrase_room_roots and text_room_roots:
                    decoder_bonus = max(
                        _room_root_similarity(text_root, phrase_root)
                        for text_root in text_room_roots
                        for phrase_root in phrase_room_roots
                    ) * 0.20

                score = (
                    (token_overlap * 0.45)
                    + (fuzzy_ratio * 0.15)
                    + (context_overlap * 0.05)
                    + (room_token_overlap * 0.20)
                    + (room_root_overlap * 0.15)
                    + visibility_bonus
                    + decoder_bonus
                )

                if score > best_phrase_score:
                    best_phrase_score = score

            if best_phrase_score > best_score:
                best_score = best_phrase_score
                best_space = candidate
                best_reason = "llm_semantic_fuzzy_match"

        if best_space is None or best_score < 0.35:
            return SpaceInference(space_name=None, confidence=best_score, reason="llm_low_confidence")

        return SpaceInference(space_name=best_space, confidence=round(best_score, 2), reason=best_reason)

    def _decode_visible_space(
        self,
        transcript: str,
        visible_spaces: list[str],
        term_map: dict[str, str],
    ) -> SpaceInference | None:
        if not visible_spaces or not _is_short_numeric_command(transcript):
            return None

        transcript_roots = _extract_room_roots(transcript)
        if not transcript_roots:
            return None

        best_space: str | None = None
        best_score = 0.0
        second_score = 0.0
        text_tokens = _tokenize(transcript, term_map)

        for candidate in visible_spaces:
            candidate_roots = _extract_room_roots(candidate)
            if not candidate_roots:
                continue

            root_score = max(
                _room_root_similarity(text_root, candidate_root)
                for text_root in transcript_roots
                for candidate_root in candidate_roots
            )
            token_overlap = 0.0
            candidate_tokens = _tokenize(candidate, term_map)
            if candidate_tokens and text_tokens:
                token_overlap = len(candidate_tokens & text_tokens) / len(candidate_tokens)

            score = (root_score * 0.85) + (token_overlap * 0.15)
            if score > best_score:
                second_score = best_score
                best_score = score
                best_space = candidate
            elif score > second_score:
                second_score = score

        if best_space and best_score >= 0.72 and (best_score - second_score) >= 0.15:
            return SpaceInference(
                space_name=best_space,
                confidence=round(min(0.96, best_score), 2),
                reason="llm_visible_space_decoder_match",
            )

        return None


def infer_space_focus(
    transcript: str,
    available_spaces: list[str],
    drawing_context: dict | None = None,
    preferred_spaces: list[str] | None = None,
) -> SpaceInference:
    return LlmLayer().infer_space(
        transcript,
        available_spaces,
        drawing_context=drawing_context,
        preferred_spaces=preferred_spaces,
    )
