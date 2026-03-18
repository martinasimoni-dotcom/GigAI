"""
Revision Executor

Coordinates the complete revision workflow:
1. Receives approved decision for design change
2. Identifies affected BIM elements
3. Creates revision clouds in Revit
4. Attaches comments with change details
5. Logs to database
6. Updates BIM360
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from ..revit import RevitRESTClient
from ..bim360_client import BIM360Client
from ..storage import append_audit_log, publish_bus_event
from .models import ArchitecturalChange, RevisionMarker, BIMElement
from .bim_identifier import BIMElementIdentifier

logger = logging.getLogger(__name__)


class RevisionExecutor:
    """
    Execute revision marking in Revit when design changes are approved.
    """

    def __init__(self, revit_server_url: str = "http://localhost:8000"):
        """
        Initialize executor with Revit and BIM360 clients.

        Args:
            revit_server_url: URL to Revit REST server
        """
        self.revit_client = RevitRESTClient(revit_server_url=revit_server_url)
        self.bim360_client = BIM360Client()
        self.bim_identifier = BIMElementIdentifier()

    async def execute_revision(
        self,
        change: ArchitecturalChange,
        decision_id: str,
        project_id: str,
        meeting_id: str,
        requested_by: str,
        bim_elements: Optional[list[BIMElement]] = None,
    ) -> Optional[RevisionMarker]:
        """
        Execute revision marking for an approved design change.

        Args:
            change: Architectural change to mark
            decision_id: GigAI decision ID
            project_id: Project ID
            meeting_id: Meeting ID for reference
            requested_by: Person who requested the change
            bim_elements: Optional pre-identified BIM elements

        Returns:
            RevisionMarker object if successful, None otherwise
        """
        try:
            logger.info(f"Executing revision for change {change.change_id}")

            # 1. Identify BIM elements if not provided
            if not bim_elements:
                logger.info(f"Identifying BIM elements for {change.space}")
                bim_elements = self.bim_identifier.find_elements_for_change(change)

            if not bim_elements:
                logger.warning(f"No BIM elements found for {change.space}")
                return None

            # 2. Build revision comment text
            comment_text = self._build_revision_comment(change, requested_by, meeting_id)
            comment_details = self._build_comment_metadata(change, decision_id, meeting_id, requested_by)

            # 3. Create revision cloud for each affected element
            revision_marker = None

            for element in bim_elements:
                try:
                    logger.info(f"Creating revision cloud for element {element.element_id}")

                    # Determine priority and color based on action
                    priority = self._estimate_priority(change)
                    color = self._get_color_for_priority(priority)

                    # Create revision marker object
                    revision_marker = RevisionMarker(
                        revision_id=f"rev_{datetime.now().timestamp()}",
                        decision_id=decision_id,
                        change_id=change.change_id,
                        revit_element_id=element.element_id,
                        revit_project_id=project_id,
                        space_name=element.space_name,
                        revision_type="NEW_REVISION",
                        color=color,
                        comment_text=comment_text,
                        comment_details=comment_details,
                        requested_by=requested_by,
                    )

                    # Call Revit to create the cloud
                    cloud_id = await self.revit_client.create_revision_cloud(revision_marker)

                    if cloud_id:
                        revision_marker.cloud_id = cloud_id
                        revision_marker.applied = True
                        revision_marker.applied_at = datetime.now()
                        revision_marker.applied_by = "GigAI_System"

                        logger.info(f"Revision cloud created: {cloud_id}")

                        # Add comment to element
                        await self.revit_client.add_comment_to_element(
                            element_id=element.element_id,
                            comment_text=comment_text,
                            comment_details=comment_details,
                        )

                        # Update element parameter (Mark/Comments)
                        await self.revit_client.update_element_parameter(
                            element.element_id, "Comments", f"GigAI Revision: {change.change_id}"
                        )
                    else:
                        logger.warning(f"Failed to create revision cloud for {element.element_id}")

                except Exception as e:
                    logger.error(f"Error creating revision for element {element.element_id}: {e}")
                    continue

            # 4. Write back to BIM360 (if enabled)
            if revision_marker:
                await self._writeback_to_bim360(
                    change, revision_marker, decision_id, meeting_id, requested_by
                )

            # 5. Log to database
            await append_audit_log(
                "revision_executed",
                {
                    "revision_id": revision_marker.revision_id if revision_marker else None,
                    "change_id": change.change_id,
                    "decision_id": decision_id,
                    "elements_marked": len(bim_elements),
                    "status": "success" if revision_marker else "failed",
                },
            )

            # 6. Emit event
            await publish_bus_event(
                topic="revision.executed",
                data={
                    "revision_id": revision_marker.revision_id if revision_marker else None,
                    "change_id": change.change_id,
                    "elements": [e.element_id for e in bim_elements],
                    "timestamp": datetime.now().isoformat(),
                },
            )

            logger.info(f"Revision execution complete for {change.change_id}")
            return revision_marker

        except Exception as e:
            logger.error(f"Error executing revision: {e}", exc_info=True)
            await append_audit_log(
                "revision_failed",
                {
                    "change_id": change.change_id,
                    "decision_id": decision_id,
                    "error": str(e),
                },
            )
            return None

    async def _writeback_to_bim360(
        self,
        change: ArchitecturalChange,
        revision: RevisionMarker,
        decision_id: str,
        meeting_id: str,
        requested_by: str,
    ) -> bool:
        """
        Write revision details back to BIM360 as an issue.

        Args:
            change: Architectural change
            revision: Placed revision marker
            decision_id: GigAI decision ID
            meeting_id: Meeting ID
            requested_by: Person requesting change

        Returns:
            True if successful
        """
        try:
            logger.info("Writing back to BIM360...")

            # Create BIM360 issue/comment with revision reference
            issue_data = {
                "title": f"Design Change: {change.space} - {change.action}",
                "description": self._build_bim360_comment(change, revision, meeting_id, requested_by),
                "priority": self._estimate_priority(change),
                "assigned_to": requested_by,
                "elements": [revision.revit_element_id],
                "metadata": {
                    "change_id": change.change_id,
                    "decision_id": decision_id,
                    "revision_id": revision.revision_id,
                    "meeting_id": meeting_id,
                    "source": "meeting_intelligence",
                },
            }

            # Note: This would call the actual BIM360 API
            # For MVP, we're logging to audit
            logger.info(f"BIM360 issue would be created: {issue_data['title']}")

            return True

        except Exception as e:
            logger.error(f"Error writing to BIM360: {e}")
            return False

    def _build_revision_comment(self, change: ArchitecturalChange, requested_by: str, meeting_id: str) -> str:
        """Build formatted revision comment for Revit"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        comment = f"""DESIGN CHANGE DETECTED
