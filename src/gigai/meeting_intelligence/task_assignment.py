"""
Task Assignment System

Assigns design changes to responsible architects based on:
- Space-to-architect mapping from project glossary
- Action type and priority
- Deadline calculation based on priority
- Google Calendar integration
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

from ..google_calendar import sync_event
from ..storage import append_audit_log, publish_bus_event
from .models import ArchitecturalChange, TaskAssignment, MeetingContext

logger = logging.getLogger(__name__)


class TaskAssigner:
    """
    Assigns architectural changes to responsible team members.
    Uses project glossary to determine responsibility.
    """

    def __init__(self, glossary_path: Optional[str] = None):
        """
        Initialize task assigner with project glossary.

        Args:
            glossary_path: Path to meeting_glossary.json
        """
        self.glossary = self._load_glossary(glossary_path)
        self.default_settings = self.glossary.get("default_settings", {})

    def _load_glossary(self, glossary_path: Optional[str]) -> dict:
        """Load meeting glossary from config file"""
        default_path = Path(__file__).parent.parent.parent / "config" / "meeting_glossary.json"

        if glossary_path and Path(glossary_path).exists():
            path = Path(glossary_path)
        elif default_path.exists():
            path = default_path
        else:
            logger.warning("Meeting glossary not found, using minimal configuration")
            return self._default_glossary()

        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading glossary: {e}")
            return self._default_glossary()

    def _default_glossary(self) -> dict:
        """Minimal default glossary"""
        return {
            "default_settings": {
                "task_deadline_days": 7,
                "approval_required_risk_level": "HIGH",
                "notify_on_task_assign": True,
            },
            "projects": {},
        }

    def assign_change(
        self,
        change: ArchitecturalChange,
        project_name: str,
        change_priority: str = "MEDIUM",
        meeting_context: Optional[MeetingContext] = None,
    ) -> Optional[TaskAssignment]:
        """
        Assign a design change to responsible architect.

        Args:
            change: Architectural change to assign
            project_name: Project name from glossary
            change_priority: Priority level (LOW, MEDIUM, HIGH)
            meeting_context: Optional meeting context for details

        Returns:
            TaskAssignment if successful, None otherwise
        """
        try:
            # 1. Find project in glossary
            project = self.glossary.get("projects", {}).get(project_name)
            if not project:
                logger.warning(f"Project {project_name} not found in glossary")
                return None

            # 2. Find responsible architect for this space
            spaces = project.get("spaces", {})
            space_config = None

            # Exact match
            if change.space in spaces:
                space_config = spaces[change.space]
            else:
                # Fuzzy match
                space_config = self._find_matching_space(change.space, spaces)

            if not space_config:
                logger.warning(f"No space configuration found for {change.space}")
                return None

            assigned_to = space_config.get("responsible_email")
            assigned_to_name = self._get_architect_name(project, assigned_to)
            assigned_role = space_config.get("responsible_role", "Designer")

            # 3. Calculate deadline based on priority
            priority_config = project.get("task_priorities", {}).get(
                change_priority, {"deadline_days": 7}
            )
            deadline_days = priority_config.get("deadline_days", 7)
            deadline = (datetime.now() + timedelta(days=deadline_days)).date()

            # 4. Create task assignment
            task = TaskAssignment(
                assignment_id=f"task_{datetime.now().timestamp()}",
                change_id=change.change_id,
                assigned_to=assigned_to,
                assigned_to_name=assigned_to_name,
                assigned_to_role=assigned_role,
                space=change.space,
                action=change.action,
                description=change.description,
                priority=change_priority,
                deadline=deadline,
                email_sent=False,
                status="pending",
            )

            logger.info(f"Task assigned to {assigned_to_name}: {change.space} - {change.action}")
            return task

        except Exception as e:
            logger.error(f"Error assigning change: {e}")
            return None

    def assign_multiple_changes(
        self,
        changes: list[ArchitecturalChange],
        project_name: str,
        meeting_context: Optional[MeetingContext] = None,
    ) -> list[TaskAssignment]:
        """
        Assign multiple changes from a meeting.

        Args:
            changes: List of architectural changes
            project_name: Project name
            meeting_context: Optional meeting context

        Returns:
            List of task assignments
        """
        tasks = []

        for change in changes:
            # Estimate priority from change action
            priority = self._estimate_priority(change)

            task = self.assign_change(change, project_name, priority, meeting_context)
            if task:
                tasks.append(task)

        logger.info(f"Assigned {len(tasks)} out of {len(changes)} changes")
        return tasks

    async def create_calendar_event(
        self, task: TaskAssignment, meeting_id: str, meeting_date: datetime
    ) -> Optional[str]:
        """
        Create a Google Calendar event for the task.

        Args:
            task: Task assignment
            meeting_id: Meeting ID for reference
            meeting_date: Date of the meeting

        Returns:
            Calendar event ID if successful
        """
        try:
            # Build event title and description
            event_title = f"Design Change: {task.space} - {task.action}"

            event_description = f"""Design Change Task

