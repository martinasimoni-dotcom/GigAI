"""
Unit tests for ACC API client (src/shared/clients/acc.py).

Tests mock urllib.request.urlopen and env vars to avoid real HTTP calls.
No ACC credentials are required.
"""
import json
import sys
import time
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

IMPL_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "src/shared/clients/acc.py"
)
IMPL_AVAILABLE = IMPL_PATH.exists() and IMPL_PATH.stat().st_size > 10
pytestmark = pytest.mark.skipif(
    not IMPL_AVAILABLE, reason="acc.py not yet implemented"
)


def _make_urlopen_response(body: dict | list):
    """Create a mock context-manager response for urllib.request.urlopen."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(body).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


@pytest.fixture(autouse=True)
def _reset_token_cache():
    """Clear the in-process token cache before each test."""
    import src.shared.clients.acc as acc_mod
    acc_mod._token_cache.clear()
    yield
    acc_mod._token_cache.clear()


# ---------------------------------------------------------------------------
# Token acquisition
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_acc_token_raises_when_credentials_missing(monkeypatch):
    """_get_acc_token() raises RuntimeError when ACC_CLIENT_ID is not set."""
    import src.shared.clients.acc as acc_mod

    monkeypatch.delenv("ACC_CLIENT_ID", raising=False)
    monkeypatch.delenv("ACC_CLIENT_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="ACC_CLIENT_ID"):
        acc_mod._get_acc_token()


@pytest.mark.unit
def test_get_acc_token_acquires_token(monkeypatch):
    """_get_acc_token() fetches and caches a token via OAuth."""
    import src.shared.clients.acc as acc_mod

    monkeypatch.setenv("ACC_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("ACC_CLIENT_SECRET", "test-client-secret")

    token_resp = {"access_token": "test-token-abc", "expires_in": 3600}
    mock_resp = _make_urlopen_response(token_resp)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        token = acc_mod._get_acc_token()

    assert token == "test-token-abc"
    assert acc_mod._token_cache["access_token"] == "test-token-abc"


@pytest.mark.unit
def test_get_acc_token_returns_cached_token(monkeypatch):
    """_get_acc_token() returns cached token without HTTP call when still valid."""
    import src.shared.clients.acc as acc_mod

    monkeypatch.setenv("ACC_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("ACC_CLIENT_SECRET", "test-client-secret")

    # Pre-populate cache with a future expiry
    acc_mod._token_cache["access_token"] = "cached-token-xyz"
    acc_mod._token_cache["expires_at"] = time.time() + 7200

    with patch("urllib.request.urlopen") as mock_urlopen:
        token = acc_mod._get_acc_token()

    # Must NOT call urlopen — uses cache
    mock_urlopen.assert_not_called()
    assert token == "cached-token-xyz"


# ---------------------------------------------------------------------------
# get_floor_plan
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_floor_plan_returns_nodes(monkeypatch):
    """get_floor_plan() returns a dict with project_id, tree_id, nodes, source."""
    import src.shared.clients.acc as acc_mod

    monkeypatch.setenv("ACC_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("ACC_CLIENT_SECRET", "test-client-secret")

    # First call: token; second: trees; third: nodes
    trees_resp = {"results": [{"id": "tree-001", "name": "Location Tree"}]}
    nodes_resp = {"results": [
        {"id": "node-1", "name": "3rd Floor"},
        {"id": "node-2", "name": "2nd Floor"},
    ]}

    call_count = {"n": 0}
    responses = [
        {"access_token": "tok", "expires_in": 3600},
        trees_resp,
        nodes_resp,
    ]

    def _mock_urlopen(req):
        resp_data = responses[call_count["n"]]
        call_count["n"] += 1
        return _make_urlopen_response(resp_data)

    with patch("urllib.request.urlopen", side_effect=_mock_urlopen):
        result = acc_mod.get_floor_plan("proj-001")

    assert result["project_id"] == "proj-001"
    assert result["tree_id"] == "tree-001"
    assert len(result["nodes"]) == 2
    assert result["source"] == "acc_api"


@pytest.mark.unit
def test_get_floor_plan_filters_by_location_query(monkeypatch):
    """get_floor_plan() filters nodes by location_query (case-insensitive)."""
    import src.shared.clients.acc as acc_mod

    monkeypatch.setenv("ACC_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("ACC_CLIENT_SECRET", "test-client-secret")

    trees_resp = {"results": [{"id": "tree-001"}]}
    nodes_resp = {"results": [
        {"id": "node-1", "name": "3rd Floor"},
        {"id": "node-2", "name": "2nd Floor"},
        {"id": "node-3", "name": "3rd Floor Annex"},
    ]}

    call_count = {"n": 0}
    responses = [
        {"access_token": "tok", "expires_in": 3600},
        trees_resp,
        nodes_resp,
    ]

    def _mock_urlopen(req):
        resp_data = responses[call_count["n"]]
        call_count["n"] += 1
        return _make_urlopen_response(resp_data)

    with patch("urllib.request.urlopen", side_effect=_mock_urlopen):
        result = acc_mod.get_floor_plan("proj-001", location_query="3rd Floor")

    # Only nodes containing "3rd floor" (case-insensitive) are returned
    assert len(result["nodes"]) == 2
    for node in result["nodes"]:
        assert "3rd" in node["name"].lower()


@pytest.mark.unit
def test_get_floor_plan_empty_trees_returns_empty(monkeypatch):
    """get_floor_plan() returns empty nodes when no location trees exist."""
    import src.shared.clients.acc as acc_mod

    monkeypatch.setenv("ACC_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("ACC_CLIENT_SECRET", "test-client-secret")

    call_count = {"n": 0}
    responses = [
        {"access_token": "tok", "expires_in": 3600},
        {"results": []},  # empty trees
    ]

    def _mock_urlopen(req):
        resp_data = responses[call_count["n"]]
        call_count["n"] += 1
        return _make_urlopen_response(resp_data)

    with patch("urllib.request.urlopen", side_effect=_mock_urlopen):
        result = acc_mod.get_floor_plan("proj-001")

    assert result["nodes"] == []
    assert result["source"] == "acc_api"


# ---------------------------------------------------------------------------
# get_schedule_activities
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_schedule_activities_raises_without_account_id(monkeypatch):
    """get_schedule_activities() raises RuntimeError when ACC_ACCOUNT_ID is not set."""
    import src.shared.clients.acc as acc_mod

    monkeypatch.delenv("ACC_ACCOUNT_ID", raising=False)

    with pytest.raises(RuntimeError, match="ACC_ACCOUNT_ID"):
        acc_mod.get_schedule_activities("proj-001")


@pytest.mark.unit
def test_get_schedule_activities_returns_normalized_list(monkeypatch):
    """get_schedule_activities() returns normalized list of activity dicts."""
    import src.shared.clients.acc as acc_mod

    monkeypatch.setenv("ACC_CLIENT_ID", "test-id")
    monkeypatch.setenv("ACC_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("ACC_ACCOUNT_ID", "acct-001")

    schedule_resp = {
        "results": [
            {"name": "Window Installation", "startDate": "2026-04-01", "endDate": "2026-04-15", "location": "3rd Floor"},
        ]
    }

    call_count = {"n": 0}
    responses = [
        {"access_token": "tok", "expires_in": 3600},
        schedule_resp,
    ]

    def _mock_urlopen(req):
        resp_data = responses[call_count["n"]]
        call_count["n"] += 1
        return _make_urlopen_response(resp_data)

    with patch("urllib.request.urlopen", side_effect=_mock_urlopen):
        result = acc_mod.get_schedule_activities("proj-001")

    assert len(result) == 1
    assert result[0]["activity"] == "Window Installation"
    assert result[0]["date"] == "2026-04-01"
    assert result[0]["location"] == "3rd Floor"


# ---------------------------------------------------------------------------
# create_issue
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_create_issue_returns_issue_dict(monkeypatch):
    """create_issue() sends POST and returns the created issue dict."""
    import src.shared.clients.acc as acc_mod

    monkeypatch.setenv("ACC_CLIENT_ID", "test-id")
    monkeypatch.setenv("ACC_CLIENT_SECRET", "test-secret")

    issue_resp = {"data": {"id": "issue-001", "title": "Window Markup"}}

    call_count = {"n": 0}
    responses = [
        {"access_token": "tok", "expires_in": 3600},
        issue_resp,
    ]

    def _mock_urlopen(req):
        resp_data = responses[call_count["n"]]
        call_count["n"] += 1
        return _make_urlopen_response(resp_data)

    with patch("urllib.request.urlopen", side_effect=_mock_urlopen):
        result = acc_mod.create_issue(
            project_id="proj-001",
            container_id="container-001",
            title="Window Markup",
            description="Add markup annotation",
        )

    assert result["id"] == "issue-001"


# ---------------------------------------------------------------------------
# create_drawing_markup
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_create_drawing_markup_returns_markup_dict(monkeypatch):
    """create_drawing_markup() sends POST and returns markup dict."""
    import src.shared.clients.acc as acc_mod

    monkeypatch.setenv("ACC_CLIENT_ID", "test-id")
    monkeypatch.setenv("ACC_CLIENT_SECRET", "test-secret")

    markup_resp = {"data": {"id": "markup-001", "type": "markup"}}

    call_count = {"n": 0}
    responses = [
        {"access_token": "tok", "expires_in": 3600},
        markup_resp,
    ]

    def _mock_urlopen(req):
        resp_data = responses[call_count["n"]]
        call_count["n"] += 1
        return _make_urlopen_response(resp_data)

    with patch("urllib.request.urlopen", side_effect=_mock_urlopen):
        result = acc_mod.create_drawing_markup(
            project_id="proj-001",
            version_urn="urn:adsk.wipprod:fs.file:xxx",
            drawing_number="A-301",
            annotation_text="aluminum -> wood, W-301 to W-312",
        )

    assert result["id"] == "markup-001"


# ---------------------------------------------------------------------------
# send_acc_notification
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_send_acc_notification_returns_response(monkeypatch):
    """send_acc_notification() sends POST and returns response dict."""
    import src.shared.clients.acc as acc_mod

    monkeypatch.setenv("ACC_CLIENT_ID", "test-id")
    monkeypatch.setenv("ACC_CLIENT_SECRET", "test-secret")

    notif_resp = {"id": "notif-001", "status": "sent"}

    call_count = {"n": 0}
    responses = [
        {"access_token": "tok", "expires_in": 3600},
        notif_resp,
    ]

    def _mock_urlopen(req):
        resp_data = responses[call_count["n"]]
        call_count["n"] += 1
        return _make_urlopen_response(resp_data)

    with patch("urllib.request.urlopen", side_effect=_mock_urlopen):
        result = acc_mod.send_acc_notification(
            account_id="acct-001",
            project_id="proj-001",
            subject="Material Change Alert",
            body="Window substitution approved.",
            recipient_ids=["user-001", "user-002"],
        )

    assert result["id"] == "notif-001"
