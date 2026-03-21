"""
Unit tests for knowledge folder chunking logic and seed script.
Phase 2: KF-01 through KF-05
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
import yaml

# Wave 0 import guard: file is always collectable; tests skip if impl missing.
# Uses Path.exists() check instead of a try/except import to avoid triggering
# config.settings singleton (pydantic ValidationError) at collection time before
# env vars are set. Lazy imports inside each test function after autouse fixture.
_IMPL_PATH = Path(__file__).parent.parent.parent / "scripts" / "seed_knowledge_folder.py"
IMPL_AVAILABLE = _IMPL_PATH.exists() and _IMPL_PATH.stat().st_size > 10

pytestmark = pytest.mark.skipif(
    not IMPL_AVAILABLE,
    reason="seed_knowledge_folder.py not yet implemented",
)


@pytest.fixture(autouse=True)
def _setup_env(monkeypatch):
    """Set env vars and pop settings-dependent modules before each test."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("VOYAGE_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
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


def test_chunk_markdown_by_sections():
    from scripts.seed_knowledge_folder import chunk_markdown_by_sections

    text = (
        "# Title\n\n"
        "## Section One\nContent one here.\n\n"
        "## Section Two\nContent two here.\n\n"
        "## Section Three\nContent three here."
    )
    result = chunk_markdown_by_sections(text)
    assert len(result) == 3
    assert result[0][0] == "Section One"
    assert "Content one here." in result[0][1]
    assert result[1][0] == "Section Two"
    assert result[2][0] == "Section Three"
    # Empty input returns empty list
    assert chunk_markdown_by_sections("") == []
    assert chunk_markdown_by_sections("   \n  ") == []


def test_chunk_team_directory(tmp_path):
    from scripts.seed_knowledge_folder import chunk_team_directory

    members = [
        {
            "name": "Alice Smith",
            "role": "Project Manager",
            "email": "alice@example.com",
            "phone": "555-0001",
            "responsibilities": ["manage project", "coordinate teams"],
            "area_of_authority": "all project decisions under $50K",
        },
        {
            "name": "Bob Jones",
            "role": "Structural Engineer",
            "email": "bob@example.com",
            "phone": "555-0002",
            "responsibilities": ["structural analysis", "PE stamp"],
            "area_of_authority": "structural modifications",
        },
    ]
    json_file = tmp_path / "team.json"
    json_file.write_text(json.dumps(members), encoding="utf-8")

    result = chunk_team_directory(str(json_file))
    assert len(result) == 2

    meta0, text0 = result[0]
    assert meta0["type"] == "team_member"
    assert meta0["name"] == "Alice Smith"
    assert meta0["role"] == "Project Manager"
    assert "Alice Smith" in text0
    assert "Project Manager" in text0

    meta1, text1 = result[1]
    assert meta1["name"] == "Bob Jones"
    assert "Bob Jones" in text1


def test_chunk_rules(tmp_path):
    from scripts.seed_knowledge_folder import chunk_rules

    rules_data = {
        "rules": [
            {
                "rule_id": "RULE-001",
                "description": "PM approves changes under $5K",
                "condition": "cost < 5000",
                "action": "notify PM",
                "stakeholders": ["Project Manager"],
                "priority": "normal",
            },
            {
                "rule_id": "RULE-002",
                "description": "Escalate above $50K immediately",
                "condition": "cost > 50000",
                "action": "escalate to owner",
                "stakeholders": ["Project Manager", "Owner Representative"],
                "priority": "critical",
            },
        ]
    }
    yaml_file = tmp_path / "rules.yaml"
    yaml_file.write_text(yaml.dump(rules_data), encoding="utf-8")

    result = chunk_rules(str(yaml_file))
    assert len(result) == 2

    meta0, text0 = result[0]
    assert meta0["rule_id"] == "RULE-001"
    assert meta0["type"] == "rule"
    assert "Rule ID: RULE-001" in text0
    assert "PM approves" in text0

    meta1, text1 = result[1]
    assert meta1["rule_id"] == "RULE-002"
    assert "Rule ID: RULE-002" in text1


