"""
Meeting Decision Agent

Integrates Meeting Intelligence with GigAI Decision Pipeline.

Flow:
  Meeting Transcript → Architectural Changes → Agent Proposals → Decision Package
  Decision Package → Authority Check (auto/manual) → Execution → Revit Revision
"""

import logging
from datetime import datetime
from typing import Optional

from .models import ArchitecturalChange, MeetingIntelligenceResult
from ..models import AgentOutput, DecisionPackage
from ..agents import MeetingAgent

logger = logging.getLogger(__name__)


class DesignChangeAgent:
    """
    Specialized agent for architectural design changes.
    Extends existing MeetingAgent with design-specific logic.
    """

    def __init__(self):
        """Initialize design change agent"""
        self.meeting_agent = MeetingAgent()

    def analyze_changes(self, meeting_result: MeetingIntelligenceResult) -> AgentOutput:
        """
        Analyze architectural changes and generate proposals.

        Args:
            meeting_result: Complete meeting intelligence result

        Returns:
            Agent output with proposals and risk assessment
        """
        if not meeting_result.architectural_changes:
            return AgentOutput(
                agent="DesignChangeAgent",
                summary="No architectural changes detected in meeting",
                proposals=[],
                risk_signals=[],
                confidence=0.0,
            )

        proposals = []
        risk_signals = []
        citations = []

        # Analyze each architectural change
        for i, change in enumerate(meeting_result.architectural_changes):
            proposal = self._generate_change_proposal(change)
            proposals.append(proposal)

            # Assess risks
            risks = self._assess_risks(change, meeting_result)
            risk_signals.extend(risks)

            # Add citations
            if change.speaker:
                citations.append(f"Meeting transcript ({change.transcript_reference}): {change.speaker}")

        # Calculate overall confidence
        confidence = sum(c.confidence for c in meeting_result.architectural_changes) / len(
            meeting_result.architectural_changes
        )

        # Generate summary
        summary = f"Detected {len(proposals)} design changes from meeting. " \
                  f"Average confidence: {confidence:.0%}. " \
                  f"Risk signals: {len(risk_signals)}"

        return AgentOutput(
            agent="DesignChangeAgent",
            summary=summary,
            proposals=proposals,
            risk_signals=risk_signals,
            confidence=confidence,
            citations=citations,
        )

    def _generate_change_proposal(self, change: ArchitecturalChange) -> str:
        """Generate a proposal string from architectural change"""
        return (
            f"Apply design change to {change.space}: "
            f"{change.action.upper()} {change.element_type} "
            f"({change.description}). "
            f"Requested by: {change.speaker}. "
            f"Confidence: {change.confidence:.0%}"
        )

    def _assess_risks(self, change: ArchitecturalChange, meeting_result: MeetingIntelligenceResult) -> list[str]:
        """Assess risks associated with a design change"""
        risks = []

        # Risk: High-impact actions like "remove"
        if change.action.lower() in ["remove", "delete"]:
            risks.append(f"HIGH: Removing {change.element_type} may impact building code compliance")

        # Risk: Moving structural elements
        if change.action.lower() == "move" and change.element_type in ["wall", "column"]:
            risks.append(f"MEDIUM: Moving {change.element_type} requires structural review")

        # Risk: Low confidence detection
        if change.confidence < 0.75:
            risks.append(f"MEDIUM: Change detected with {change.confidence:.0%} confidence, may need verification")

        # Risk: No speaker identified
        if not change.speaker:
            risks.append("LOW: Change detected but speaker not identified")

        # Risk: Multiple changes in same space
        space_changes = [
            c for c in meeting_result.architectural_changes if c.space.lower() == change.space.lower()
        ]
        if len(space_changes) > 2:
            risks.append(
                f"MEDIUM: Multiple changes detected in {change.space}, may indicate redesign or coordination issue"
            )

        return risks

    def build_decision_package(
        self, meeting_result: MeetingIntelligenceResult, agent_output: AgentOutput, meeting_id: str
    ) -> list[DecisionPackage]:
        """
        Build decision packages for each architectural change.

        Args:
            meeting_result: Meeting intelligence result
            agent_output: Agent analysis output
            meeting_id: Meeting identifier

        Returns:
            List of decision packages
        """
        decisions = []

        for i, change in enumerate(meeting_result.architectural_changes):
            # Determine risk level based on action
            risk_level = self._classify_risk_level(change, agent_output.risk_signals)

            # Generate alternatives
            alternatives = self._generate_alternatives(change)

            # Build constraints
            constraints = self._build_constraints(change)

            decision = DecisionPackage(
                decision_id=f"d_{datetime.now().timestamp()}_{i}",
                event_id=meeting_result.meeting_id,
                proposal=self._generate_change_proposal(change),
                alternatives=alternatives,
                confidence=change.confidence,
                risk_level=risk_level,
                constraints=constraints,
                evidence=[{
                    "source": f"Meeting transcript - {meeting_result.meeting_context.title}",
                    "timestamp": change.timestamp.isoformat() if change.timestamp else "",
                    "speaker": change.speaker or "Unknown",
                    "reference": change.transcript_reference,
                }],
            )

            decisions.append(decision)

        return decisions

    def _classify_risk_level(self, change: ArchitecturalChange, risk_signals: list[str]) -> str:
        """Classify overall risk level for a change"""
        # Check for HIGH risk signals
        high_risk_actions = ["remove", "delete", "move"]
        if any(action in change.action.lower() for action in high_risk_actions):
            return "high"

        # Check for MEDIUM risk
        if change.confidence < 0.75:
            return "medium"

        structural_elements = ["wall", "column", "floor", "stair"]
        if change.element_type in structural_elements and change.action.lower() in ["move", "modify"]:
            return "medium"

        # Default to LOW
        return "low"

    def _generate_alternatives(self, change: ArchitecturalChange) -> list[str]:
        """Generate alternative approaches for the change"""
        alternatives = []

        if change.action.lower() == "resize":
            alternatives.append(f"Increase {change.element_type} size gradually (phased approach)")
            alternatives.append(f"Keep current {change.element_type} size and modify adjacent elements")

        elif change.action.lower() == "move":
            alternatives.append(f"Shift {change.element_type} in opposite direction")
            alternatives.append(f"Use flexible system instead of moving {change.element_type}")

        elif change.action.lower() == "change_material":
            alternatives.append("Keep existing material, apply finish/coating instead")
            alternatives.append(f"Use alternative sustainable material for {change.element_type}")

        elif change.action.lower() == "add":
            alternatives.append("Use modular/removable approach instead of permanent installation")

        elif change.action.lower() == "remove":
            alternatives.append("Keep element but disable/hide it temporarily")
            alternatives.append("Replace with lighter/transparent version instead of full removal")

        return alternatives

    def _build_constraints(self, change: ArchitecturalChange) -> list[str]:
        """Build list of constraints that affect the change"""
        constraints = []

        # Structural constraints
        if change.element_type in ["wall", "column", "floor"]:
            constraints.append("Requires structural engineer review and approval")

        # Building code constraints
        constraints.append("Must comply with local building codes and regulations")

        # Schedule constraints
        constraints.append("Must be coordinated with project schedule and construction phasing")

        # Cost impact
        if change.action.lower() in ["add", "change_material"]:
            constraints.append("Potential cost impact - requires budget review")

        # Coordination constraints
        constraints.append("Requires MEP coordination if affecting mechanical/electrical systems")

        # Material lead time
        if change.action.lower() == "change_material":
            constraints.append("Material lead time may impact schedule")

        return constraints


