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
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS review_queue (
                    id TEXT PRIMARY KEY,
                    structured_intelligence_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    reason_for_review TEXT NOT NULL,
                    entities_json TEXT NOT NULL,
                    actions_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    assigned_to TEXT,
                    reviewer_note TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    resolved_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS stt_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transcript_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    latency_ms REAL NOT NULL,
                    audio_duration_ms REAL,
                    transcript_length INTEGER,
                    error TEXT,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS stt_shadow_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transcript_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    fireflies_transcript TEXT NOT NULL,
                    whisper_transcript TEXT NOT NULL,
                    similarity_score REAL NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
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


def list_bus_events_since(after_id: int, limit: int = 50) -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM bus_events WHERE id > ? ORDER BY id ASC LIMIT ?",
            (after_id, limit),
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


def save_review_item(
    review_id: str,
    structured_intelligence_id: str,
    project_id: str,
    confidence_score: float,
    reason_for_review: str,
    entities: list[dict[str, Any]],
    actions: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> None:
    now = _utc_now()
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO review_queue (
                id, structured_intelligence_id, project_id, confidence_score, reason_for_review,
                entities_json, actions_json, metadata_json, status, assigned_to, reviewer_note,
                resolved_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT assigned_to FROM review_queue WHERE id=?), NULL),
                      COALESCE((SELECT reviewer_note FROM review_queue WHERE id=?), NULL),
                      COALESCE((SELECT resolved_at FROM review_queue WHERE id=?), NULL), ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                structured_intelligence_id = excluded.structured_intelligence_id,
                project_id = excluded.project_id,
                confidence_score = excluded.confidence_score,
                reason_for_review = excluded.reason_for_review,
                entities_json = excluded.entities_json,
                actions_json = excluded.actions_json,
                metadata_json = excluded.metadata_json,
                updated_at = excluded.updated_at
            """,
            (
                review_id,
                structured_intelligence_id,
                project_id,
                confidence_score,
                reason_for_review,
                _serialize(entities),
                _serialize(actions),
                _serialize(metadata or {}),
                "pending",
                review_id,
                review_id,
                review_id,
                now,
                now,
            ),
        )


def get_review_item(review_id: str) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM review_queue WHERE id=?", (review_id,)).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "structured_intelligence_id": row["structured_intelligence_id"],
        "project_id": row["project_id"],
        "confidence_score": row["confidence_score"],
        "reason_for_review": row["reason_for_review"],
        "entities": _deserialize(row["entities_json"], []),
        "actions": _deserialize(row["actions_json"], []),
        "metadata": _deserialize(row["metadata_json"], {}),
        "status": row["status"],
        "assigned_to": row["assigned_to"],
        "reviewer_note": row["reviewer_note"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "resolved_at": row["resolved_at"],
    }


def update_review_item(
    review_id: str,
    status: str,
    assigned_to: str | None = None,
    reviewer_note: str | None = None,
) -> None:
    resolved_at = _utc_now() if status in {"approved", "rejected"} else None
    with connection() as conn:
        conn.execute(
            """
            UPDATE review_queue
            SET status=?, assigned_to=COALESCE(?, assigned_to), reviewer_note=COALESCE(?, reviewer_note),
                resolved_at=COALESCE(?, resolved_at), updated_at=?
            WHERE id=?
            """,
            (status, assigned_to, reviewer_note, resolved_at, _utc_now(), review_id),
        )


def list_review_queue(
    project_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    with connection() as conn:
        query = "SELECT * FROM review_queue WHERE 1=1"
        params: list[Any] = []
        if project_id:
            query += " AND project_id=?"
            params.append(project_id)
        if status:
            query += " AND status=?"
            params.append(status)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
    return [
        {
            "id": row["id"],
            "structured_intelligence_id": row["structured_intelligence_id"],
            "project_id": row["project_id"],
            "confidence_score": row["confidence_score"],
            "reason_for_review": row["reason_for_review"],
            "entities": _deserialize(row["entities_json"], []),
            "actions": _deserialize(row["actions_json"], []),
            "metadata": _deserialize(row["metadata_json"], {}),
            "status": row["status"],
            "assigned_to": row["assigned_to"],
            "reviewer_note": row["reviewer_note"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "resolved_at": row["resolved_at"],
        }
        for row in rows
    ]


def save_stt_metric(
    transcript_id: str,
    provider: str,
    model: str,
    latency_ms: float,
    audio_duration_ms: float | None = None,
    transcript_length: int | None = None,
    error: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO stt_metrics (
                transcript_id, provider, model, latency_ms, audio_duration_ms,
                transcript_length, error, metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                transcript_id,
                provider,
                model,
                latency_ms,
                audio_duration_ms,
                transcript_length,
                error,
                _serialize(metadata or {}),
                _utc_now(),
            ),
        )


def get_stt_metrics(
    provider: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    with connection() as conn:
        query = "SELECT * FROM stt_metrics WHERE 1=1"
        params: list[Any] = []
        if provider:
            query += " AND provider=?"
            params.append(provider)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
    return [
        {
            "id": row["id"],
            "transcript_id": row["transcript_id"],
            "provider": row["provider"],
            "model": row["model"],
            "latency_ms": row["latency_ms"],
            "audio_duration_ms": row["audio_duration_ms"],
            "transcript_length": row["transcript_length"],
            "error": row["error"],
            "metadata": _deserialize(row["metadata_json"], {}),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def save_stt_shadow_metric(
    transcript_id: str,
    project_id: str,
    fireflies_transcript: str,
    whisper_transcript: str,
    similarity_score: float,
    metadata: dict[str, Any] | None = None,
) -> None:
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO stt_shadow_metrics (
                transcript_id, project_id, fireflies_transcript, whisper_transcript,
                similarity_score, metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                transcript_id,
                project_id,
                fireflies_transcript,
                whisper_transcript,
                similarity_score,
                _serialize(metadata or {}),
                _utc_now(),
            ),
        )


def get_stt_shadow_metrics(
    project_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    with connection() as conn:
        query = "SELECT * FROM stt_shadow_metrics WHERE 1=1"
        params: list[Any] = []
        if project_id:
            query += " AND project_id=?"
            params.append(project_id)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
    return [
        {
            "id": row["id"],
            "transcript_id": row["transcript_id"],
            "project_id": row["project_id"],
            "fireflies_transcript": row["fireflies_transcript"],
            "whisper_transcript": row["whisper_transcript"],
            "similarity_score": row["similarity_score"],
            "metadata": _deserialize(row["metadata_json"], {}),
            "created_at": row["created_at"],
        }
        for row in rows
    ]
