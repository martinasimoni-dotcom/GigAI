from pathlib import Path

from gigai.llm import infer_space_focus
from gigai.orchestrator import get_cached_pipeline, process_webhook, resolve_approval_action
from gigai.voice import build_voice_focus_payload, extract_space_candidate


def test_auto_execution_for_low_risk_event() -> None:
    payload = {
        "id": "evt_test_low",
        "eventType": "issue.updated",
        "projectId": "project_alpha",
        "status": "open",
        "due_overrun_days": 0,
    }

    result = process_webhook(payload)

    assert result.action.mode == "auto"
    assert result.action.status == "executed"
    assert result.decision.risk_level in {"low", "medium"}


def test_manual_approval_for_high_risk_event() -> None:
    payload = {
        "id": "evt_test_high",
        "eventType": "issue.updated",
        "projectId": "project_alpha",
        "status": "blocked",
        "due_overrun_days": 5,
    }

    result = process_webhook(payload)

    assert result.action.mode == "manual"
    assert result.action.status == "approval_required"
    assert result.action.approval_id
    assert result.decision.risk_level == "high"
    assert result.context


def test_space_focus_detected_from_meeting_utterance() -> None:
    payload = {
        "id": "evt_test_space_focus",
        "type": "meeting.focus",
        "projectId": "project_alpha",
        "meeting_utterance": "Please focus on East Lobby and fix the open issue there",
        "available_spaces": ["West Lobby", "East Lobby", "Roof"],
        "status": "open",
        "due_overrun_days": 0,
    }

    result = process_webhook(payload)

    assert result.event.focus_space == "East Lobby"
    assert result.event.focus_reason == "meeting_utterance_match"
    assert result.decision.proposal == "focus_space_triage"
    assert any(
        item["ref"] == "bim:space:East Lobby" for item in result.decision.evidence
    )


def test_space_focus_detected_from_room_number_fallback() -> None:
    payload = {
        "id": "evt_test_room_root",
        "type": "meeting.focus",
        "projectId": "project_alpha",
        "meeting_utterance": "fix kitchen layout in stdo unet 404 and toilet same unit",
        "available_spaces": ["Studio Unit 404", "Office Unit 401", "Two Story Studio Unit 406"],
        "status": "open",
        "due_overrun_days": 0,
    }

    result = process_webhook(payload)

    assert result.event.focus_space == "Studio Unit 404"
    assert result.event.focus_reason in {"meeting_room_number_match", "llm_room_number_match", "llm_exact_phrase_match"}


def test_voice_command_extracts_space_candidate() -> None:
    transcript = "GigAI please focus on Room 204 and check the blocked issue"
    assert extract_space_candidate(transcript) == "Room 204"


def test_voice_command_extracts_find_candidate() -> None:
    transcript = "find 504"
    assert extract_space_candidate(transcript) == "504"


def test_voice_command_payload_without_space_catalog() -> None:
    payload = {
        "projectId": "project_alpha",
        "transcript": "Go to North Wing and review issue",
    }

    normalized = build_voice_focus_payload(payload)
    result = process_webhook(normalized)

    assert result.event.focus_space == "North Wing"
    assert result.event.focus_reason == "explicit_space_field"


def test_llm_layer_fuzzy_space_resolution() -> None:
    inference = infer_space_focus(
        transcript="please focus on east loby and fix issue",
        available_spaces=["West Lobby", "East Lobby", "Roof"],
    )

    assert inference.space_name == "East Lobby"
    assert inference.confidence >= 0.35
    assert inference.reason in {"llm_exact_phrase_match", "llm_semantic_fuzzy_match"}


def test_voice_command_payload_with_space_catalog_uses_llm_layer() -> None:
    payload = {
        "projectId": "project_alpha",
        "transcript": "go to east loby and check issue",
        "available_spaces": ["East Lobby", "West Lobby"],
    }

    normalized = build_voice_focus_payload(payload)
    result = process_webhook(normalized)

    assert result.event.focus_space == "East Lobby"
    assert result.event.focus_reason.startswith("llm_")


def test_voice_command_payload_with_catalog_falls_back_to_explicit_candidate() -> None:
    payload = {
        "projectId": "project_alpha",
        "transcript": "fix kitchen layout in studio unit 404 and toilet layout in same unit",
        "available_spaces": ["East Lobby", "West Lobby"],
    }

    normalized = build_voice_focus_payload(payload)
    result = process_webhook(normalized)

    assert result.event.focus_space.lower() in {"studio unit 404", "unit 404", "404"}
    assert result.event.focus_reason == "explicit_space_field"


