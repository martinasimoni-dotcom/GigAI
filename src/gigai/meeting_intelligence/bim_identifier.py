"""
BIM Element Identifier

Maps architectural changes to BIM elements in Revit:
- Identifies spaces (rooms) referenced in meetings
- Finds associated elements (windows, doors, walls)
- Extracts element properties
- Cross-references with glossary
"""

import json
import logging
from pathlib import Path
from typing import Optional
from difflib import SequenceMatcher

from .models import ArchitecturalChange, BIMElement

logger = logging.getLogger(__name__)


class BIMElementIdentifier:
    """
    Identifies BIM elements based on architectural changes.
    Uses Glossary for space aliases and mock BIM data for MVP.
    """

    def __init__(self):
        """Initialize identifier with BIM data"""
        self.bim_data = self._load_mock_bim_data()
        self.space_mapping = self._build_space_mapping()

    def _load_mock_bim_data(self) -> dict:
        """
        Load or create mock BIM model data for testing.
        In production, would query Revit via API.
        """
        return {
            "spaces": {
                "studio_504": {
                    "element_id": "room_001",
                    "name": "Studio Unit 504",
                    "level": "Level 05",
                    "aliases": ["Studio 504", "Unit 504", "504"],
                    "elements": {
                        "windows": ["window_501", "window_502"],
                        "doors": ["door_501"],
                        "walls": ["wall_501", "wall_502"],
                    },
                },
                "corridor_b": {
                    "element_id": "room_002",
                    "name": "Corridor B",
                    "level": "Level 05",
                    "aliases": ["Corridor B", "Corr B", "Hallway B"],
                    "elements": {
                        "windows": [],
                        "doors": ["door_101", "door_102"],
                        "walls": ["wall_301", "wall_302"],
                    },
                },
                "lobby": {
                    "element_id": "room_003",
                    "name": "Lobby",
                    "level": "Level 00",
                    "aliases": ["Main Lobby", "Entry Lobby"],
                    "elements": {
                        "windows": ["window_001", "window_002", "window_003"],
                        "doors": ["door_001"],
                        "walls": ["wall_001"],
                    },
                },
            },
            "elements": {
                "window_501": {
                    "element_id": "window_501",
                    "type": "window",
                    "space": "Studio 504",
                    "family": "Fixed Window",
                    "symbol": "1200x1500",
                    "properties": {"width": 1.2, "height": 1.5},
                    "mark": "W-101",
                    "level": "Level 05",
                },
                "window_502": {
                    "element_id": "window_502",
                    "type": "window",
                    "space": "Studio 504",
                    "family": "Fixed Window",
                    "symbol": "1000x1500",
                    "properties": {"width": 1.0, "height": 1.5},
                    "mark": "W-102",
                    "level": "Level 05",
                },
                "door_501": {
                    "element_id": "door_501",
                    "type": "door",
                    "space": "Studio 504",
                    "family": "Single Interior Door",
                    "symbol": "900x2100",
                    "properties": {"width": 0.9, "height": 2.1},
                    "mark": "D-501",
                    "level": "Level 05",
                },
                "wall_501": {
                    "element_id": "wall_501",
                    "type": "wall",
                    "space": "Studio 504",
                    "family": "Interior Partition",
                    "properties": {"thickness": 0.15},
                    "mark": "W-01",
                    "level": "Level 05",
                },
            },
        }

    def _build_space_mapping(self) -> dict:
        """Build mapping from space names and aliases to element IDs"""
        mapping = {}

        for space_key, space_data in self.bim_data["spaces"].items():
            # Add main name
            mapping[space_data["name"].lower()] = space_key

            # Add aliases
            for alias in space_data.get("aliases", []):
                mapping[alias.lower()] = space_key

        return mapping

    def find_elements_for_change(self, change: ArchitecturalChange) -> list[BIMElement]:
        """
        Find BIM elements referenced in an architectural change.

        Args:
            change: Detected architectural change

        Returns:
            List of affected BIM elements
        """
        elements = []

        # 1. Find the space
        space_key = self._find_space(change.space)
        if not space_key:
            logger.warning(f"Could not find space: {change.space}")
            return []

        space_data = self.bim_data["spaces"].get(space_key, {})
        space_element_id = space_data.get("element_id")

        # 2. Get elements of the affected type in that space
        element_type = change.element_type.lower()
        element_ids = []

        if element_type == "room" or element_type == "space":
            # Return room itself
            element_ids = [space_element_id]
        else:
            # Get specific element type
            element_category = self._map_element_type_to_category(element_type)
            element_ids = space_data.get("elements", {}).get(element_category, [])

        # 3. Create BIMElement objects
        for elem_id in element_ids:
            elem_data = self.bim_data["elements"].get(elem_id)
            if elem_data:
                bim_elem = BIMElement(
                    element_id=elem_data["element_id"],
                    element_type=elem_data.get("type", element_type),
                    space_name=space_data.get("name", change.space),
                    space_id=space_element_id,
                    family=elem_data.get("family"),
                    symbol=elem_data.get("symbol"),
                    current_properties=elem_data.get("properties", {}),
                    parameters={"Mark": elem_data.get("mark"), "Comments": ""},
                    level=elem_data.get("level"),
                )
                elements.append(bim_elem)

        logger.info(f"Found {len(elements)} BIM elements for {change.space}")
        return elements

    def find_element_by_id(self, element_id: str) -> Optional[BIMElement]:
        """Get BIM element by its Revit ElementId"""
        elem_data = self.bim_data["elements"].get(element_id)
        if not elem_data:
            return None

        # Find parent space
        space_name = elem_data.get("space", "Unknown")
        space_key = self._find_space(space_name)
        space_data = self.bim_data["spaces"].get(space_key, {})

        return BIMElement(
            element_id=elem_data["element_id"],
            element_type=elem_data.get("type"),
            space_name=space_name,
            space_id=space_data.get("element_id"),
            family=elem_data.get("family"),
            current_properties=elem_data.get("properties", {}),
            parameters={"Mark": elem_data.get("mark")},
            level=elem_data.get("level"),
        )

    def find_elements_in_space(self, space_name: str) -> list[BIMElement]:
        """Get all elements in a space"""
        space_key = self._find_space(space_name)
        if not space_key:
            return []

        space_data = self.bim_data["spaces"][space_key]
        elements = []

        for element_type_plural, element_ids in space_data.get("elements", {}).items():
            for elem_id in element_ids:
                elem_data = self.bim_data["elements"].get(elem_id)
                if elem_data:
                    elements.append(
                        BIMElement(
                            element_id=elem_id,
                            element_type=elem_data.get("type"),
                            space_name=space_data["name"],
                            space_id=space_data["element_id"],
                            family=elem_data.get("family"),
                        )
                    )

        return elements

    def get_element_properties(self, element_id: str) -> Optional[BIMElement]:
        """Get properties for an element"""
        return self.find_element_by_id(element_id)

    def _find_space(self, space_name: str) -> Optional[str]:
        """
        Find space key using fuzzy matching.
        Returns space_key if found, None otherwise.
        """
        space_lower = space_name.lower()

        # Exact match
        if space_lower in self.space_mapping:
            return self.space_mapping[space_lower]

        # Fuzzy match
        best_match = None
        best_score = 0.6  # Minimum similarity threshold

        for space_key, aliases in self._get_all_space_names().items():
            for alias in aliases:
                score = SequenceMatcher(None, space_lower, alias.lower()).ratio()
                if score > best_score:
                    best_score = score
                    best_match = space_key

        return best_match

    def _get_all_space_names(self) -> dict:
        """Get all space names and aliases"""
        all_names = {}

        for space_key, space_data in self.bim_data["spaces"].items():
            all_names[space_key] = [space_data["name"]] + space_data.get("aliases", [])

        return all_names

    def _map_element_type_to_category(self, element_type: str) -> str:
        """Map element type to BIM data category"""
        element_type_lower = element_type.lower()

        mapping = {
            "window": "windows",
            "door": "doors",
            "wall": "walls",
            "stair": "stairs",
            "column": "columns",
            "floor": "floors",
            "ceiling": "ceilings",
        }

        return mapping.get(element_type_lower, "elements")

    def export_bim_data_to_json(self, output_path: str) -> bool:
        """Export BIM data to JSON file (for testing)"""
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(self.bim_data, f, indent=2)
            logger.info(f"BIM data exported to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error exporting BIM data: {e}")
            return False

    def import_bim_data_from_json(self, input_path: str) -> bool:
        """Import BIM data from JSON file"""
        try:
            with open(input_path, "r", encoding="utf-8") as f:
                self.bim_data = json.load(f)
            self.space_mapping = self._build_space_mapping()
            logger.info(f"BIM data imported from {input_path}")
            return True
        except Exception as e:
            logger.error(f"Error importing BIM data: {e}")
            return False

    def refresh_from_revit(self) -> bool:
        """
        In production: Refresh BIM data from live Revit model
        For MVP: Use mock data
        """
        logger.info("Refreshing BIM data from Revit (mock data in MVP)")
        # This would call Revit API in production
        return True
