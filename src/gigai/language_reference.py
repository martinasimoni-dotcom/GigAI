from __future__ import annotations

from dataclasses import dataclass
from difflib import get_close_matches
from functools import lru_cache
import json
import os
from pathlib import Path
import re


DEFAULT_REFERENCE_PATH = "config/architecture_reference.json"

DEFAULT_REFERENCE_DATA = {
    "actions": [
        "move",
        "shift",
        "rotate",
        "extend",
        "reduce",
        "increase",
        "change",
        "replace",
        "add",
        "remove",
        "align",
        "adjust",
        "fix",
        "rework",
        "review",
    ],
    "elements": [
        "wall",
        "door",
        "window",
        "column",
        "beam",
        "stair",
        "core",
        "facade",
        "floor",
        "ceiling",
        "balcony",
        "corridor",
        "slab",
        "railing",
        "partition",
        "cladding",
        "opening",
        "kitchen",
        "toilet",
        "bathroom",
        "restroom",
        "material",
        "materials",
        "layout",
    ],
    "spaces": [
        "studio 404",
        "meeting room",
        "lobby",
        "entrance",
        "office",
        "corridor",
        "balcony",
        "stair core",
        "bedroom",
        "conference room",
    ],
}

SPOKEN_DIGIT_MAP = {
    "zero": "0",
    "oh": "0",
    "o": "0",
    "one": "1",
    "won": "1",
    "two": "2",
    "too": "2",
    "three": "3",
    "four": "4",
    "for": "4",
    "fore": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "ate": "8",
    "nine": "9",
}

ARCHITECTURAL_TOKEN_REWRITES = {
    "stdo": "studio",
    "studo": "studio",
    "unet": "unit",
    "unti": "unit",
    "kitchan": "kitchen",
    "kitchn": "kitchen",
    "layot": "layout",
    "layoout": "layout",
    "tolet": "toilet",
    "toliet": "toilet",
    "optons": "options",
    "elevater": "elevator",
    "coridor": "corridor",
    "loby": "lobby",
}


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _tokenize(value: str) -> list[str]:
    normalized = _normalize_text(value)
    if not normalized:
        return []
    return normalized.split()


@dataclass
class ArchitectureReference:
    terms: set[str]


def _build_terms(payload: dict) -> set[str]:
    terms: set[str] = set()
    for value in payload.values():
        if isinstance(value, list):
            for item in value:
                if not isinstance(item, str):
                    continue
                for token in _tokenize(item):
                    if len(token) >= 2:
                        terms.add(token)
    return terms


@lru_cache(maxsize=4)
def load_architecture_reference() -> ArchitectureReference:
    path = Path(os.getenv("GIGAI_ARCH_REFERENCE_PATH", DEFAULT_REFERENCE_PATH))
    payload = DEFAULT_REFERENCE_DATA

    if path.exists() and path.is_file():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                payload = raw
        except (json.JSONDecodeError, OSError):
            payload = DEFAULT_REFERENCE_DATA

    return ArchitectureReference(terms=_build_terms(payload))


def _extract_room_root_tokens(value: str) -> set[str]:
    roots: set[str] = set()
    for token in re.findall(r"\b[a-z]?[0-9]{2,4}[a-z]?\b", _normalize_text(value)):
        digits = "".join(ch for ch in token if ch.isdigit())
        if len(digits) >= 2:
            roots.add(digits)
    return roots


def _collapse_spoken_digit_sequences(tokens: list[str]) -> list[str]:
    collapsed: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token not in SPOKEN_DIGIT_MAP:
            collapsed.append(token)
            index += 1
            continue

        end = index
        digits: list[str] = []
        while end < len(tokens) and tokens[end] in SPOKEN_DIGIT_MAP:
            digits.append(SPOKEN_DIGIT_MAP[tokens[end]])
            end += 1

        if len(digits) >= 2:
            collapsed.append("".join(digits))
            index = end
            continue

        collapsed.append(token)
        index += 1

    return collapsed


def normalize_speech_text(transcript: str) -> str:
    text = _normalize_text(transcript)
    if not text:
        return ""

    rewritten = [ARCHITECTURAL_TOKEN_REWRITES.get(token, token) for token in text.split()]
    collapsed = _collapse_spoken_digit_sequences(rewritten)
    return " ".join(collapsed).strip()


def correct_transcript_with_reference(transcript: str, available_spaces: list[str]) -> str:
    text = normalize_speech_text(transcript)
    if not text:
        return ""

    reference = load_architecture_reference()
    lexicon = set(reference.terms)
    for space in available_spaces:
        if isinstance(space, str):
            lexicon.update(_tokenize(space))

    # Keep common function words untouched.
    stop_words = {
        "the",
        "a",
        "an",
        "in",
        "on",
        "at",
        "to",
        "for",
        "and",
        "with",
        "of",
        "from",
        "same",
        "this",
        "that",
        "it",
        "is",
        "be",
        "we",
        "should",
        "can",
        "could",
        "maybe",
        "please",
    }

    corrected_tokens: list[str] = []
    for token in text.split():
        if token in lexicon or token in stop_words:
            corrected_tokens.append(token)
            continue
        if token.isdigit():
            corrected_tokens.append(token)
            continue
        if len(token) <= 2:
            corrected_tokens.append(token)
            continue

        cutoff = 0.86 if len(token) >= 5 else 0.92
        match = get_close_matches(token, lexicon, n=1, cutoff=cutoff)
        corrected_tokens.append(match[0] if match else token)

    corrected = " ".join(corrected_tokens)

    # If transcript contains a unique room root in available spaces, inject that
    # exact space phrase to stabilize downstream parser.
    roots_in_text = _extract_room_root_tokens(corrected)
    if roots_in_text:
        matching_spaces: list[str] = []
        for space in available_spaces:
            if not isinstance(space, str):
                continue
            roots_in_space = _extract_room_root_tokens(space)
            if roots_in_space & roots_in_text:
                matching_spaces.append(space)
        if len(matching_spaces) == 1:
            canonical = _normalize_text(matching_spaces[0])
            if canonical and canonical not in corrected:
                corrected = f"{corrected} in {canonical}".strip()

    return corrected
