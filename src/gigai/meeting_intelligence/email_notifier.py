"""
Email Notification System

Sends email notifications for:
- Task assignments
- Meeting minutes
- Revision clouds created
- Status updates
- Daily digests
"""

import json
import logging
from datetime import datetime
from typing import Optional
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template

from ..storage import append_audit_log, publish_bus_event
from .models import TaskAssignment, ArchitecturalChange, RevisionMarker, MeetingContext

logger = logging.getLogger(__name__)


class EmailNotifier:
    """
    Sends email notifications using Gmail API or SMTP.
    """

    def __init__(
        self,
        smtp_server: str = "smtp.gmail.com",
        smtp_port: int = 587,
        sender_email: Optional[str] = None,
        sender_password: Optional[str] = None,
        use_gmail_api: bool = False,
    ):
        """
        Initialize email notifier.

        Args:
            smtp_server: SMTP server address
            smtp_port: SMTP port
            sender_email: Sender email address
            sender_password: Sender password or app password
            use_gmail_api: Use Gmail API instead of SMTP
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email or "gigai-notifications@company.com"
        self.sender_password = sender_password
        self.use_gmail_api = use_gmail_api
        self.sent_emails = []

    async def send_task_assignment_email(
        self,
        task: TaskAssignment,
        meeting_context: MeetingContext,
        change: ArchitecturalChange,
    ) -> bool:
        """
        Send email notifying architect of task assignment.

        Args:
            task: Task assignment
            meeting_context: Meeting context
            change: Architectural change details

        Returns:
            True if email sent successfully
        """
        try:
            # Build email content
            subject = self._build_task_subject(task)
            body = self._build_task_email_body(task, meeting_context, change)

            # Send email
            success = await self._send_email(
                to_email=task.assigned_to,
                to_name=task.assigned_to_name,
                subject=subject,
                body=body,
                html=True,
            )

            if success:
                task.email_sent = True
                logger.info(f"Task assignment email sent to {task.assigned_to}")

                # Log to audit
                await append_audit_log(
                    "email_sent",
                    {
                        "type": "task_assignment",
                        "recipient": task.assigned_to,
                        "task_id": task.assignment_id,
                        "change_id": task.change_id,
                    },
                )

            return success

        except Exception as e:
            logger.error(f"Error sending task assignment email: {e}")
            return False

    async def send_meeting_minutes_email(
        self,
        participants: list[str],
        meeting_context: MeetingContext,
        changes_summary: str,
        action_items: list[dict],
    ) -> bool:
        """
        Send meeting minutes to all participants.

        Args:
            participants: List of participant emails
            meeting_context: Meeting context
            changes_summary: Summary of design changes
            action_items: List of action items

        Returns:
            True if all emails sent
        """
        try:
            subject = self._build_minutes_subject(meeting_context)
            body = self._build_minutes_email_body(
                meeting_context, changes_summary, action_items
            )

            all_sent = True
            for participant_email in participants:
                success = await self._send_email(
                    to_email=participant_email,
                    subject=subject,
                    body=body,
                    html=True,
                )

                if not success:
                    all_sent = False
                else:
                    logger.info(f"Meeting minutes sent to {participant_email}")

            return all_sent

        except Exception as e:
            logger.error(f"Error sending meeting minutes: {e}")
            return False

    async def send_revision_notification(
        self,
        revision: RevisionMarker,
        task: TaskAssignment,
        meeting_context: MeetingContext,
    ) -> bool:
        """
        Send notification that revision cloud has been applied.

        Args:
            revision: Revision marker
            task: Associated task
            meeting_context: Meeting context

        Returns:
            True if sent successfully
        """
        try:
            subject = (
                f"Revit Revision Applied: {task.space} - {task.action}"
            )

            body = f"""
<html>
<body style="font-family: Arial, sans-serif;">
<h2>Design Change Marked in Revit</h2>

<p>The design change you requested has been marked in the Revit model.</p>

<h3>Details:</h3>
<ul>
<li><strong>Space:</strong> {task.space}</li>
<li><strong>Action:</strong> {task.action}</li>
<li><strong>Description:</strong> {task.description}</li>
<li><strong>Revision Mark:</strong> {revision.cloud_id}</li>
<li><strong>Applied at:</strong> {revision.applied_at}</li>
</ul>

<h3>Next Steps:</h3>
<ol>
<li>Open the Revit model</li>
<li>Find the red revision cloud in {task.space}</li>
<li>Review the attached comment for details</li>
<li>Make the requested changes</li>
<li>Mark the task as complete in GigAI dashboard</li>
</ol>

