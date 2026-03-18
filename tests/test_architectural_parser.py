from gigai.meeting_intelligence import ArchitecturalNLPParser


def test_parser_loads_repository_vocabulary_file() -> None:
    parser = ArchitecturalNLPParser()

    assert parser.detect_action_type("align the wall with the grid") == "align"
    assert "fixture" in parser.detect_element_types("add a fixture in the lobby")


def test_parser_extracts_change_from_noisy_architectural_transcript() -> None:
    parser = ArchitecturalNLPParser()

    changes = parser.parse_transcript(
        "Architect_A: move the wall 300mm because east elevater loby needs more clearance",
        project_id="project_alpha",
        meeting_id="meet_001",
    )

    assert len(changes) == 1

    change = changes[0]
    assert change.speaker == "Architect_A"
    assert change.action == "move"
    assert change.element_type == "wall"
    assert change.space == "East Elevator Lobby"
    assert change.extracted_properties == {"distance": "300mm"}
