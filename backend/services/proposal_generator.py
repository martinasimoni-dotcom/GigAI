"""
Proposal Generator — Claude Sonnet creates rich proposals from RFI or transcript data.
"""
import uuid
from datetime import datetime
from integrations.claude_client import ClaudeClient
from integrations.acc_client import ACCClient


class ProposalGenerator:
    def __init__(self):
        self.claude = ClaudeClient()
        self.acc = ACCClient()

    # -------------------------------------------------------------------------
    # Primary: generate from ACC RFI
    # -------------------------------------------------------------------------

    async def generate_from_rfi(
        self,
        rfi_data: dict,
        extracted: dict,
        assigned_user_email: str | None = None,
    ) -> dict:
        """Generate a full proposal from an ACC RFI and its Haiku extraction."""
        project_context = await self.acc.get_project_context(
            rfi_data.get("projectId")
        )

        context = {
            "source": "acc_rfi",
            "rfi": {
                "id": rfi_data.get("id"),
                "title": rfi_data.get("title"),
                "description": rfi_data.get("description"),
                "assigned_to": rfi_data.get("assignedTo"),
                "assigned_email": assigned_user_email,
                "created_at": rfi_data.get("createdAt"),
            },
            "project": project_context,
            "extracted_change": extracted,
            "timestamp": datetime.utcnow().isoformat(),
        }

        proposal_data = await self.claude.generate_proposal_from_rfi(context)

        proposal_id = str(uuid.uuid4())
        cost = self._extract_cost_rfi(proposal_data)
        confidence = self._extract_confidence(proposal_data)

        return {
            "id": proposal_id,
            "title": proposal_data.get(
                "title",
                f"Material Change: {extracted.get('material_from', '?')} → {extracted.get('material_to', '?')}",
            ),
            "summary": proposal_data.get("summary", ""),
            "status": "pending",
            "confidence": confidence,
            "cost": cost,
            "actions": [],  # actions are executed individually via dashboard buttons
            "extracted": extracted,
            "proposal_data": proposal_data,
            "source_rfi_id": rfi_data.get("id"),
            "acc_project_id": rfi_data.get("projectId") or self.acc.project_id,
            "assigned_user_email": assigned_user_email,
        }

    # -------------------------------------------------------------------------
    # Legacy: generate from transcript extraction
    # -------------------------------------------------------------------------

    async def generate(self, extracted: dict, meeting_title: str = "Meeting") -> dict:
        """Legacy: Generate a full proposal from extracted transcript data."""
        project_info = await self.acc.get_project_info()

        context = {
            "meeting_title": meeting_title,
            "project": project_info,
            "change": extracted,
            "timestamp": datetime.utcnow().isoformat(),
        }

        proposal_data = await self.claude.generate_proposal_with_sonnet(context)
        proposal_id = str(uuid.uuid4())
        cost = self._extract_cost_legacy(proposal_data)
        confidence = self._extract_confidence(proposal_data)

        return {
            "id": proposal_id,
            "title": proposal_data.get(
                "title",
                f"Material Change: {extracted.get('material_from', 'Unknown')} → {extracted.get('material_to', 'Unknown')}",
            ),
            "summary": proposal_data.get("summary", ""),
            "status": "pending",
            "confidence": confidence,
            "cost": cost,
            "actions": proposal_data.get("actions", []),
            "extracted": extracted,
            "proposal_data": proposal_data,
        }

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _extract_cost_rfi(self, proposal_data: dict) -> float:
        try:
            ca = proposal_data.get("cost_analysis", {}) or {}
            delta = ca.get("total_delta_eur") or ca.get("total_eur", 0)
            return float(abs(delta))
        except (TypeError, ValueError):
            return 0.0

    def _extract_cost_legacy(self, proposal_data: dict) -> float:
        try:
            ca = proposal_data.get("cost_analysis", {}) or {}
            return float(ca.get("total_eur", 0))
        except (TypeError, ValueError):
            return 0.0

    def _extract_confidence(self, proposal_data: dict) -> float:
        try:
            factors = proposal_data.get("confidence_factors", {}) or {}
            if not factors:
                return 0.75
            values = [v for v in factors.values() if isinstance(v, (int, float))]
            return round(sum(values) / len(values), 2) if values else 0.75
        except Exception:
            return 0.75
