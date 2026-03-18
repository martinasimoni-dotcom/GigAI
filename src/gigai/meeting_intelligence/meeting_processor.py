"""
Meeting Event Processor

Orchestrates the meeting intelligence workflow:
1. Fetches meeting transcript from Fireflies
2. Extracts architectural changes
3. Maps to BIM elements
4. Generates tasks and minutes
5. Integrates with GigAI decision pipeline
"""

import json
import logging
from datetime import datetime
from typing import Optional

from ..fireflies_stt import resolve_fireflies_transcript
from ..storage import append_audit_log, publish_bus_event
from .models import (
    ArchitecturalChange,
    MeetingContext,
    MeetingIntelligenceResult,
)
from .architectural_parser import ArchitecturalNLPParser
from .bim_identifier import BIMElementIdentifier

logger = logging.getLogger(__name__)


class MeetingEventProcessor:
    """
    Process meeting transcripts through the Meeting Intelligence pipeline.
    Integrates with existing GigAI infrastructure.
    """

    def __init__(self):
        """Initialize processor with dependencies"""
        self.parser = ArchitecturalNLPParser()
        self.bim_identifier = BIMElementIdentifier()

    async def process_meeting_from_fireflies(
        self, fireflies_meeting_id: str, project_id: str, project_name: str
    ) -> MeetingIntelligenceResult:
        """
        Process a meeting from Fireflies API.

        Args:
            fireflies_meeting_id: Meeting ID from Fireflies
            project_id: GigAI project identifier
            project_name: Project name

        Returns:
            Complete meeting intelligence result
        """
        start_time = datetime.now()

        try:
            # 1. Fetch transcript from Fireflies
            logger.info(f"Fetching transcript for meeting: {fireflies_meeting_id}")
            transcript_response = await resolve_fireflies_transcript(fireflies_meeting_id)

            transcript_text = transcript_response.get("transcript", "")
            meeting_title = transcript_response.get("title", "Meeting")
            participants = transcript_response.get("participants", [])
            meeting_date = transcript_response.get("date", datetime.now())

            # Create meeting context
            meeting_context = MeetingContext(
                meeting_id=f"meet_{datetime.now().timestamp()}",
                fireflies_meeting_id=fireflies_meeting_id,
                title=meeting_title,
                project_id=project_id,
                project_name=project_name,
                date=meeting_date,
                duration_minutes=transcript_response.get("duration", 45),
                participants=participants,
                transcript_text=transcript_text,
                transcript_url=transcript_response.get("url"),
            )

            logger.info(f"Meeting context created: {meeting_context.meeting_id}")

            # 2. Extract architectural changes
            logger.info("Extracting architectural changes...")
            architectural_changes = self.parser.parse_transcript(
                transcript_text, project_id, meeting_context.meeting_id
            )

            warnings = []
            if not architectural_changes:
                warnings.append("No architectural changes detected in transcript")

            # 3. Identify BIM elements
            logger.info(f"Identifying {len(architectural_changes)} BIM elements...")
            identified_elements = []
            for change in architectural_changes:
                try:
                    elements = self.bim_identifier.find_elements_for_change(change)
                    identified_elements.extend(elements)
                    change.affected_elements = [e.element_id for e in elements]
                except Exception as e:
                    logger.warning(f"Error identifying elements for {change.space}: {e}")
                    warnings.append(f"Could not identify elements for {change.space}")

            # 4. Generate meeting minutes (basic version)
            meeting_summary = self._generate_summary(architectural_changes, participants)

            # Build result
            result = MeetingIntelligenceResult(
                meeting_id=meeting_context.meeting_id,
                meeting_context=meeting_context,
                architectural_changes=architectural_changes,
                identified_elements=identified_elements,
                task_assignments=[],  # Will be populated by task assigner
                revision_markers=[],  # Will be populated by revision executor
                processing_time_seconds=(datetime.now() - start_time).total_seconds(),
                success=True,
                warnings=warnings,
            )

            # 5. Emit event to bus
            await publish_bus_event(
                topic="meeting.processed",
                data={
                    "meeting_id": meeting_context.meeting_id,
                    "changes_detected": len(architectural_changes),
                    "project_id": project_id,
                },
            )

            # Audit log
            await append_audit_log(
                "meeting_processed",
                {
                    "meeting_id": meeting_context.meeting_id,
                    "changes": len(architectural_changes),
                    "elements": len(identified_elements),
                },
            )

            logger.info(f"Meeting processing complete: {len(architectural_changes)} changes detected")
            return result

        except Exception as e:
            logger.error(f"Error processing meeting: {e}", exc_info=True)
            return MeetingIntelligenceResult(
                meeting_id=f"meet_{datetime.now().timestamp()}",
                meeting_context=MeetingContext(
                    meeting_id="unknown",
                    title="Error Processing Meeting",
                    project_id=project_id,
                    project_name=project_name,
                    date=datetime.now(),
                    duration_minutes=0,
                ),
                processing_time_seconds=(datetime.now() - start_time).total_seconds(),
                success=False,
                errors=[str(e)],
            )

    async def process_meeting_from_transcript(
        self, transcript_text: str, project_id: str, project_name: str, title: str = "Manual Transcript"
    ) -> MeetingIntelligenceResult:
        """
        Process a meeting from raw transcript text.

        Args:
            transcript_text: Full meeting transcript
            project_id: Project identifier
            project_name: Project name
            title: Meeting title

        Returns:
            Complete meeting intelligence result
        """
        start_time = datetime.now()

        try:
            # Create meeting context
            meeting_context = MeetingContext(
                meeting_id=f"meet_{datetime.now().timestamp()}",
                title=title,
                project_id=project_id,
                project_name=project_name,
                date=datetime.now(),
                duration_minutes=45,  # Estimate
                transcript_text=transcript_text,
            )

            # Extract changes
            logger.info("Extracting architectural changes from transcript...")
            architectural_changes = self.parser.parse_transcript(
                transcript_text, project_id, meeting_context.meeting_id
            )

            # Identify elements
            logger.info(f"Identifying BIM elements for {len(architectural_changes)} changes...")
            identified_elements = []
            for change in architectural_changes:
                try:
                    elements = self.bim_identifier.find_elements_for_change(change)
                    identified_elements.extend(elements)
                    change.affected_elements = [e.element_id for e in elements]
                except Exception as e:
                    logger.warning(f"Error identifying elements: {e}")

            # Build result
            result = MeetingIntelligenceResult(
                meeting_id=meeting_context.meeting_id,
                meeting_context=meeting_context,
                architectural_changes=architectural_changes,
                identified_elements=identified_elements,
                processing_time_seconds=(datetime.now() - start_time).total_seconds(),
                success=True,
            )

            logger.info(f"Transcript processing complete: {len(architectural_changes)} changes")
            return result

        except Exception as e:
            logger.error(f"Error processing transcript: {e}", exc_info=True)
            return MeetingIntelligenceResult(
                meeting_id=f"meet_{datetime.now().timestamp()}",
                meeting_context=MeetingContext(
                    meeting_id="unknown",
                    title=title,
                    project_id=project_id,
                    project_name=project_name,
                    date=datetime.now(),
                    duration_minutes=0,
                ),
                processing_time_seconds=(datetime.now() - start_time).total_seconds(),
                success=False,
                errors=[str(e)],
            )

    def _generate_summary(self, changes: list[ArchitecturalChange], participants: list[str]) -> str:
        """Generate basic meeting summary from changes"""
        if not changes:
            return "No architectural changes identified in meeting."

        summary_lines = [f"Meeting summary with {len(changes)} design changes:"]

        # Group by space
        by_space = {}
        for change in changes:
            if change.space not in by_space:
                by_space[change.space] = []
            by_space[change.space].append(change)

        for space, space_changes in by_space.items():
            summary_lines.append(f"\n{space}:")
            for change in space_changes:
                summary_lines.append(f"  - {change.action}: {change.description}")

        summary_lines.append(f"\nParticipants: {', '.join(participants)}")

        return "\n".join(summary_lines)

    def extract_participants(self, transcript_text: str) -> list[str]:
        """Extract speaker names from transcript"""
        speakers = set()

        lines = transcript_text.split("\n")
        for line in lines:
            # Look for "Speaker: text" pattern
            if ": " in line:
                speaker = line.split(":")[0].strip()
                if speaker and not speaker.lower().startswith("note"):
                    speakers.add(speaker)

        return list(speakers)
