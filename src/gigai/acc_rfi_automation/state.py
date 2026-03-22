from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class RfiAutomationState:
    rfi_id: str
    payload_hash: str
    email_sent: bool
    calendar_created: bool
    email_message_id: str
    calendar_event_id: str
    last_status: str
    created_at: str
    updated_at: str


class RfiAutomationStateStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _initialize(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS acc_rfi_automation (
                    rfi_id TEXT PRIMARY KEY,
                    payload_hash TEXT NOT NULL,
                    email_sent INTEGER NOT NULL,
                    calendar_created INTEGER NOT NULL,
                    email_message_id TEXT NOT NULL,
                    calendar_event_id TEXT NOT NULL,
                    last_status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def get(self, rfi_id: str) -> RfiAutomationState | None:
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM acc_rfi_automation WHERE rfi_id=?", (rfi_id,)).fetchone()
        if row is None:
            return None
        return RfiAutomationState(
            rfi_id=row["rfi_id"],
            payload_hash=row["payload_hash"],
            email_sent=bool(row["email_sent"]),
            calendar_created=bool(row["calendar_created"]),
            email_message_id=row["email_message_id"],
            calendar_event_id=row["calendar_event_id"],
            last_status=row["last_status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def upsert(
        self,
        *,
        rfi_id: str,
        payload_hash: str,
        email_sent: bool,
        calendar_created: bool,
        email_message_id: str,
        calendar_event_id: str,
        last_status: str,
    ) -> None:
        existing = self.get(rfi_id)
        created_at = existing.created_at if existing is not None else _utc_now()
        updated_at = _utc_now()
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO acc_rfi_automation (
                    rfi_id, payload_hash, email_sent, calendar_created, email_message_id,
                    calendar_event_id, last_status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(rfi_id) DO UPDATE SET
                    payload_hash=excluded.payload_hash,
                    email_sent=excluded.email_sent,
                    calendar_created=excluded.calendar_created,
                    email_message_id=excluded.email_message_id,
                    calendar_event_id=excluded.calendar_event_id,
                    last_status=excluded.last_status,
                    updated_at=excluded.updated_at
                """,
                (
                    rfi_id,
                    payload_hash,
                    int(email_sent),
                    int(calendar_created),
                    email_message_id,
                    calendar_event_id,
                    last_status,
                    created_at,
                    updated_at,
                ),
            )

