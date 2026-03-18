"""
Architectural NLP Parser

Extracts design changes from meeting transcripts:
- Space identification (rooms, units, facades, etc.)
- Action type detection (resize, move, modify, add, remove, etc.)
- Design change extraction
- Affected element identification
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
import logging

from ..llm import LlmLayer  # Existing space inference
from ..language_reference import correct_transcript_with_reference
from ..glossary import get_project_glossary
from .models import ArchitecturalChange

logger = logging.getLogger(__name__)


class ArchitecturalNLPParser:
    """
    Parse transcripts for architectural design changes.
    Integrates with existing LLM and glossary systems.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize parser with architectural vocabulary.

        Args:
            config_path: Path to architectural_vocabulary.json
        """
        self.glossary = get_project_glossary()
        self.llm_layer = LlmLayer(self.glossary)

        # Load architectural vocabulary
        self.vocabulary = self._load_vocabulary(config_path)

    def _load_vocabulary(self, config_path: Optional[str]) -> dict:
        """Load architectural vocabulary from config file"""
        default_path = Path(__file__).resolve().parents[3] / "config" / "architectural_vocabulary.json"

        if config_path and Path(config_path).exists():
            vocab_path = Path(config_path)
        elif default_path.exists():
            vocab_path = default_path
        else:
            logger.warning("Architectural vocabulary file not found, using minimal vocabulary")
            return self._default_vocabulary()

        try:
            with open(vocab_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading vocabulary: {e}")
            return self._default_vocabulary()

    def _default_vocabulary(self) -> dict:
        """Default vocabulary if config file not found"""
        return {
            "actions": [
                {"action": "resize", "aliases": ["increase", "decrease", "expand", "shrink", "widen", "narrow"]},
                {"action": "move", "aliases": ["shift", "relocate", "reposition", "adjust position"]},
                {"action": "add", "aliases": ["create", "new", "insert", "install", "place"]},
                {"action": "remove", "aliases": ["delete", "eliminate", "take out", "remove"]},
                {"action": "modify", "aliases": ["change", "update", "alter", "adjust"]},
                {"action": "change_material", "aliases": ["use", "apply", "switch to", "replace with"]},
            ],
            "elements": [
                {"element": "window", "aliases": ["glass", "glazing", "fenestration", "opening"]},
                {"element": "door", "aliases": ["entrance", "exit", "opening", "access"]},
                {"element": "wall", "aliases": ["partition", "facade", "exterior", "boundary"]},
                {"element": "stair", "aliases": ["stairs", "staircase", "steps", "riser", "stairwell"]},
                {"element": "column", "aliases": ["post", "pillar", "support", "structural"]},
                {"element": "floor", "aliases": ["slab", "surface", "level"]},
                {"element": "ceiling", "aliases": ["soffit", "overhead", "top"]},
                {"element": "room", "aliases": ["space", "unit", "area"]},
            ],
            "properties": [
                {"property": "width", "aliases": ["w", "dimension", "span"]},
                {"property": "height", "aliases": ["h", "vertical"]},
                {"property": "depth", "aliases": ["d", "thickness"]},
                {"property": "material", "aliases": ["finish", "surface", "type"]},
                {"property": "color", "aliases": ["colour", "shade", "tone"]},
            ],
        }

    def parse_transcript(
        self,
        transcript_text: str,
        project_id: str,
        meeting_id: str,
        available_spaces: list[str] | None = None,
    ) -> list[ArchitecturalChange]:
        """
        Parse full meeting transcript for architectural changes.

        Args:
            transcript_text: Full meeting transcript
            project_id: Project identifier
            meeting_id: Meeting identifier

        Returns:
            List of detected architectural changes
        """
        changes = []
        available_spaces = available_spaces if available_spaces is not None else self._available_spaces()
        lines = transcript_text.split("\n")

        for idx, line in enumerate(lines):
            if not line.strip():
                continue

            # Extract speaker and text (assume format: "Speaker: text")
            speaker, text = self._parse_speaker_line(line)
            if not text:
                continue

            # Correct ASR errors using existing language reference
            corrected_text = correct_transcript_with_reference(text, available_spaces)

            # Detect changes in this utterance
            utterance_changes = self._extract_changes_from_utterance(
                corrected_text,
                speaker,
                project_id,
                meeting_id,
                timestamp=self._estimate_timestamp(idx, len(lines)),
                available_spaces=available_spaces,
            )

            changes.extend(utterance_changes)

        logger.info(f"Extracted {len(changes)} architectural changes from transcript")
        return changes

    def _parse_speaker_line(self, line: str) -> tuple[Optional[str], str]:
        """Extract speaker and text from transcript line"""
        # Format: "Speaker_Name: text here"
        match = re.match(r"^([A-Za-z0-9_\s]+):\s*(.+)$", line)
        if match:
            return match.group(1).strip(), match.group(2).strip()
        return None, line.strip()

    def _extract_changes_from_utterance(
        self,
        text: str,
        speaker: Optional[str],
        project_id: str,
        meeting_id: str,
        timestamp: str,
        available_spaces: list[str],
    ) -> list[ArchitecturalChange]:
        """Extract architectural changes from a single utterance"""
        changes = []

        # Pattern 1: "increase [element] [size/dimension]"
        pattern1 = r"(increase|expand|widen|enlarge)\s+(?:the\s+)?(\w+)(?:\s+(?:to|by)\s+([\d.]+\s*[a-z]+))?.*?(?:for|to)\s+([^.!?]+)"
        matches = re.finditer(pattern1, text, re.IGNORECASE)
        for match in matches:
            action_verb, element, dimension, reason = match.groups()
            action = self._normalize_action("resize")
            element_type = self._normalize_element(element)

            if action and element_type:
                change = ArchitecturalChange(
                    project=project_id,
                    space=self._extract_space(text, available_spaces),
                    element_type=element_type,
                    action=action,
                    description=f"{action_verb.capitalize()} {element} {f'to {dimension}' if dimension else ''} {reason if reason else ''}".strip(),
                    timestamp=datetime.fromisoformat(f"2026-03-15T{timestamp}"),
                    confidence=0.85,
                    speaker=speaker,
                    transcript_reference=timestamp,
                    extracted_properties={"target_dimension": dimension} if dimension else {},
                )
                changes.append(change)

        # Pattern 2: "move [element] [direction/distance]"
        pattern2 = r"(move|shift|relocate|reposition)\s+(?:the\s+)?(\w+)(?:\s+(\d+\s*(?:mm|m|cm)))?.*?(?:to|for|because)\s+([^.!?]+)"
        matches = re.finditer(pattern2, text, re.IGNORECASE)
        for match in matches:
            action_verb, element, distance, reason = match.groups()
            action = self._normalize_action("move")
            element_type = self._normalize_element(element)

            if action and element_type:
                change = ArchitecturalChange(
                    project=project_id,
                    space=self._extract_space(text, available_spaces),
                    element_type=element_type,
                    action=action,
                    description=f"{action_verb.capitalize()} {element} {f'{distance}' if distance else ''} {reason if reason else ''}".strip(),
                    timestamp=datetime.fromisoformat(f"2026-03-15T{timestamp}"),
                    confidence=0.82,
                    speaker=speaker,
                    transcript_reference=timestamp,
                    extracted_properties={"distance": distance} if distance else {},
                )
                changes.append(change)

        # Pattern 3: "change [element] material/color to [value]"
        pattern3 = r"(change|switch|replace)\s+(?:the\s+)?(\w+)\s+(?:material|color|colour|finish)\s+to\s+(\w+(?:\s+\w+)*)"
        matches = re.finditer(pattern3, text, re.IGNORECASE)
        for match in matches:
            action_verb, element, new_value = match.groups()
            action = self._normalize_action("change_material")
            element_type = self._normalize_element(element)

            if action and element_type:
                change = ArchitecturalChange(
                    project=project_id,
                    space=self._extract_space(text, available_spaces),
                    element_type=element_type,
                    action=action,
                    description=f"Change {element} material/color to {new_value}",
                    timestamp=datetime.fromisoformat(f"2026-03-15T{timestamp}"),
                    confidence=0.80,
                    speaker=speaker,
                    transcript_reference=timestamp,
                    extracted_properties={"new_material": new_value},
                )
                changes.append(change)

        # Pattern 4: "add [element] to [space]"
        pattern4 = r"(add|create|install|place)\s+(?:a\s+)?(?:new\s+)?(\w+)(?:\s+to|in|at)\s+(?:the\s+)?([^.!?]+)"
        matches = re.finditer(pattern4, text, re.IGNORECASE)
        for match in matches:
            action_verb, element, location = match.groups()
            action = self._normalize_action("add")
            element_type = self._normalize_element(element)

            if action and element_type:
                change = ArchitecturalChange(
                    project=project_id,
                    space=location.strip(),
                    element_type=element_type,
                    action=action,
                    description=f"Add new {element} to {location}",
                    timestamp=datetime.fromisoformat(f"2026-03-15T{timestamp}"),
                    confidence=0.78,
                    speaker=speaker,
                    transcript_reference=timestamp,
                )
                changes.append(change)

        return changes

    def _extract_space(self, text: str, available_spaces: list[str]) -> str:
        """Extract space name from utterance using LLM layer"""
        inferred_space = self.llm_layer.infer_space(text, available_spaces)
        if inferred_space.space_name:
            return inferred_space.space_name
        return "Unknown"

    def _available_spaces(self) -> list[str]:
        """Build canonical space candidates from glossary and vocabulary."""
        spaces: list[str] = []

        for canonical in self.glossary.space_aliases.keys():
            label = self._display_space_name(canonical)
            if label not in spaces:
                spaces.append(label)

        for entry in self.vocabulary.get("spaces", []):
            if not isinstance(entry, dict):
                continue
            for example in entry.get("examples", []):
                if not isinstance(example, str) or not example.strip():
                    continue
                label = self._display_space_name(example)
                if label not in spaces:
                    spaces.append(label)

        return spaces

    def _display_space_name(self, value: str) -> str:
        return " ".join(token.capitalize() if token.isalpha() else token for token in value.strip().split())

    def _normalize_action(self, action: str) -> Optional[str]:
        """Normalize action to standard form"""
        action_lower = action.lower()

        for vocab_action in self.vocabulary["actions"]:
            if action_lower == vocab_action["action"].lower():
                return vocab_action["action"]

            for alias in vocab_action.get("aliases", []):
                if action_lower == alias.lower():
                    return vocab_action["action"]

        return None

    def _normalize_element(self, element: str) -> Optional[str]:
        """Normalize element type to standard form"""
        element_lower = element.lower()

        for vocab_element in self.vocabulary["elements"]:
            if element_lower == vocab_element["element"].lower():
                return vocab_element["element"]

            for alias in vocab_element.get("aliases", []):
                if element_lower == alias.lower():
                    return vocab_element["element"]

        return None

    def _estimate_timestamp(self, line_index: int, total_lines: int) -> str:
        """Estimate timestamp based on line position in transcript"""
        # Rough estimate: distribute meeting duration across lines
        meeting_duration = 45  # minutes, default
        minutes = int((line_index / total_lines) * meeting_duration)
        hours = 10  # Assume meeting starts at 10:00 AM
        seconds = (line_index % 60)

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def detect_action_type(self, text: str) -> Optional[str]:
        """Detect primary action type in text"""
        text_lower = text.lower()

        for vocab_action in self.vocabulary["actions"]:
            for alias in [vocab_action["action"]] + vocab_action.get("aliases", []):
                if alias.lower() in text_lower:
                    return vocab_action["action"]

        return None

    def detect_element_types(self, text: str) -> list[str]:
        """Detect all mentioned element types in text"""
        elements = []
        text_lower = text.lower()

        for vocab_element in self.vocabulary["elements"]:
            for check in [vocab_element["element"]] + vocab_element.get("aliases", []):
                if check.lower() in text_lower and vocab_element["element"] not in elements:
                    elements.append(vocab_element["element"])

        return elements

    def extract_property_values(self, text: str) -> dict[str, str]:
        """Extract dimension, material, and other property values"""
        properties = {}

        # Extract dimensions (e.g., "2400mm", "2.4m", "8 feet")
        dim_pattern = r"(\d+(?:\.\d+)?)\s*(mm|cm|m|feet|ft|')"
        for match in re.finditer(dim_pattern, text, re.IGNORECASE):
            value, unit = match.groups()
            properties["dimension"] = f"{value}{unit}"

        # Extract colors/materials
        materials = ["aluminum", "glass", "brick", "concrete", "timber", "wood", "steel", "granite", "marble"]
        for material in materials:
            if material.lower() in text.lower():
                properties["material"] = material

        return properties
