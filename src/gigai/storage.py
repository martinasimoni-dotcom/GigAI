from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sqlite3
from threading import Lock
from typing import Any, Iterator


_INIT_LOCK = Lock()
_INITIALIZED = False
_INITIALIZED_PATH: str | None = None


def _db_path() -> Path:
    raw = os.getenv("GIGAI_DB_PATH", "gigai_state.sqlite3").strip() or "gigai_state.sqlite3"
    return Path(raw)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _serialize(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def _deserialize(value: str | None, default: Any) -> Any:
    if not value:
        return default
    return json.loads(value)


def init_db() -> None:
    global _INITIALIZED, _INITIALIZED_PATH
    path = _db_path()
    if _INITIALIZED and _INITIALIZED_PATH == str(path):
        return

    with _INIT_LOCK:
        path = _db_path()
        if _INITIALIZED and _INITIALIZED_PATH == str(path):
            return

        if path.parent and str(path.parent) not in {"", "."}:
            path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    type TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    normalized_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS decisions (
                    id TEXT PRIMARY KEY,
                    event_id TEXT NOT NULL,
                    proposal_json TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    risk_level TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS actions (
                    id TEXT PRIMARY KEY,
                    decision_id TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS approvals (
                    id TEXT PRIMARY KEY,
                    decision_id TEXT NOT NULL,
                    requested_from TEXT NOT NULL,
                    status TEXT NOT NULL,
                    note TEXT,
                    requested_at TEXT NOT NULL,
                    resolved_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS bus_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    decision_id TEXT NOT NULL,
                    approval_id TEXT,
                    outcome TEXT NOT NULL,
                    feedback_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS coordination_plans (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    meeting_id TEXT,
                    transcript TEXT NOT NULL,
                    plan_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

        _INITIALIZED = True
        _INITIALIZED_PATH = str(path)


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    init_db()
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def upsert_event(
    event_id: str,
    source: str,
    event_type: str,
    project_id: str,
    payload: dict[str, Any],
    normalized: dict[str, Any],
    status: str,
    idempotency_key: str,
) -> None:
    now = _utc_now()
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO events (
                id, source, type, project_id, payload_json, normalized_json,
                status, idempotency_key, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                source=excluded.source,
                type=excluded.type,
                project_id=excluded.project_id,
                payload_json=excluded.payload_json,
                normalized_json=excluded.normalized_json,
                status=excluded.status,
                updated_at=excluded.updated_at
            """,
            (
                event_id,
                source,
                event_type,
                project_id,
                _serialize(payload),
                _serialize(normalized),
                status,
                idempotency_key,
                now,
                now,
            ),
        )


def update_event_status(event_id: str, status: str) -> None:
    with connection() as conn:
        conn.execute(
            "UPDATE events SET status=?, updated_at=? WHERE id=?",
            (status, _utc_now(), event_id),
        )


def get_event(event_id: str) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "source": row["source"],
        "type": row["type"],
        "project_id": row["project_id"],
        "payload_json": _deserialize(row["payload_json"], {}),
        "normalized_json": _deserialize(row["normalized_json"], {}),
        "status": row["status"],
        "idempotency_key": row["idempotency_key"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def find_event_by_idempotency(idempotency_key: str) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM events WHERE idempotency_key=?", (idempotency_key,)).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "source": row["source"],
        "type": row["type"],
        "project_id": row["project_id"],
        "payload_json": _deserialize(row["payload_json"], {}),
        "normalized_json": _deserialize(row["normalized_json"], {}),
        "status": row["status"],
        "idempotency_key": row["idempotency_key"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def save_decision(
    decision_id: str,
    event_id: str,
    proposal: dict[str, Any],
    confidence: float,
    risk_level: str,
    evidence: list[dict[str, Any]],
) -> None:
    with connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO decisions (
                id, event_id, proposal_json, confidence, risk_level, evidence_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision_id,
                event_id,
                _serialize(proposal),
                confidence,
                risk_level,
                _serialize(evidence),
                _utc_now(),
            ),
        )


def get_decision(decision_id: str) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM decisions WHERE id=?", (decision_id,)).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "event_id": row["event_id"],
        "proposal_json": _deserialize(row["proposal_json"], {}),
        "confidence": row["confidence"],
        "risk_level": row["risk_level"],
        "evidence_json": _deserialize(row["evidence_json"], []),
        "created_at": row["created_at"],
    }


def get_decision_by_event(event_id: str) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM decisions WHERE event_id=? ORDER BY created_at DESC LIMIT 1",
            (event_id,),
        ).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "event_id": row["event_id"],
        "proposal_json": _deserialize(row["proposal_json"], {}),
        "confidence": row["confidence"],
        "risk_level": row["risk_level"],
        "evidence_json": _deserialize(row["evidence_json"], []),
        "created_at": row["created_at"],
    }


def save_action(
    action_id: str,
    decision_id: str,
    mode: str,
    status: str,
    result: dict[str, Any],
) -> None:
    now = _utc_now()
    with connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO actions (
                id, decision_id, mode, status, result_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                action_id,
                decision_id,
                mode,
                status,
                _serialize(result),
                now,
                now,
            ),
        )


def update_action(
    action_id: str,
    status: str,
    result: dict[str, Any],
) -> None:
    with connection() as conn:
        conn.execute(
            "UPDATE actions SET status=?, result_json=?, updated_at=? WHERE id=?",
            (status, _serialize(result), _utc_now(), action_id),
        )


def get_action(action_id: str) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM actions WHERE id=?", (action_id,)).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "decision_id": row["decision_id"],
        "mode": row["mode"],
        "status": row["status"],
        "result_json": _deserialize(row["result_json"], {}),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get_action_by_decision(decision_id: str) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM actions WHERE decision_id=? ORDER BY created_at DESC LIMIT 1",
            (decision_id,),
        ).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "decision_id": row["decision_id"],
        "mode": row["mode"],
        "status": row["status"],
        "result_json": _deserialize(row["result_json"], {}),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def save_approval(
    approval_id: str,
    decision_id: str,
    requested_from: str,
    status: str,
    note: str | None = None,
) -> None:
    with connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO approvals (
                id, decision_id, requested_from, status, note, requested_at, resolved_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                approval_id,
                decision_id,
                requested_from,
                status,
                note,
                _utc_now(),
                None,
            ),
        )


def resolve_approval(approval_id: str, status: str, note: str | None = None) -> None:
    with connection() as conn:
        conn.execute(
            """
            UPDATE approvals
            SET status=?, note=?, resolved_at=?
            WHERE id=?
            """,
            (status, note, _utc_now(), approval_id),
        )


def get_approval(approval_id: str) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM approvals WHERE id=?", (approval_id,)).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "decision_id": row["decision_id"],
        "requested_from": row["requested_from"],
        "status": row["status"],
        "note": row["note"],
        "requested_at": row["requested_at"],
        "resolved_at": row["resolved_at"],
    }


def get_approval_by_decision(decision_id: str) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM approvals WHERE decision_id=? ORDER BY requested_at DESC LIMIT 1",
            (decision_id,),
        ).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "decision_id": row["decision_id"],
        "requested_from": row["requested_from"],
        "status": row["status"],
        "note": row["note"],
        "requested_at": row["requested_at"],
        "resolved_at": row["resolved_at"],
    }


def append_audit_log(
    entity_type: str,
    entity_id: str,
    event_type: str,
    actor: str,
    metadata: dict[str, Any],
) -> None:
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO audit_logs (entity_type, entity_id, event_type, actor, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (entity_type, entity_id, event_type, actor, _serialize(metadata), _utc_now()),
        )


def publish_bus_event(topic: str, payload: dict[str, Any]) -> None:
    with connection() as conn:
        conn.execute(
            "INSERT INTO bus_events (topic, payload_json, created_at) VALUES (?, ?, ?)",
            (topic, _serialize(payload), _utc_now()),
        )


def list_bus_events(limit: int = 50) -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM bus_events ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "topic": row["topic"],
            "payload_json": _deserialize(row["payload_json"], {}),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def add_feedback(
    decision_id: str,
    outcome: str,
    feedback: dict[str, Any],
    approval_id: str | None = None,
) -> None:
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO feedback (decision_id, approval_id, outcome, feedback_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (decision_id, approval_id, outcome, _serialize(feedback), _utc_now()),
        )


def list_project_history(project_id: str, artifact_id: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT id, type, normalized_json, status, updated_at
            FROM events
            WHERE project_id=?
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (project_id, limit),
        ).fetchall()

    history: list[dict[str, Any]] = []
    for row in rows:
        normalized = _deserialize(row["normalized_json"], {})
        if artifact_id and normalized.get("artifact_id") not in {None, artifact_id}:
            continue
        history.append(
            {
                "event_id": row["id"],
                "type": row["type"],
                "status": row["status"],
                "updated_at": row["updated_at"],
                "normalized": normalized,
            }
        )
    return history


def save_coordination_plan(
    plan_id: str,
    project_id: str,
    meeting_id: str | None,
    transcript: str,
    plan: dict[str, Any],
    status: str,
) -> None:
    now = _utc_now()
    with connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO coordination_plans (
                id, project_id, meeting_id, transcript, plan_json, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                plan_id,
                project_id,
                meeting_id,
                transcript,
                _serialize(plan),
                status,
                now,
                now,
            ),
        )


def update_coordination_plan(
    plan_id: str,
    status: str,
    plan: dict[str, Any],
) -> None:
    with connection() as conn:
        conn.execute(
            """
            UPDATE coordination_plans
            SET status=?, plan_json=?, updated_at=?
            WHERE id=?
            """,
            (status, _serialize(plan), _utc_now(), plan_id),
        )


def get_coordination_plan(plan_id: str) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM coordination_plans WHERE id=?", (plan_id,)).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "project_id": row["project_id"],
        "meeting_id": row["meeting_id"],
        "transcript": row["transcript"],
        "plan_json": _deserialize(row["plan_json"], {}),
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
