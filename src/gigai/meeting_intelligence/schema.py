"""
Database Schema Extensions for Meeting Intelligence Module

Add these tables to the existing GigAI SQLite database:
- meetings: Store meeting metadata
- architectural_changes: Store detected design changes
- task_assignments: Store task assignments
- revisions: Store applied Revit revisions
"""

import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def create_meeting_intelligence_tables(db_path: str = "gigai_state.sqlite3") -> bool:
    """
    Create all Meeting Intelligence tables in SQLite database.

    Args:
        db_path: Path to SQLite database file

    Returns:
        True if successful, False otherwise
    """
    try:
        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()

        # Table 1: Meetings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meetings (
                meeting_id TEXT PRIMARY KEY,
                fireflies_meeting_id TEXT UNIQUE,
                title TEXT NOT NULL,
                project_id TEXT,
                project_name TEXT,
                date DATETIME NOT NULL,
                duration_minutes INTEGER,
                participants TEXT,  -- JSON array of participant names
                transcript_text TEXT,
                transcript_url TEXT,
                summary TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(project_id)
            )
        """)
        logger.info("Created 'meetings' table")

        # Table 2: Architectural Changes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS architectural_changes (
                change_id TEXT PRIMARY KEY,
                meeting_id TEXT NOT NULL,
                project_id TEXT,
                space TEXT NOT NULL,
                element_type TEXT NOT NULL,
                action TEXT NOT NULL,
                description TEXT,
                timestamp DATETIME,
                confidence REAL,
                speaker TEXT,
                transcript_reference TEXT,
                extracted_properties TEXT,  -- JSON
                affected_elements TEXT,  -- JSON array
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (meeting_id) REFERENCES meetings(meeting_id),
                FOREIGN KEY (project_id) REFERENCES projects(project_id)
            )
        """)
        logger.info("Created 'architectural_changes' table")

        # Table 3: Task Assignments
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_assignments (
                assignment_id TEXT PRIMARY KEY,
                decision_id TEXT,
                change_id TEXT NOT NULL,
                assigned_to TEXT,  -- Email
                assigned_to_name TEXT,
                assigned_to_role TEXT,
                space TEXT,
                action TEXT,
                description TEXT,
                priority TEXT CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH')),
                deadline DATE,
                calendar_event_id TEXT,
                email_sent BOOLEAN DEFAULT FALSE,
                status TEXT CHECK (status IN ('pending', 'in_progress', 'completed', 'on_hold')) DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME,
                FOREIGN KEY (change_id) REFERENCES architectural_changes(change_id),
                FOREIGN KEY (decision_id) REFERENCES decisions(decision_id)
            )
        """)
        logger.info("Created 'task_assignments' table")

        # Table 4: Revisions (Revit Revision Clouds)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS revisions (
                revision_id TEXT PRIMARY KEY,
                decision_id TEXT,
                change_id TEXT NOT NULL,
                revit_element_id TEXT NOT NULL,
                revit_project_id TEXT,
                space_name TEXT,
                revision_type TEXT DEFAULT 'NEW_REVISION',
                revision_number INTEGER,
                revision_date DATETIME,
                cloud_id TEXT,  -- Revit RevisionCloud ElementId
                shape_type TEXT DEFAULT 'CLOUD',
                color TEXT DEFAULT 'FF0000',  -- Red
                comment_text TEXT,
                comment_details TEXT,  -- JSON
                requested_by TEXT,
                applied BOOLEAN DEFAULT FALSE,
                applied_at DATETIME,
                applied_by TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (change_id) REFERENCES architectural_changes(change_id),
                FOREIGN KEY (decision_id) REFERENCES decisions(decision_id)
            )
        """)
        logger.info("Created 'revisions' table")

        # Table 5: Meeting Minutes (optional, can also use decisions table)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS meeting_minutes (
                minutes_id TEXT PRIMARY KEY,
                meeting_id TEXT NOT NULL UNIQUE,
                title TEXT,
                date DATETIME,
                participants TEXT,  -- JSON array
                duration_minutes INTEGER,
                project TEXT,
                decisions TEXT,  -- JSON array
                summary TEXT,
                action_items TEXT,  -- JSON array
                risks TEXT,  -- JSON array
                next_steps TEXT,
                generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (meeting_id) REFERENCES meetings(meeting_id)
            )
        """)
        logger.info("Created 'meeting_minutes' table")

        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_meetings_project_id ON meetings(project_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_meetings_date ON meetings(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_architectural_changes_meeting ON architectural_changes(meeting_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_architectural_changes_space ON architectural_changes(space)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_assignments_assigned_to ON task_assignments(assigned_to)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_assignments_status ON task_assignments(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_revisions_element_id ON revisions(revit_element_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_revisions_applied ON revisions(applied)")

        connection.commit()
        connection.close()

        logger.info("All Meeting Intelligence tables created successfully")
        return True

    except sqlite3.OperationalError as e:
        logger.error(f"Database error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False


def add_sample_data(db_path: str = "gigai_state.sqlite3") -> bool:
    """
    Add sample data for testing.

    Args:
        db_path: Path to SQLite database file

    Returns:
        True if successful, False otherwise
    """
    try:
        import json
        from datetime import datetime, timedelta

        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()

        # Sample meeting
        meeting_data = {
            "meeting_id": "meet_20260315_001",
            "fireflies_meeting_id": "ff_abc123xyz",
            "title": "Architecture Coordination - Phase 5",
            "project_id": "proj_tower_a",
            "project_name": "Residential Tower A",
            "date": "2026-03-15 10:15:00",
            "duration_minutes": 45,
            "participants": json.dumps(["Architect_A", "Architect_B", "Architect_C"]),
            "summary": "Discussed design changes for studio units, corridor modifications, and facade material updates",
        }

        cursor.execute(
            """INSERT OR IGNORE INTO meetings
            (meeting_id, fireflies_meeting_id, title, project_id, project_name, date,
             duration_minutes, participants, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            tuple(meeting_data.values()),
        )

        # Sample architectural change
        change_data = {
            "change_id": "change_001",
            "meeting_id": "meet_20260315_001",
            "project_id": "proj_tower_a",
            "space": "Studio Unit 504",
            "element_type": "window",
            "action": "resize",
            "description": "Increase window width from 1.2m to 2.4m for improved daylight",
            "timestamp": "2026-03-15 10:21:32",
            "confidence": 0.92,
            "speaker": "Architect_A",
            "transcript_reference": "10:21:32",
            "extracted_properties": json.dumps({"target_width": "2.4m"}),
            "affected_elements": json.dumps(["W-101", "W-102"]),
        }

        cursor.execute(
            """INSERT OR IGNORE INTO architectural_changes
            (change_id, meeting_id, project_id, space, element_type, action, description,
             timestamp, confidence, speaker, transcript_reference, extracted_properties, affected_elements)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            tuple(change_data.values()),
        )

        # Sample task assignment
        task_data = {
            "assignment_id": "task_001",
            "change_id": "change_001",
            "assigned_to": "alice.johnson@company.com",
            "assigned_to_name": "Alice Johnson",
            "assigned_to_role": "Unit Designer",
            "space": "Studio 504",
            "action": "resize",
            "description": "Increase window width to 2.4m",
            "priority": "HIGH",
            "deadline": "2026-03-22",
            "email_sent": True,
            "status": "pending",
        }

        cursor.execute(
            """INSERT OR IGNORE INTO task_assignments
            (assignment_id, change_id, assigned_to, assigned_to_name, assigned_to_role,
             space, action, description, priority, deadline, email_sent, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            tuple(task_data.values()),
        )

        connection.commit()
        connection.close()

        logger.info("Sample data added successfully")
        return True

    except Exception as e:
        logger.error(f"Error adding sample data: {e}")
        return False


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create tables
    success = create_meeting_intelligence_tables()
    if success:
        # Add sample data
        add_sample_data()
        print("Database setup complete!")
    else:
        print("Failed to create database tables")