Space: {task.space}
Element: {task.action}
Description: {task.description}

Priority: {task.priority}
Deadline: {task.deadline}
Meeting Reference: {meeting_id}

Action Required:
1. Review the Revit revision cloud
2. Update the BIM model
3. Mark complete in GigAI dashboard

For questions, refer to the full meeting transcript and revision notes.
"""

            # Create calendar event
            event_data = {
                "summary": event_title,
                "description": event_description,
                "start": {
                    "date": str(task.deadline),  # All-day event on deadline
                },
                "end": {
                    "date": str(task.deadline + timedelta(days=1)),
                },
                "attendees": [
                    {"email": task.assigned_to},
                ],
                "reminders": {
                    "useDefault": False,
                    "overrides": [
                        {"method": "email", "minutes": 24 * 60},  # 1 day before
                        {"method": "popup", "minutes": 60},  # 1 hour before
                    ],
                },
            }

            # Call Google Calendar API
            calendar_event_id = await sync_event(event_data)

            logger.info(f"Calendar event created: {calendar_event_id}")
            return calendar_event_id

        except Exception as e:
            logger.error(f"Error creating calendar event: {e}")
            return None

    def _find_matching_space(self, space_name: str, spaces: dict) -> Optional[dict]:
        """Find space using fuzzy matching"""
        from difflib import SequenceMatcher

        space_lower = space_name.lower()
        best_match = None
        best_score = 0.6

        for space_key, space_config in spaces.items():
            # Check main space name
            score = SequenceMatcher(None, space_lower, space_key.lower()).ratio()

            if score > best_score:
                best_score = score
                best_match = space_config

        return best_match

    def _get_architect_name(self, project: dict, email: str) -> str:
        """Get architect name by email"""
        disciplines = project.get("disciplines", {})

        for discipline, discipline_data in disciplines.items():
            team_members = discipline_data.get("team_members", [])
            for member in team_members:
                if member.get("email") == email:
                    return member.get("name", email.split("@")[0])

        return email.split("@")[0]

    def _estimate_priority(self, change: ArchitecturalChange) -> str:
        """Estimate priority from change action"""
        high_priority = ["remove", "move", "add"]
        medium_priority = ["resize", "change_material"]

        action_lower = change.action.lower()

        if any(a in action_lower for a in high_priority):
            return "HIGH"
        elif any(a in action_lower for a in medium_priority):
            return "MEDIUM"
        else:
            return "LOW"

    def get_team_workload(self, project_name: str) -> dict:
        """
        Get current workload for each team member.

        Args:
            project_name: Project to analyze

        Returns:
            Dictionary of email -> task count
        """
        # In production, would query database for active tasks
        # For MVP, return structure
        return {
            "alice.johnson@company.com": 3,
            "bob.wilson@company.com": 2,
            "david.lee@company.com": 5,
        }

    async def balance_workload(
        self, task: TaskAssignment, project_name: str
    ) -> TaskAssignment:
        """
        Re-assign task to less-busy architect if needed.

        Args:
            task: Task assignment
            project_name: Project name

        Returns:
            Task with potentially updated assignment
        """
        # Get team workload
        workload = self.get_team_workload(project_name)

        # If assigned person is overloaded, find alternative
        current_load = workload.get(task.assigned_to, 0)

        if current_load > 5:  # Overloaded threshold
            # Find less busy person with same role
            alternatives = self._find_role_alternatives(task.assigned_to_role, project_name)

            for email in alternatives:
                alt_load = workload.get(email, 0)
                if alt_load < current_load:
                    logger.info(f"Re-assigning {task.space} from {task.assigned_to} to {email}")
                    task.assigned_to = email
                    task.assigned_to_name = self._get_architect_name(
                        self.glossary.get("projects", {}).get(project_name, {}), email
                    )
                    break

        return task

    def _find_role_alternatives(self, role: str, project_name: str) -> list[str]:
        """Find other architects with same role"""
        project = self.glossary.get("projects", {}).get(project_name, {})
        alternatives = []

        for discipline, discipline_data in project.get("disciplines", {}).items():
            for member in discipline_data.get("team_members", []):
                if member.get("role") == role:
                    alternatives.append(member.get("email"))

        return alternatives

    async def notify_assignment(self, task: TaskAssignment, meeting_id: str) -> bool:
        """
        Send notification about task assignment.

        Args:
            task: Task assignment
            meeting_id: Meeting reference

        Returns:
            True if successful
        """
        # Framework for notification - implemented in email_notifier.py
        logger.info(f"Task notification prepared for {task.assigned_to}")
        return True

    async def check_overdue_tasks(self, project_name: str) -> list[TaskAssignment]:
        """
        Check for overdue tasks.

        Args:
            project_name: Project to check

        Returns:
            List of overdue tasks
        """
        # In production, would query database
        # For MVP, return framework
        return []
