"""
Unit test stubs for scripts/seed_knowledge_folder.py — Wave 0 scaffold.

Purpose: Establish the Nyquist-compliant test scaffold before any content or
implementation is written. All subsequent waves have an automated verify command
to run against.

Requirements: KF-01, KF-02, KF-03, KF-04, KF-05
"""
import json
import sys
from unittest.mock import MagicMock, patch, call

import pytest
import yaml

# ---------------------------------------------------------------------------
# Wave 0 import-guard: file is always collectable even before implementation
# ---------------------------------------------------------------------------
try:
    from scripts.seed_knowledge_folder import (
        chunk_markdown_by_sections,
        chunk_team_directory,
        chunk_rules,
        chunk_historical_patterns,
        seed,
    )
    IMPL_AVAILABLE = True
except ImportError:
    IMPL_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not IMPL_AVAILABLE,
    reason="seed_knowledge_folder.py not yet implemented",
)


# ---------------------------------------------------------------------------
# Autouse fixture: set env vars + pop sys.modules before each test
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _setup_env(monkeypatch):
    """Set required env vars and clear cached module imports for isolation."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("VOYAGE_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    # Pop any cached module imports that transitively load config.settings
    for mod in [
        "scripts.seed_knowledge_folder",
        "src.shared.db.vector_store",
        "src.shared.db.postgres",
        "src.shared.llm.voyage",
        "src.shared.db",
        "src.shared.llm",
        "src.shared",
        "config.settings",
    ]:
        sys.modules.pop(mod, None)


# ---------------------------------------------------------------------------
# KF-01: chunk_markdown_by_sections
# ---------------------------------------------------------------------------
def test_chunk_markdown_by_sections():
    """chunk_markdown_by_sections returns one (heading, text) tuple per ## section."""
    text = (
        "# Title\n\n"
        "## Section One\nContent one\n\n"
        "## Section Two\nContent two\n\n"
        "## Section Three\nContent three"
    )
    result = chunk_markdown_by_sections(text)

    assert len(result) == 3

    # Headings must be stripped of leading # chars and surrounding whitespace
    assert result[0][0] == "Section One"
    assert "Content one" in result[0][1]

    assert result[1][0] == "Section Two"
    assert "Content two" in result[1][1]

    assert result[2][0] == "Section Three"
    assert "Content three" in result[2][1]

    # Edge case: empty input returns empty list
    assert chunk_markdown_by_sections("") == []


# ---------------------------------------------------------------------------
# KF-02: chunk_team_directory
# ---------------------------------------------------------------------------
def test_chunk_team_directory(tmp_path):
    """chunk_team_directory returns one (meta, text) tuple per team member."""
    members = [
        {
            "name": "Alice Smith",
            "role": "PM",
            "email": "a@b.com",
            "phone": "555-0001",
            "responsibilities": ["manage"],
            "area_of_authority": "all",
        },
        {
            "name": "Bob Jones",
            "role": "Engineer",
            "email": "b@b.com",
            "phone": "555-0002",
            "responsibilities": ["build"],
            "area_of_authority": "structural",
        },
    ]
    team_file = tmp_path / "team.json"
    team_file.write_text(json.dumps(members))

    result = chunk_team_directory(str(tmp_path))

    assert len(result) == 2

    # Each tuple: (meta dict, text string)
    assert result[0][0]["type"] == "team_member"
    assert result[0][0]["name"] == "Alice Smith"
    assert "Alice Smith" in result[0][1]

    assert result[1][0]["type"] == "team_member"
    assert result[1][0]["name"] == "Bob Jones"
    assert "Bob Jones" in result[1][1]


# ---------------------------------------------------------------------------
# KF-03: chunk_rules
# ---------------------------------------------------------------------------
def test_chunk_rules(tmp_path):
    """chunk_rules returns one (meta, text) tuple per rule in the YAML file."""
    rules_data = {
        "rules": [
            {
                "rule_id": "RULE-001",
                "description": "PM approves",
                "condition": "cost < 5000",
                "action": "notify PM",
                "stakeholders": ["PM"],
                "priority": "high",
            },
            {
                "rule_id": "RULE-002",
                "description": "Escalate",
                "condition": "cost > 50000",
                "action": "escalate",
                "stakeholders": ["PM", "Owner"],
                "priority": "critical",
            },
        ]
    }
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text(yaml.dump(rules_data))

    result = chunk_rules(str(tmp_path))

    assert len(result) == 2

    assert result[0][0]["rule_id"] == "RULE-001"
    assert "Rule ID: RULE-001" in result[0][1]

    assert result[1][0]["rule_id"] == "RULE-002"
    assert "Rule ID: RULE-002" in result[1][1]