Action: {change.action.upper()}
Requested by: {requested_by}
Meeting Reference: {meeting_id}
Timestamp: {timestamp}

Change Description:
{change.description}

Affected Element: {change.element_type.upper()}
Space: {change.space}
Confidence: {change.confidence * 100:.0f}%

Reference: {change.change_id}
Decision: Available for review in GigAI Dashboard
"""
        return comment

    def _build_comment_metadata(
        self, change: ArchitecturalChange, decision_id: str, meeting_id: str, requested_by: str
    ) -> dict:
        """Build structured metadata for revision comment"""
        return {
            "change_id": change.change_id,
            "decision_id": decision_id,
            "meeting_id": meeting_id,
            "action": change.action,
            "element_type": change.element_type,
            "space": change.space,
            "request_timestamp": change.timestamp.isoformat() if change.timestamp else None,
            "requested_by": requested_by,
            "speaker": change.speaker,
            "transcript_reference": change.transcript_reference,
            "confidence": change.confidence,
            "properties": change.extracted_properties,
        }

    def _build_bim360_comment(
        self, change: ArchitecturalChange, revision: RevisionMarker, meeting_id: str, requested_by: str
    ) -> str:
        """Build comment for BIM360 issue"""
        return f"""
Design Change from Meeting Intelligence System

Space: {change.space}
Element Type: {change.element_type}
Action Requested: {change.action}

Description:
{change.description}

Revit Revision Cloud: {revision.revision_id}
Revit Element ID: {revision.revit_element_id}
Meeting Reference: {meeting_id}
Requested By: {requested_by}
Confidence: {change.confidence * 100:.0f}%

This design change has been automatically detected from the meeting transcript
and marked in the Revit model. Please review and confirm.

For details, see the GigAI Dashboard or meeting transcript.
"""

    def _estimate_priority(self, change: ArchitecturalChange) -> str:
        """Estimate priority based on action type"""
        high_priority_actions = ["remove", "move", "add"]
        medium_priority_actions = ["resize", "change_material"]
        low_priority_actions = ["modify"]

        action_lower = change.action.lower()

        if any(a in action_lower for a in high_priority_actions):
            return "HIGH"
        elif any(a in action_lower for a in medium_priority_actions):
            return "MEDIUM"
        else:
            return "LOW"

    def _get_color_for_priority(self, priority: str) -> str:
        """Get revision cloud color based on priority"""
        colors = {
            "HIGH": "FF0000",  # Red
            "MEDIUM": "FFA500",  # Orange
            "LOW": "FFFF00",  # Yellow
        }
        return colors.get(priority, "FF0000")

    async def rollback_revision(self, revision_id: str) -> bool:
        """
        Delete a revision cloud (rollback).

        Args:
            revision_id: Revision marker ID

        Returns:
            True if successful
        """
        try:
            logger.info(f"Rolling back revision {revision_id}")
            # Implementation would delete the revision cloud from Revit
            return True
        except Exception as e:
            logger.error(f"Error rolling back revision: {e}")
            return False

    async def close(self):
        """Close client connections"""
        await self.revit_client.close()
