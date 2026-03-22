from __future__ import annotations

import json
import re
from statistics import mean
from typing import Literal

from pydantic import BaseModel, Field

from gigai.glossary import get_project_glossary
from gigai.language_reference import correct_transcript_with_reference

from .architectural_parser import ArchitecturalNLPParser


EntityType = Literal["space", "element", "material", "person"]
ActionType = Literal["change", "add", "remove", "approve", "review"]


class StructuredEntity(BaseModel):
    type: EntityType
    value: str
    confidence: float = Field(ge=0.0, le=1.0)


class StructuredAction(BaseModel):
    action: ActionType
    target: str
    space: str
    details: str
    owner: str
    deadline: str
    confidence: float = Field(ge=0.0, le=1.0)


class StructuredMeetingIntelligence(BaseModel):
    transcript_cleaned: str
    entities: list[StructuredEntity] = Field(default_factory=list)
    actions: list[StructuredAction] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    design_changes: list[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0)


def _normalize_unit_tokens(text: str) -> str:
    normalized = text
    normalized = re.sub(r"\bmillimeters?\b", "mm", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bcentimeters?\b", "cm", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bmeters?\b", "m", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _extract_people_from_transcript(transcript: str) -> list[str]:
    people: list[str] = []
    for line in transcript.splitlines():
        match = re.match(r"^([A-Za-z][A-Za-z0-9_\- ]{1,40}):", line.strip())
        if not match:
            continue
        person = match.group(1).strip()
        if person and person not in people:
            people.append(person)
    return people


def _extract_deadline(text: str) -> str:
    date_match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", text)
    if date_match:
        return date_match.group(0)
    phrase_match = re.search(
        r"\b(by|before|due)\s+([A-Za-z]+\s+\d{1,2}(?:,\s*\d{4})?)\b",
        text,
        flags=re.IGNORECASE,
    )
    if phrase_match:
        return phrase_match.group(2).strip()
    return ""


def _map_action(action: str) -> ActionType:
    normalized = action.strip().lower()
    if normalized in {"add"}:
        return "add"
    if normalized in {"remove"}:
        return "remove"
    if normalized in {"approve", "approved"}:
        return "approve"
    if normalized in {"review"}:
        return "review"
    return "change"


def _append_unique(values: list[str], value: str) -> None:
    clean = value.strip()
    if clean and clean not in values:
        values.append(clean)


class ArchitecturalMeetingIntelligenceEngine:
    def __init__(self) -> None:
        self._parser = ArchitecturalNLPParser()
        self._glossary = get_project_glossary()

    def transform(
        self,
        transcript: str,
        *,
        available_spaces: list[str] | None = None,
        project_glossary: dict | None = None,
        past_meeting_summaries: list[str] | None = None,
        bim_element_references: list[str] | None = None,
    ) -> StructuredMeetingIntelligence:
        del project_glossary, past_meeting_summaries, bim_element_references

        spaces = available_spaces or list(self._glossary.space_aliases.keys())
        cleaned = _normalize_unit_tokens(correct_transcript_with_reference(transcript, spaces))
        changes = self._parser.parse_transcript(
            transcript_text=cleaned,
            project_id="project_alpha",
            meeting_id="meeting_structured",
            available_spaces=spaces,
        )

        entities: list[StructuredEntity] = []
        actions: list[StructuredAction] = []
        decisions: list[str] = []
        risks: list[str] = []
        open_questions: list[str] = []
        design_changes: list[str] = []

        for person in _extract_people_from_transcript(cleaned):
            entities.append(StructuredEntity(type="person", value=person, confidence=0.95))

        for change in changes:
            confidence = max(0.0, min(1.0, float(change.confidence)))

            if change.space and change.space != "Unknown":
                entities.append(StructuredEntity(type="space", value=change.space, confidence=confidence))
            if change.element_type:
                entities.append(StructuredEntity(type="element", value=change.element_type, confidence=confidence))
            material = str(change.extracted_properties.get("new_material") or "").strip()
            if material:
                entities.append(StructuredEntity(type="material", value=material, confidence=confidence))

            owner = (change.speaker or "").strip()
            details = _normalize_unit_tokens(change.description)
            deadline = _extract_deadline(details)
            action_item = StructuredAction(
                action=_map_action(change.action),
                target=change.element_type or "",
                space="" if change.space == "Unknown" else (change.space or ""),
                details=details,
                owner=owner,
                deadline=deadline,
                confidence=confidence,
            )
            actions.append(action_item)
            _append_unique(design_changes, details)

        for line in cleaned.splitlines():
            sentence = line.strip()
            lowered = sentence.lower()
            if not sentence:
                continue
            if "?" in sentence or "clarify" in lowered or "unclear" in lowered:
                _append_unique(open_questions, sentence)
            if "risk" in lowered or "clash" in lowered or "conflict" in lowered or "issue" in lowered:
                _append_unique(risks, sentence)
            if "decided" in lowered or "approved" in lowered or "we will" in lowered:
                _append_unique(decisions, sentence)

        confidence_score = round(mean([action.confidence for action in actions]), 2) if actions else 0.0
        if confidence_score < 0.75:
            _append_unique(open_questions, "Manual review required: confidence_score below 0.75")

        result = StructuredMeetingIntelligence(
            transcript_cleaned=cleaned,
            entities=entities,
            actions=actions,
            decisions=decisions,
            risks=risks,
            open_questions=open_questions,
            design_changes=design_changes,
            confidence_score=confidence_score,
        )

        return self._ensure_valid_output(result)

    def _ensure_valid_output(self, result: StructuredMeetingIntelligence) -> StructuredMeetingIntelligence:
        for _ in range(2):
            try:
                payload = result.model_dump(mode="json")
                serialized = json.dumps(payload, ensure_ascii=False)
                parsed = json.loads(serialized)
                return StructuredMeetingIntelligence.model_validate(parsed)
            except Exception:
                result = StructuredMeetingIntelligence(
                    transcript_cleaned=result.transcript_cleaned,
                    entities=result.entities,
                    actions=result.actions,
                    decisions=result.decisions,
                    risks=result.risks,
                    open_questions=result.open_questions,
                    design_changes=result.design_changes,
                    confidence_score=result.confidence_score,
                )

        return StructuredMeetingIntelligence(
            transcript_cleaned=result.transcript_cleaned,
            entities=[],
            actions=[],
            decisions=[],
            risks=[],
            open_questions=["Manual review required: output regeneration failed"],
            design_changes=[],
            confidence_score=0.0,
        )
