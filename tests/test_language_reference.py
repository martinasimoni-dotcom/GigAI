from gigai.language_reference import correct_transcript_with_reference, normalize_speech_text
from gigai.voice import build_voice_focus_payload


def test_reference_correction_for_noisy_architecture_phrase() -> None:
    corrected = correct_transcript_with_reference(
        transcript="fix stdo unet 404 kitchan layaout and tolet optons",
        available_spaces=["Studio Unit 404", "Office Unit 401"],
    )

    assert "studio" in corrected
    assert "unit" in corrected
    assert "404" in corrected


def test_normalize_speech_text_collapses_spoken_digits() -> None:
    normalized = normalize_speech_text("mark studio unit five zero four")

    assert "504" in normalized
    assert "five" not in normalized


def test_build_voice_payload_applies_reference_correction() -> None:
    payload = {
        "projectId": "project_alpha",
        "transcript": "fix stdo unet 404 kitchan layaout",
        "available_spaces": ["Studio Unit 404", "Office Unit 401"],
    }

    normalized = build_voice_focus_payload(payload)

    assert "transcript_original" in normalized
    assert "transcript_corrected" in normalized
    assert "studio" in normalized["meeting_utterance"].lower()
    assert "404" in normalized["meeting_utterance"]


def test_build_voice_payload_understands_spoken_room_digits() -> None:
    payload = {
        "projectId": "project_alpha",
        "transcript": "mark studio unit five zero four",
        "available_spaces": ["104 - Pocket Park", "504 - Studio Unit", "406 - Two Story Studio Unit"],
    }

    normalized = build_voice_focus_payload(payload)

    assert normalized["llm_space_name"] == "504 - Studio Unit"
    assert "504" in normalized["meeting_utterance"]


def test_build_voice_payload_prefers_visible_space_decoder_for_number_miss() -> None:
    payload = {
        "projectId": "project_alpha",
        "transcript": "find 104",
        "available_spaces": ["104 - Pocket Park", "504 - Studio Unit", "406 - Two Story Studio Unit"],
        "visible_spaces": ["504 - Studio Unit", "406 - Two Story Studio Unit"],
    }

    normalized = build_voice_focus_payload(payload)

    assert normalized["llm_space_name"] == "504 - Studio Unit"
    assert normalized["llm_reason"] == "llm_visible_space_decoder_match"
    assert normalized["meeting_utterance"] == "find 104"


def test_build_voice_payload_extracts_structured_architectural_change() -> None:
    payload = {
        "projectId": "project_alpha",
        "transcript": "move the wall 300mm because east elevater loby needs more clearance",
        "available_spaces": ["East Elevator Lobby", "West Lobby"],
    }

    normalized = build_voice_focus_payload(payload)

    assert normalized["building_element"] == "wall"
    assert normalized["issue"].lower().startswith("move wall 300mm")
    assert normalized["architectural_properties"] == {"distance": "300mm"}
    assert normalized["llm_space_name"] == "East Elevator Lobby"


def test_build_voice_payload_rejects_garbage_space_guess() -> None:
    payload = {
        "projectId": "project_alpha",
        "transcript": "you hope the week before you do for me change until now",
        "available_spaces": ["104 - Pocket Park", "504 - Studio Unit", "406 - Two Story Studio Unit"],
    }

    normalized = build_voice_focus_payload(payload)

    assert "llm_space_name" not in normalized
    assert "space_name" not in normalized