<p style="color: #666; margin-top: 20px; font-size: 12px;">
Meeting: {meeting_context.title}<br/>
Date: {meeting_context.date}<br/>
Reference: {revision.revision_id}
</p>
</body>
</html>
"""

            return await self._send_email(
                to_email=task.assigned_to,
                to_name=task.assigned_to_name,
                subject=subject,
                body=body,
                html=True,
            )

        except Exception as e:
            logger.error(f"Error sending revision notification: {e}")
            return False

    def _build_task_subject(self, task: TaskAssignment) -> str:
        """Build task assignment email subject"""
        priority_indicator = "🔴" if task.priority == "HIGH" else "🟡" if task.priority == "MEDIUM" else "🟢"
        return f"{priority_indicator} Design Change Assigned – {task.space} – {task.action}"

    def _build_task_email_body(
        self, task: TaskAssignment, meeting_context: MeetingContext, change: ArchitecturalChange
    ) -> str:
        """Build task assignment email HTML body"""
        return f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6;">

<h2>Design Change Task Assigned</h2>

<p>Dear {task.assigned_to_name},</p>

<p>A design revision from today's architecture meeting has been assigned to you.</p>

<h3 style="color: #d32f2f;">ACTION REQUIRED</h3>

<div style="background-color: #f5f5f5; padding: 15px; border-left: 4px solid #d32f2f;">
  <p><strong>{task.action.upper()}:</strong> {task.description}</p>
  <p><strong>Space:</strong> {task.space}</p>
  <p><strong>Priority:</strong> {task.priority}</p>
  <p><strong>Deadline:</strong> {task.deadline}</p>
</div>

<h3>Meeting Details</h3>
<ul>
  <li><strong>Meeting:</strong> {meeting_context.title}</li>
  <li><strong>Date:</strong> {meeting_context.date.strftime('%Y-%m-%d %H:%M')}</li>
  <li><strong>Requested by:</strong> {change.speaker}</li>
  <li><strong>Confidence:</strong> {change.confidence * 100:.0f}%</li>
</ul>

<h3>What to Do</h3>
<ol>
  <li>Open the project file in Revit</li>
  <li>Look for the <strong>red revision cloud</strong> in {task.space}</li>
  <li>Review the attached comment for full details</li>
  <li>Update the BIM model with the requested change</li>
  <li>When complete, mark the task status as "completed" in GigAI dashboard</li>
</ol>

<h3>Revision Cloud Reference</h3>
<p style="background-color: #fff3cd; padding: 10px; border-radius: 4px;">
  Change ID: <code>{change.change_id}</code><br/>
  Decision ID: Linked in GigAI<br/>
  Extracted Properties: {json.dumps(change.extracted_properties)}
</p>

<h3>Questions?</h3>
<p>
  Report issues or ask questions in the GigAI dashboard.<br/>
  Full meeting transcript: <a href="{meeting_context.transcript_url}">Available in Fireflies</a>
</p>

<hr style="margin-top: 30px; border: none; border-top: 1px solid #ddd;">

<p style="color: #666; font-size: 12px;">
  This task was automatically generated by GigAI from the meeting transcript.<br/>
  Do not reply to this email. Use the GigAI dashboard to update task status.
</p>

</body>
</html>
"""

    def _build_minutes_subject(self, meeting_context: MeetingContext) -> str:
        """Build meeting minutes email subject"""
        return f"Meeting Minutes – {meeting_context.date.strftime('%Y-%m-%d')} – {meeting_context.title}"

    def _build_minutes_email_body(
        self, meeting_context: MeetingContext, changes_summary: str, action_items: list[dict]
    ) -> str:
        """Build meeting minutes email HTML body"""
        action_items_html = ""
        for i, item in enumerate(action_items, 1):
            action_items_html += f"""
  <tr>
    <td style="padding: 8px; border-bottom: 1px solid #ddd;">{item.get('task', '')}</td>
    <td style="padding: 8px; border-bottom: 1px solid #ddd;">{item.get('assigned_to', '')}</td>
    <td style="padding: 8px; border-bottom: 1px solid #ddd;">{item.get('due', '')}</td>
  </tr>
"""

        return f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6;">

<h2>Architecture Coordination Meeting Minutes</h2>

<h3>Meeting Information</h3>
<ul>
  <li><strong>Title:</strong> {meeting_context.title}</li>
  <li><strong>Date:</strong> {meeting_context.date.strftime('%Y-%m-%d %H:%M')}</li>
  <li><strong>Duration:</strong> {meeting_context.duration_minutes} minutes</li>
  <li><strong>Project:</strong> {meeting_context.project_name}</li>
  <li><strong>Participants:</strong> {', '.join(meeting_context.participants)}</li>
</ul>

<h3>Design Decisions</h3>
<div style="background-color: #f5f5f5; padding: 15px;">
{changes_summary}
</div>