def test_chunk_historical_patterns(tmp_path):
    from scripts.seed_knowledge_folder import chunk_historical_patterns

    events = [
        {
            "event_id": "EVT-001",
            "date": "2025-01-01",
            "material_original": "aluminum",
            "material_new": "wood",
            "element_type": "window",
            "location": "3rd floor",
            "quantity": 5,
            "reason": "cost savings",
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
            "element_type": "partition",
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
    json_file = tmp_path / "history.json"
    json_file.write_text(json.dumps(events), encoding="utf-8")

    result = chunk_historical_patterns(str(json_file))
    assert len(result) == 2

    meta0, text0 = result[0]
    assert meta0["event_id"] == "EVT-001"
    assert meta0["type"] == "historical_event"
    assert meta0["material_original"] == "aluminum"
    assert meta0["pm_decision"] == "accepted"
    assert "Event ID: EVT-001" in text0
    assert "aluminum" in text0

    meta1, text1 = result[1]
    assert meta1["event_id"] == "EVT-002"
    assert "Event ID: EVT-002" in text1


def test_seed_calls_delete_before_insert(monkeypatch):
    """Verify DELETE runs before INSERT and targets knowledge_chunks table."""
    # Track SQL call order
    executed_sql: list[str] = []

    cursor_mock = MagicMock()
    cursor_mock.rowcount = 0

    def track_execute(sql, *args, **kwargs):
        executed_sql.append(sql.strip())

    cursor_mock.execute.side_effect = track_execute
    cursor_mock.__enter__ = lambda s: s
    cursor_mock.__exit__ = MagicMock(return_value=False)

    conn_mock = MagicMock()
    conn_mock.cursor.return_value = cursor_mock

    # Patch get_connection and release_connection in seed script module
    import scripts.seed_knowledge_folder as seed_mod

    monkeypatch.setattr(seed_mod, "get_connection", lambda: conn_mock)
    monkeypatch.setattr(seed_mod, "release_connection", lambda c: None)

    # Patch embed_batch to return dummy vectors
    monkeypatch.setattr(
        seed_mod, "embed_batch", lambda texts, input_type="document": [[0.1] * 1024] * len(texts)
    )

    # Patch execute_values to avoid real DB
    monkeypatch.setattr(
        "scripts.seed_knowledge_folder.execute_values",
        lambda cur, sql, rows: executed_sql.append(sql.strip()),
    )

    seed_mod.seed()

    # At least one DELETE statement targeting knowledge_chunks
    delete_calls = [s for s in executed_sql if "DELETE" in s.upper() and "knowledge_chunks" in s]
    insert_calls = [s for s in executed_sql if "INSERT" in s.upper() and "knowledge_chunks" in s]

    assert len(delete_calls) >= 1, f"No DELETE found. SQL calls: {executed_sql}"
    assert len(insert_calls) >= 1, f"No INSERT found. SQL calls: {executed_sql}"

    # DELETE must appear before INSERT in call order
    first_delete_idx = next(i for i, s in enumerate(executed_sql) if "DELETE" in s.upper())
    first_insert_idx = next(i for i, s in enumerate(executed_sql) if "INSERT" in s.upper())
    assert first_delete_idx < first_insert_idx, "DELETE must come before INSERT"


def test_seed_calls_embed_batch_with_document_type(monkeypatch):
    """Verify embed_batch is called exactly once with input_type='document'."""
    embed_calls: list[dict] = []

    def mock_embed_batch(texts, input_type="document"):
        embed_calls.append({"texts_count": len(texts), "input_type": input_type})
        return [[0.1] * 1024] * len(texts)

    cursor_mock = MagicMock()
    cursor_mock.rowcount = 0
    cursor_mock.__enter__ = lambda s: s
    cursor_mock.__exit__ = MagicMock(return_value=False)
    conn_mock = MagicMock()
    conn_mock.cursor.return_value = cursor_mock

    import scripts.seed_knowledge_folder as seed_mod

    monkeypatch.setattr(seed_mod, "get_connection", lambda: conn_mock)
    monkeypatch.setattr(seed_mod, "release_connection", lambda c: None)
    monkeypatch.setattr(seed_mod, "embed_batch", mock_embed_batch)
    monkeypatch.setattr(
        "scripts.seed_knowledge_folder.execute_values",
        lambda cur, sql, rows: None,
    )

    seed_mod.seed()

    assert len(embed_calls) == 1, f"embed_batch should be called once, got {len(embed_calls)} calls"
    assert embed_calls[0]["input_type"] == "document", (
        f"embed_batch must use input_type='document', got '{embed_calls[0]['input_type']}'"
    )
    # Confirm total chunks in range (glossary ~5 + team 7 + rules 18 + history 12 = ~42-47)
    assert 35 <= embed_calls[0]["texts_count"] <= 60, (
        f"Expected 35-60 total chunks, got {embed_calls[0]['texts_count']}"
    )