# ---------------------------------------------------------------------------
# KF-04: chunk_historical_patterns
# ---------------------------------------------------------------------------
def test_chunk_historical_patterns(tmp_path):
    """chunk_historical_patterns returns one (meta, text) tuple per event."""
    events = [
        {
            "event_id": "EVT-001",
            "date": "2025-01-01",
            "material_original": "aluminum",
            "material_new": "wood",
            "location": "3rd floor",
            "quantity": 5,
            "reason": "cost",
            "outcome": "success",
            "cost_impact": 10000,
            "schedule_impact_days": 7,
            "pm_decision": "accepted",
            "lessons_learned": "lead time matters",
        },
        {
            "event_id": "EVT-002",
            "date": "2025-02-01",
            "material_original": "steel",
            "material_new": "aluminum",
            "location": "2nd floor",
            "quantity": 3,
            "reason": "weight",
            "outcome": "success",
            "cost_impact": 5000,
            "schedule_impact_days": 3,
            "pm_decision": "accepted",
            "lessons_learned": "check spec",
        },
    ]
    events_file = tmp_path / "historical_patterns.json"
    events_file.write_text(json.dumps(events))

    result = chunk_historical_patterns(str(tmp_path))

    assert len(result) == 2

    assert result[0][0]["event_id"] == "EVT-001"
    assert "Event ID: EVT-001" in result[0][1]

    assert result[1][0]["event_id"] == "EVT-002"
    assert "Event ID: EVT-002" in result[1][1]


# ---------------------------------------------------------------------------
# KF-05a: seed() calls DELETE on knowledge_chunks before any INSERT
# ---------------------------------------------------------------------------
def test_seed_calls_delete_before_insert():
    """seed() must DELETE from knowledge_chunks before any INSERT."""
    import scripts.seed_knowledge_folder as skf

    cursor_mock = MagicMock()
    conn_mock = MagicMock()
    conn_mock.cursor.return_value.__enter__ = MagicMock(return_value=cursor_mock)
    conn_mock.cursor.return_value.__exit__ = MagicMock(return_value=False)
    # Also support non-context-manager cursor usage
    conn_mock.cursor.return_value = cursor_mock

    # embed_batch returns enough embeddings for any batch
    def fake_embed_batch(texts, input_type="document"):
        return [[0.1] * 1024] * len(texts)

    with patch.object(skf, "get_connection", return_value=conn_mock), \
         patch.object(skf, "embed_batch", side_effect=fake_embed_batch):

        seed()

    # Collect all SQL strings passed to cursor.execute
    all_execute_calls = cursor_mock.execute.call_args_list
    sql_strings = []
    for c in all_execute_calls:
        if c.args:
            sql_strings.append((str(c.args[0]).upper(), c))

    delete_indices = [
        i for i, (sql, _) in enumerate(sql_strings)
        if "DELETE" in sql and "KNOWLEDGE_CHUNKS" in sql
    ]
    insert_indices = [
        i for i, (sql, _) in enumerate(sql_strings)
        if "INSERT" in sql and "KNOWLEDGE_CHUNKS" in sql
    ]

    assert len(delete_indices) >= 1, (
        "Expected at least one DELETE FROM knowledge_chunks call"
    )
    # DELETE must precede every INSERT
    if insert_indices:
        assert min(delete_indices) < min(insert_indices), (
            "DELETE must occur before any INSERT into knowledge_chunks"
        )


# ---------------------------------------------------------------------------
# KF-05b: seed() calls embed_batch with input_type="document"
# ---------------------------------------------------------------------------
def test_seed_calls_embed_batch_with_document_type():
    """seed() must call embed_batch exactly once with input_type='document'."""
    import scripts.seed_knowledge_folder as skf

    cursor_mock = MagicMock()
    conn_mock = MagicMock()
    conn_mock.cursor.return_value = cursor_mock

    embed_mock = MagicMock(return_value=[[0.1] * 1024] * 100)

    with patch.object(skf, "get_connection", return_value=conn_mock), \
         patch.object(skf, "embed_batch", embed_mock):

        seed()

    embed_mock.assert_called_once()
    call_args = embed_mock.call_args

    # Check input_type="document" passed as keyword or positional
    input_type_kwarg = call_args[1].get("input_type") if call_args[1] else None
    input_type_positional = call_args[0][1] if call_args[0] and len(call_args[0]) > 1 else None

    assert input_type_kwarg == "document" or input_type_positional == "document", (
        f"Expected embed_batch called with input_type='document', "
        f"got kwargs={call_args[1]}, args={call_args[0]}"
    )