<h3>Action Items</h3>
<table style="width: 100%; border-collapse: collapse;">
  <thead>
    <tr style="background-color: #f5f5f5;">
      <th style="padding: 8px; text-align: left; border-bottom: 2px solid #ddd;">Task</th>
      <th style="padding: 8px; text-align: left; border-bottom: 2px solid #ddd;">Assigned To</th>
      <th style="padding: 8px; text-align: left; border-bottom: 2px solid #ddd;">Due Date</th>
    </tr>
  </thead>
  <tbody>
{action_items_html}
  </tbody>
</table>

<h3>Resources</h3>
<ul>
  <li><a href="{meeting_context.transcript_url}">Full Meeting Transcript (Fireflies)</a></li>
  <li><a href="https://gigai-dashboard.company.com">GigAI Dashboard for tracking</a></li>
  <li>Revit revision clouds have been applied to the model</li>
</ul>

<hr style="margin-top: 30px; border: none; border-top: 1px solid #ddd;">

<p style="color: #666; font-size: 12px;">
  These minutes were automatically generated by GigAI Meeting Intelligence.<br/>
  Meeting transcript: {meeting_context.title}
</p>

</body>
</html>
"""

    async def _send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        to_name: str = "",
        html: bool = False,
    ) -> bool:
        """
        Send email via SMTP or Gmail API.

        Args:
            to_email: Recipient email
            subject: Email subject
            body: Email body
            to_name: Recipient name
            html: Whether body is HTML

        Returns:
            True if sent successfully
        """
        try:
            if self.use_gmail_api:
                return await self._send_via_gmail_api(to_email, subject, body, html)
            else:
                return self._send_via_smtp(to_email, subject, body, to_name, html)

        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {e}")
            return False

    def _send_via_smtp(
        self, to_email: str, subject: str, body: str, to_name: str = "", html: bool = False
    ) -> bool:
        """Send email via SMTP"""
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.sender_email
            msg["To"] = to_email

            # Attach body
            if html:
                msg.attach(MIMEText(body, "html"))
            else:
                msg.attach(MIMEText(body, "plain"))

            # Send via SMTP
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                if self.sender_password:
                    server.login(self.sender_email, self.sender_password)
                server.send_message(msg)

            self.sent_emails.append(
                {
                    "to": to_email,
                    "subject": subject,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            logger.info(f"Email sent to {to_email}: {subject}")
            return True

        except Exception as e:
            logger.error(f"SMTP error: {e}")
            return False

    async def _send_via_gmail_api(
        self, to_email: str, subject: str, body: str, html: bool = False
    ) -> bool:
        """Send email via Gmail API"""
        try:
            # This would use the existing Gmail API integration
            # from google_calendar.py pattern
            logger.info(f"[MOCK] Sending via Gmail API to {to_email}")

            self.sent_emails.append(
                {
                    "to": to_email,
                    "subject": subject,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            return True

        except Exception as e:
            logger.error(f"Gmail API error: {e}")
            return False

    async def send_daily_digest(
        self, project_name: str, recipients: list[str], summary_data: dict
    ) -> bool:
        """
        Send daily digest of all changes and tasks.

        Args:
            project_name: Project name
            recipients: List of recipient emails
            summary_data: Summary statistics

        Returns:
            True if all sent
        """
        try:
            subject = f"GigAI Daily Digest – {project_name} – {datetime.now().strftime('%Y-%m-%d')}"

            body = f"""
<html>
<body style="font-family: Arial, sans-serif;">

<h2>GigAI Daily Summary</h2>

<h3>Today's Activity</h3>
<ul>
  <li>New meetings processed: {summary_data.get('meetings_processed', 0)}</li>
  <li>Design changes detected: {summary_data.get('changes_detected', 0)}</li>
  <li>Tasks assigned: {summary_data.get('tasks_assigned', 0)}</li>
  <li>Revisions applied: {summary_data.get('revisions_applied', 0)}</li>
</ul>

<h3>Pending Overdue Tasks</h3>
<p>{summary_data.get('overdue_tasks', 0)} tasks are overdue</p>

<h3>Key Updates</h3>
<p>{summary_data.get('summary', 'No major updates')}</p>

<p><a href="https://gigai-dashboard.company.com">View full dashboard</a></p>

</body>
</html>
"""

            all_sent = True
            for recipient in recipients:
                success = await self._send_email(
                    to_email=recipient,
                    subject=subject,
                    body=body,
                    html=True,
                )
                if not success:
                    all_sent = False

            return all_sent

        except Exception as e:
            logger.error(f"Error sending daily digest: {e}")
            return False

    def get_sent_emails(self) -> list[dict]:
        """Get log of sent emails"""
        return self.sent_emails.copy()
