"""
Meeting Minutes Generator

Creates structured meeting minutes from architectural changes and decisions.
Supports HTML, PDF, and JSON output formats.
"""

import json
import logging
from datetime import datetime
from typing import Optional, List
from pathlib import Path

from .models import (
    ArchitecturalChange,
    MeetingContext,
    MeetingMinutes,
    TaskAssignment,
    RevisionMarker,
)

logger = logging.getLogger(__name__)


class MeetingMinutesGenerator:
    """
    Generates structured meeting minutes from architectural discussions.
    """

    def __init__(self):
        """Initialize minutes generator"""
        self.minutes = None

    def generate_minutes(
        self,
        meeting_context: MeetingContext,
        changes: List[ArchitecturalChange],
        tasks: List[TaskAssignment],
        revisions: Optional[List[RevisionMarker]] = None,
    ) -> MeetingMinutes:
        """
        Generate complete meeting minutes.

        Args:
            meeting_context: Meeting metadata
            changes: Detected architectural changes
            tasks: Assigned tasks
            revisions: Optional placed revisions

        Returns:
            MeetingMinutes object
        """
        try:
            # Build decisions list
            decisions = self._build_decisions(changes, tasks, revisions)

            # Build action items
            action_items = self._build_action_items(tasks)

            # Build risks list
            risks = self._extract_risks(changes)

            # Build summary
            summary = self._generate_summary(meeting_context, changes)

            # Build next steps
            next_steps = self._generate_next_steps(tasks)

            # Create minutes object
            minutes = MeetingMinutes(
                meeting_id=meeting_context.meeting_id,
                title=meeting_context.title,
                date=meeting_context.date,
                participants=meeting_context.participants,
                duration_minutes=meeting_context.duration_minutes,
                project=meeting_context.project_name,
                decisions=decisions,
                summary=summary,
                action_items=action_items,
                risks=risks,
                next_steps=next_steps,
            )

            self.minutes = minutes
            logger.info(f"Meeting minutes generated: {len(decisions)} decisions")
            return minutes

        except Exception as e:
            logger.error(f"Error generating meeting minutes: {e}")
            raise

    def _build_decisions(
        self,
        changes: List[ArchitecturalChange],
        tasks: List[TaskAssignment],
        revisions: Optional[List[RevisionMarker]] = None,
    ) -> List[dict]:
        """Build decisions list from changes and tasks"""
        decisions = []

        # Group by space
        by_space = {}
        for change in changes:
            if change.space not in by_space:
                by_space[change.space] = {
                    "changes": [],
                    "tasks": [],
                    "revisions": [],
                }
            by_space[change.space]["changes"].append(change)

        # Add tasks and revisions
        for task in tasks:
            space = task.space
            if space not in by_space:
                by_space[space] = {"changes": [], "tasks": [], "revisions": []}
            by_space[space]["tasks"].append(task)

        if revisions:
            for revision in revisions:
                space = revision.space_name
                if space not in by_space:
                    by_space[space] = {"changes": [], "tasks": [], "revisions": []}
                by_space[space]["revisions"].append(revision)

        # Build decision entries
        order = 1
        for space, space_data in by_space.items():
            for change in space_data["changes"]:
                # Find associated task
                task = next(
                    (t for t in space_data["tasks"] if t.change_id == change.change_id),
                    None,
                )
                # Find associated revision
                revision = next(
                    (r for r in space_data["revisions"] if r.change_id == change.change_id),
                    None,
                )

                decision = {
                    "order": order,
                    "space": change.space,
                    "element": change.element_type,
                    "action": change.action.upper(),
                    "description": change.description,
                    "assigned_to": task.assigned_to_name if task else "Unassigned",
                    "assigned_role": task.assigned_to_role if task else "N/A",
                    "priority": task.priority if task else self._estimate_priority(change),
                    "deadline": str(task.deadline) if task else "TBD",
                    "status": "Pending Review",
                    "confidence": f"{change.confidence * 100:.0f}%",
                    "speaker": change.speaker or "Unknown",
                    "revision_cloud": revision.cloud_id if revision and revision.applied else "Pending",
                }

                decisions.append(decision)
                order += 1

        return decisions

    def _build_action_items(self, tasks: List[TaskAssignment]) -> List[dict]:
        """Build action items from tasks"""
        items = []

        for task in tasks:
            item = {
                "task": f"{task.action}: {task.description}",
                "assigned_to": task.assigned_to_name,
                "role": task.assigned_to_role,
                "due": str(task.deadline),
                "priority": task.priority,
                "status": task.status,
            }
            items.append(item)

        return items

    def _extract_risks(self, changes: List[ArchitecturalChange]) -> List[str]:
        """Extract risks from design changes"""
        risks = []

        # Detect high-risk changes
        for change in changes:
            if change.action.lower() in ["remove", "move"]:
                risks.append(f"HIGH: {change.action} of {change.element_type} in {change.space} requires structural review")

            if change.confidence < 0.75:
                risks.append(
                    f"MEDIUM: Confidence {change.confidence * 100:.0f}% for {change.space} change - verify with team"
                )

            if change.element_type in ["wall", "column", "floor"]:
                risks.append(f"MEDIUM: Structural element change in {change.space} needs structural coordination")

        # Count multiple changes in same space
        spaces = {}
        for change in changes:
            spaces[change.space] = spaces.get(change.space, 0) + 1

        for space, count in spaces.items():
            if count > 2:
                risks.append(f"MEDIUM: {count} design changes in {space} - potential coordination conflict")

        return list(set(risks))  # Remove duplicates

    def _generate_summary(self, meeting_context: MeetingContext, changes: List[ArchitecturalChange]) -> str:
        """Generate meeting summary"""
        if not changes:
            return "No architectural changes were identified in this meeting."

        # Group by action
        by_action = {}
        for change in changes:
            action = change.action
            if action not in by_action:
                by_action[action] = 0
            by_action[action] += 1

        summary_lines = []
        summary_lines.append(
            f"Design coordination meeting with {len(meeting_context.participants)} participants."
        )
        summary_lines.append(
            f"Meeting identified {len(changes)} architectural design changes requiring action:"
        )

        for action, count in by_action.items():
            summary_lines.append(f"  - {count} element(s) to {action}")

        # Get unique spaces
        spaces = set(c.space for c in changes)
        summary_lines.append(f"Affected spaces: {', '.join(sorted(spaces))}")

        return " ".join(summary_lines)

    def _generate_next_steps(self, tasks: List[TaskAssignment]) -> str:
        """Generate next steps recommendations"""
        if not tasks:
            return "No followup actions required."

        lines = []
        lines.append(f"1. Team members should review their assigned tasks (see action items above)")
        lines.append("2. Open Revit model and locate red revision clouds for each assigned change")
        lines.append("3. Review attached comments for detailed change specifications")
        lines.append("4. Make required modifications to the BIM model")
        lines.append("5. Mark tasks as complete in GigAI dashboard when done")
        lines.append("6. Schedule followup meeting to review completed changes and coordinate any conflicts")

        # Add deadline warning if many high priority
        high_priority = sum(1 for t in tasks if t.priority == "HIGH")
        if high_priority > 0:
            lines.append(
                f"\nWARNING: {high_priority} HIGH priority tasks due within 3 days - coordinate to avoid conflicts"
            )

        return "\n".join(lines)

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

    def render_html(self) -> str:
        """Render minutes as HTML"""
        if not self.minutes:
            logger.error("No minutes to render, call generate_minutes() first")
            return ""

        m = self.minutes

        decisions_html = ""
        for decision in m.decisions:
            decisions_html += f"""
  <tr>
    <td>{decision['order']}</td>
    <td>{decision['space']}</td>
    <td>{decision['element']}</td>
    <td>{decision['action']}</td>
    <td>{decision['assigned_to']}</td>
    <td>{decision['priority']}</td>
    <td>{decision['deadline']}</td>
  </tr>
"""

        action_items_html = ""
        for item in m.action_items:
            action_items_html += f"""
  <tr>
    <td>{item['task']}</td>
    <td>{item['assigned_to']}</td>
    <td>{item['due']}</td>
    <td>{item['priority']}</td>
  </tr>
"""

        risks_html = ""
        for risk in m.risks:
            risks_html += f"  <li>{risk}</li>\n"

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{m.title}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1, h2, h3 {{
            color: #1976d2;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            border: 1px solid #ddd;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #f5f5f5;
            font-weight: bold;
        }}
        tr:hover {{
            background-color: #f9f9f9;
        }}
        .priority-HIGH {{ color: #d32f2f; font-weight: bold; }}
        .priority-MEDIUM {{ color: #f57c00; }}
        .priority-LOW {{ color: #388e3c; }}
        .metadata {{
            background-color: #f5f5f5;
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
        }}
        .summary {{
            background-color: #e3f2fd;
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
        }}
        .risks {{
            background-color: #fff3e0;
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
        }}
    </style>
</head>
<body>

<h1>{m.title}</h1>

<div class="metadata">
    <p><strong>Date:</strong> {m.date.strftime('%Y-%m-%d %H:%M')}</p>
    <p><strong>Duration:</strong> {m.duration_minutes} minutes</p>
    <p><strong>Project:</strong> {m.project}</p>
    <p><strong>Participants:</strong> {', '.join(m.participants)}</p>
</div>

<div class="summary">
    <h2>Summary</h2>
    <p>{m.summary}</p>
</div>

<h2>Design Decisions</h2>
<table>
    <thead>
        <tr>
            <th>#</th>
            <th>Space</th>
            <th>Element</th>
            <th>Action</th>
            <th>Assigned To</th>
            <th>Priority</th>
            <th>Deadline</th>
        </tr>
    </thead>
    <tbody>
{decisions_html}
    </tbody>
</table>

<h2>Action Items</h2>
<table>
    <thead>
        <tr>
            <th>Task</th>
            <th>Assigned To</th>
            <th>Due Date</th>
            <th>Priority</th>
        </tr>
    </thead>
    <tbody>
{action_items_html}
    </tbody>
</table>

<div class="risks">
    <h2>Identified Risks</h2>
    <ul>
{risks_html}
    </ul>
</div>

<h2>Next Steps</h2>
<p>{m.next_steps}</p>

<hr style="margin-top: 40px; border: none; border-top: 1px solid #ddd;">
<p style="color: #666; font-size: 12px;">
    Generated by GigAI Meeting Intelligence on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>
    Meeting ID: {m.meeting_id}
</p>

</body>
</html>
"""

        return html

    def render_json(self) -> str:
        """Render minutes as JSON"""
        if not self.minutes:
            logger.error("No minutes to render")
            return "{}"

        return json.dumps(self.minutes.model_dump(), indent=2, default=str)

    def save_html(self, output_path: str) -> bool:
        """Save minutes as HTML file"""
        try:
            html = self.render_html()
            Path(output_path).write_text(html, encoding="utf-8")
            logger.info(f"Minutes saved to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving HTML: {e}")
            return False

    def save_json(self, output_path: str) -> bool:
        """Save minutes as JSON file"""
        try:
            json_data = self.render_json()
            Path(output_path).write_text(json_data, encoding="utf-8")
            logger.info(f"Minutes saved to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving JSON: {e}")
            return False

    def render_pdf(self) -> Optional[bytes]:
        """
        Render minutes as PDF.
        Requires: pip install reportlab weasyprint
        """
        try:
            # Try using weasyprint (better for HTML to PDF)
            from weasyprint import HTML
            import io

            html = self.render_html()
            pdf_bytes = io.BytesIO()
            HTML(string=html).write_pdf(pdf_bytes)
            return pdf_bytes.getvalue()

        except ImportError:
            logger.error("weasyprint not installed, PDF rendering not available")
            logger.info("Install with: pip install weasyprint")
            return None
        except Exception as e:
            logger.error(f"Error rendering PDF: {e}")
            return None
