"""Tests for FastAPI routes."""
import asyncio
import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("VOYAGE_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.shared.models.proposals import Action, Proposal


def _make_proposal():
    return Proposal(
        proposal_id="prop-r-001",
        event_id="evt-r-001",
        alert={"title": "Test"},
        actions=[],
        confidence_score=0.75,
        recommendation="review",
        created_at=datetime(2026, 3, 13, 12, 0, 0),
    )


def _build_app():
    """Build a fresh FastAPI app with routes for each test."""
    import importlib
    import src.api.routes as routes_mod
    # Reset module-level state
    routes_mod._proposals.clear()
    routes_mod._proposal_objects.clear()

    app = FastAPI()
    app.include_router(routes_mod.router)
    return app


def test_health():
    app = _build_app()
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "version": "0.1.0"}


def test_get_proposals_empty():
    app = _build_app()
    client = TestClient(app)
    resp = client.get("/api/proposals")
    assert resp.status_code == 200
    assert resp.json() == []


def test_store_proposal_adds_and_notifies():
    import src.api.routes as routes_mod
    routes_mod._proposals.clear()
    routes_mod._proposal_objects.clear()
    proposal = _make_proposal()
    proposal_response = {"id": "prop-r-001", "recommendation": "review"}

    with patch("src.api.routes.notify_dashboard") as mock_notify:
        routes_mod.store_proposal(proposal, proposal_response)
        assert len(routes_mod._proposals) == 1
        assert routes_mod._proposals[0]["id"] == "prop-r-001"
        mock_notify.assert_called_once_with(proposal_response)


def test_get_proposals_after_store():
    import src.api.routes as routes_mod
    routes_mod._proposals.clear()
    routes_mod._proposal_objects.clear()
    proposal = _make_proposal()
    proposal_response = {"id": "prop-r-001", "recommendation": "review"}

    with patch("src.api.routes.notify_dashboard"):
        routes_mod.store_proposal(proposal, proposal_response)

    app = FastAPI()
    app.include_router(routes_mod.router)
    client = TestClient(app)
    resp = client.get("/api/proposals")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_decision_not_found():
    app = _build_app()
    client = TestClient(app)
    resp = client.post("/api/proposals/nonexistent/decision", json={"decision": "accept"})
    assert resp.status_code == 404


def test_decision_review():
    import src.api.routes as routes_mod
    routes_mod._proposals.clear()
    routes_mod._proposal_objects.clear()
    proposal = _make_proposal()
    proposal_response = {"id": "prop-r-001", "recommendation": "review"}

    with patch("src.api.routes.notify_dashboard"):
        routes_mod.store_proposal(proposal, proposal_response)

    app = FastAPI()
    app.include_router(routes_mod.router)
    client = TestClient(app)

    with patch("src.api.routes.record_decision") as mock_record, \
         patch("src.api.routes.execute_actions", new=AsyncMock()) as mock_gateway:
        resp = client.post(
            "/api/proposals/prop-r-001/decision",
            json={"decision": "review", "reason": "needs more info"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "recorded"
        mock_record.assert_called_once()
        mock_gateway.assert_not_called()  # Only called on "accept"


def test_decision_accept_runs_gateway():
    import src.api.routes as routes_mod
    routes_mod._proposals.clear()
    routes_mod._proposal_objects.clear()
    proposal = _make_proposal()
    proposal_response = {"id": "prop-r-001", "recommendation": "accept"}

    with patch("src.api.routes.notify_dashboard"):
        routes_mod.store_proposal(proposal, proposal_response)

    app = FastAPI()
    app.include_router(routes_mod.router)
    client = TestClient(app)

    mock_exec_result = MagicMock()
    with patch("src.api.routes.record_decision"), \
         patch("src.api.routes.execute_actions", new=AsyncMock(return_value=mock_exec_result)):
        resp = client.post(
            "/api/proposals/prop-r-001/decision",
            json={"decision": "accept"},
        )
        assert resp.status_code == 200
        assert resp.json()["decision"] == "accept"
