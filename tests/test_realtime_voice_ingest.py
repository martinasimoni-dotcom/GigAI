from __future__ import annotations

from gigai.coordination import CoordinationService
from gigai.coordination.models import RevitElementInput, TeamContact
from gigai.coordination.realtime import (
    RealTimeVoiceIngestService,
    VoiceStreamChunkRequest,
    VoiceStreamFinalizeRequest,
    VoiceStreamStartRequest,
)


def _build_elements(count: int) -> list[RevitElementInput]:
    return [
        RevitElementInput(
            element_id=f"win_{index:03d}",
            category="window",
            level="3rd Floor",
            material="aluminum",
        )
        for index in range(1, count + 1)
    ]


def test_stream_text_chunks_finalize_to_coordination_plan() -> None:
    ingest = RealTimeVoiceIngestService(CoordinationService())

    session = ingest.start_session(
        VoiceStreamStartRequest(
            project_id="project_alpha",
            drawing_id="A-301",
            available_revit_elements=_build_elements(15),
            team_contacts=[TeamContact(name="Alice", email="alice@example.com")],
        )
    )

    ingest.append_chunk(
        session.session_id,
        VoiceStreamChunkRequest(text_chunk="Change all 3rd floor windows"),
    )
    state = ingest.append_chunk(
        session.session_id,
        VoiceStreamChunkRequest(text_chunk="from aluminum to wood, around 12 units"),
    )

    assert state.chunk_count == 2
    assert "3rd floor" in state.transcript.lower()

    result = ingest.finalize(
        session.session_id,
        VoiceStreamFinalizeRequest(auto_accept=False, execute_actions=False),
    )

    assert result.plan.normalized_change.change_type == "material change"
    assert result.plan.normalized_change.quantity == 12
    assert len(result.plan.matched_targets) == 12
    assert result.plan.status == "pending"


def test_stream_auto_accept_executes_plan() -> None:
    ingest = RealTimeVoiceIngestService(CoordinationService())
    session = ingest.start_session(
        VoiceStreamStartRequest(
            project_id="project_alpha",
            available_revit_elements=_build_elements(12),
        )
    )

    ingest.append_chunk(
        session.session_id,
        VoiceStreamChunkRequest(
            text_chunk="Window material substitution 3rd floor windows aluminum to wood 12 units"
        ),
    )

    result = ingest.finalize(
        session.session_id,
        VoiceStreamFinalizeRequest(auto_accept=True, execute_actions=True, actor="pm_auto"),
    )

    assert result.plan.status == "executed"
    assert result.plan.execution_results
