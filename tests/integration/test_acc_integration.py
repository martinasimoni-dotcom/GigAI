"""
Integration tests — Autodesk Construction Cloud (ACC) API.
Requires: .env with ACC_CLIENT_ID, ACC_CLIENT_SECRET, ACC_PROJECT_ID
Tests skip automatically if credentials are absent.
Run: pytest tests/integration/test_acc_integration.py -m integration -v
"""
import os

from dotenv import load_dotenv

load_dotenv()

import pytest  # noqa: E402

pytestmark = [pytest.mark.integration, pytest.mark.requires_api]


class TestACCIntegration:
    """Real ACC API integration tests — skipped when ACC credentials are absent."""

    def test_acc_token_acquisition(self):
        """Acquire a real ACC OAuth2 2-legged token."""
        if not os.getenv("ACC_CLIENT_ID"):
            pytest.skip(
                "ACC_CLIENT_ID not set — real ACC credentials required for integration tests"
            )
        if not os.getenv("ACC_CLIENT_SECRET"):
            pytest.skip(
                "ACC_CLIENT_SECRET not set — real ACC credentials required for integration tests"
            )

        from src.shared.clients.acc import _get_acc_token  # lazy import

        token = _get_acc_token()
        assert token is not None
        assert len(token) > 10, f"Expected a real token (len > 10), got: {token!r}"

    def test_acc_get_floor_plan_returns_units(self):
        """Fetch floor plan from ACC Locations API for the demo project."""
        if not os.getenv("ACC_CLIENT_ID"):
            pytest.skip(
                "ACC_CLIENT_ID not set — real ACC credentials required for integration tests"
            )
        project_id = os.getenv("ACC_PROJECT_ID")
        if not project_id:
            pytest.skip(
                "ACC_PROJECT_ID not set — project ID required to fetch floor plan"
            )

        from src.shared.clients.acc import get_floor_plan  # lazy import

        result = get_floor_plan(project_id=project_id, location_query="3rd Floor")

        assert isinstance(result, dict), f"Expected dict response from ACC, got: {type(result)}"
        # Result should have project_id and nodes keys from the ACC Locations API response
        assert "project_id" in result or "nodes" in result or "source" in result, (
            f"Expected ACC floor plan dict with standard keys, got: {list(result.keys())}"
        )

    def test_acc_create_issue_succeeds(self):
        """Create a real ACC issue (tagged as integration test data — safe to delete)."""
        if not os.getenv("ACC_CLIENT_ID"):
            pytest.skip(
                "ACC_CLIENT_ID not set — real ACC credentials required for integration tests"
            )
        project_id = os.getenv("ACC_PROJECT_ID")
        if not project_id:
            pytest.skip(
                "ACC_PROJECT_ID not set — project ID required to create issue"
            )
        container_id = os.getenv("ACC_CONTAINER_ID")
        if not container_id:
            pytest.skip(
                "ACC_CONTAINER_ID not set — issues container ID required to create issue"
            )

        from src.shared.clients.acc import create_issue  # lazy import

        result = create_issue(
            project_id=project_id,
            container_id=container_id,
            title="Integration Test Issue — DELETE ME",
            description=(
                "Created by tests/integration/test_acc_integration.py — safe to delete. "
                "This is automated integration test data from GigAI."
            ),
        )

        assert isinstance(result, dict), f"Expected dict response from ACC, got: {type(result)}"
        # ACC creates an issue and returns a dict with an ID field
        has_id = "id" in result or "issue_id" in result
        assert has_id, (
            f"Expected ACC issue response to have 'id' or 'issue_id' key, got: {list(result.keys())}"
        )