async def integrate_meeting_into_pipeline(
    meeting_result: MeetingIntelligenceResult, orchestrator
) -> list[DecisionPackage]:
    """
    Integrate meeting intelligence result into GigAI decision pipeline.

    Args:
        meeting_result: Complete meeting intelligence output
        orchestrator: GigAI orchestrator instance

    Returns:
        List of generated decision packages
    """
    logger.info(f"Integrating meeting {meeting_result.meeting_id} into pipeline")

    agent = DesignChangeAgent()

    # 1. Analyze changes with agent
    agent_output = agent.analyze_changes(meeting_result)
    logger.info(f"Agent analysis complete: {len(agent_output.proposals)} proposals generated")

    # 2. Build decision packages
    decisions = agent.build_decision_package(meeting_result, agent_output, meeting_result.meeting_id)
    logger.info(f"Decision packages built: {len(decisions)} decisions")

    # 3. Process each decision through orchestrator pipeline
    processed_decisions = []
    for decision in decisions:
        try:
            # This would call the existing orchestrator.process_decision()
            # For now, we're just building the decision packages
            processed_decisions.append(decision)
            logger.info(f"Decision {decision.decision_id} prepared for orchestrator")
        except Exception as e:
            logger.error(f"Error processing decision: {e}")

    return processed_decisions


# Extend the existing agents module
class MeetingAgentExtended(MeetingAgent):
    """
    Extended MeetingAgent with design change detection.
    This is a compatibility layer that wraps DesignChangeAgent.
    """

    def __init__(self):
        """Initialize extended meeting agent"""
        super().__init__()
        self.design_agent = DesignChangeAgent()

    async def analyze_meeting(self, transcript: str, focus_space: Optional[str] = None) -> AgentOutput:
        """
        Analyze meeting transcript with design change detection.

        Args:
            transcript: Meeting transcript
            focus_space: Optional focused space

        Returns:
            Agent output with proposals
        """
        # Use base MeetingAgent logic plus design change detection
        return await super().analyze_meeting(transcript, focus_space)
