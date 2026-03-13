"""Tests for the feedback loop (record_decision)."""
import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

# Ensure settings can load before any src.shared.db imports happen
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("VOYAGE_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")

from src.shared.models.proposals import Proposal


def _make_proposal():
    return Proposal(
        proposal_id="prop-001",
        event_id="evt-001",
        alert={"title": "Window Substitution"},
        actions=[],
        confidence_score=0.85,
        recommendation="accept",
        created_at=datetime(2026, 3, 13, 12, 0, 0),
    )


def test_record_decision_inserts_and_embeds():
    proposal = _make_proposal()
    mock_conn = MagicMock()

    with patch("src.output.feedback.feedback_loop.postgres.get_connection", return_value=mock_conn) as mock_get, \
         patch("src.output.feedback.feedback_loop.postgres.release_connection") as mock_release, \
         patch("src.output.feedback.feedback_loop.postgres.execute") as mock_execute, \
         patch("src.output.feedback.feedback_loop.embed_and_store") as mock_embed:

        from src.output.feedback.feedback_loop import record_decision
        record_decision("prop-001", "accept", "looks good", proposal)

        mock_get.assert_called_once()
        mock_release.assert_called_once_with(mock_conn)
        assert mock_execute.call_count == 2

        ddl_call = mock_execute.call_args_list[0]
        assert "CREATE TABLE IF NOT EXISTS decisions" in ddl_call[0][1]

        insert_call = mock_execute.call_args_list[1]
        assert "INSERT INTO decisions" in insert_call[0][1]
        insert_params = insert_call[0][2]
        assert insert_params[0] == "prop-001"
        assert insert_params[2] == "accept"

        mock_embed.assert_called_once()
        embed_call = mock_embed.call_args
        assert embed_call[1].get("source") == "decisions"
        assert "prop-001" in embed_call[0][0][0]


def test_record_decision_releases_on_exception():
    proposal = _make_proposal()
    mock_conn = MagicMock()

    with patch("src.output.feedback.feedback_loop.postgres.get_connection", return_value=mock_conn), \
         patch("src.output.feedback.feedback_loop.postgres.release_connection") as mock_release, \
         patch("src.output.feedback.feedback_loop.postgres.execute", side_effect=Exception("db error")), \
         patch("src.output.feedback.feedback_loop.embed_and_store"):

        from src.output.feedback.feedback_loop import record_decision
        with pytest.raises(Exception, match="db error"):
            record_decision("prop-001", "accept", None, proposal)

        mock_release.assert_called_once_with(mock_conn)