def test_voice_command_payload_uses_parser_enrichment_for_issue_creation() -> None:
    payload = {
        "projectId": "project_alpha",
        "transcript": "move the wall 300mm because east elevater loby needs more clearance",
        "available_spaces": ["East Elevator Lobby", "West Lobby"],
    }

    normalized = build_voice_focus_payload(payload)
    result = process_webhook(normalized)

    assert normalized["building_element"] == "wall"
    assert normalized["issue"]
    assert result.event.focus_space == "East Elevator Lobby"
    assert result.decision.proposal == "create_issue_note"


def test_voice_command_payload_matches_spoken_room_digits() -> None:
    payload = {
        "projectId": "project_alpha",
        "transcript": "mark studio unit five zero four",
        "available_spaces": ["104 - Pocket Park", "504 - Studio Unit", "406 - Two Story Studio Unit"],
    }

    normalized = build_voice_focus_payload(payload)
    result = process_webhook(normalized)

    assert result.event.focus_space == "504 - Studio Unit"
    assert result.event.focus_reason in {"llm_exact_phrase_match", "llm_room_number_match"}


def test_voice_command_payload_prefers_visible_space_decoder_match() -> None:
    payload = {
        "projectId": "project_alpha",
        "transcript": "find 104",
        "available_spaces": ["104 - Pocket Park", "504 - Studio Unit", "406 - Two Story Studio Unit"],
        "visible_spaces": ["504 - Studio Unit", "406 - Two Story Studio Unit"],
    }

    normalized = build_voice_focus_payload(payload)
    result = process_webhook(normalized)

    assert result.event.focus_space == "504 - Studio Unit"
    assert result.event.focus_reason == "llm_visible_space_decoder_match"


def test_llm_architecture_synonym_resolution() -> None:
    inference = infer_space_focus(
        transcript="focus on lift lobby and add revision cloud",
        available_spaces=["East Elevator Lobby", "West Corridor"],
    )

    assert inference.space_name == "East Elevator Lobby"
    assert inference.reason in {"llm_exact_phrase_match", "llm_semantic_fuzzy_match"}


def test_llm_project_glossary_alias_resolution(scratch_dir: Path, monkeypatch) -> None:
    glossary_file = scratch_dir / "project_glossary.json"
    glossary_file.write_text(
        (
            "{"
            "\"term_normalization\": {\"atriom\": \"atrium\"},"
            "\"space_aliases\": {\"Design Atrium\": [\"design atrom\", \"atrium design\"]}"
            "}"
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("GIGAI_PROJECT_GLOSSARY", str(glossary_file))

    inference = infer_space_focus(
        transcript="please focus on design atrom and mark revision",
        available_spaces=["Design Atrium", "Main Corridor"],
    )

    assert inference.space_name == "Design Atrium"
    assert inference.reason in {"llm_glossary_alias_match", "llm_semantic_fuzzy_match"}


def test_llm_prefers_explicit_unit_number_match() -> None:
    inference = infer_space_focus(
        transcript="Fix kitchen layout in studio unit 404 and toilet layout in same unit",
        available_spaces=["101 - Cafe 101", "Studio Unit 404", "Office Unit 401"],
    )

    assert inference.space_name == "Studio Unit 404"
    assert inference.reason in {"llm_room_number_match", "llm_exact_phrase_match", "llm_semantic_fuzzy_match"}


def test_manual_approval_can_be_approved_and_cached() -> None:
    result = process_webhook(
        {
            "id": "evt_test_approve",
            "eventType": "issue.updated",
            "projectId": "project_alpha",
            "status": "blocked",
            "due_overrun_days": 5,
            "artifactId": "issue_approve_1",
        }
    )

    assert result.action.approval_id

    resolved = resolve_approval_action(
        result.action.approval_id,
        decision="approve",
        actor="pm_alice",
        note="looks good",
    )

    cached = get_cached_pipeline(result.event.event_id)

    assert resolved.status == "approved"
    assert resolved.action_status == "executed"
    assert cached is not None
    assert cached.action.status == "executed"


def test_missing_project_id_is_blocked() -> None:
    result = process_webhook(
        {
            "id": "evt_missing_project",
            "eventType": "issue.updated",
            "status": "open",
        }
    )

    assert "missing_project_id" in result.policy.blockers
    assert result.action.status == "approval_required"
