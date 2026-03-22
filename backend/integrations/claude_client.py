import json
from anthropic import Anthropic
from config import settings


class ClaudeClient:
    def __init__(self):
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    # -------------------------------------------------------------------------
    # RFI-based extraction (primary workflow)
    # -------------------------------------------------------------------------

    async def extract_from_rfi(self, rfi_data: dict) -> dict:
        """
        Claude Haiku — fast structured extraction from an ACC RFI.
        Returns a normalised material-change dict.
        """
        rfi_text = (
            f"Title: {rfi_data.get('title', '')}\n"
            f"Description: {rfi_data.get('description', '')}"
        )

        prompt = f"""You are a construction coordinator assistant. Extract material change details from this RFI.

RFI Content:
{rfi_text}

Return a JSON object with these fields:
- location: where in the building / which rooms or areas (string)
- material_from: original / current material being replaced (string)
- material_to: new material requested (string)
- quantity: number of elements to change (number, 0 if not stated)
- element_ids: list of specific element IDs or descriptions if mentioned (array of strings)
- cost_estimate_eur: estimated cost delta in EUR (number, 0 if unknown)
- urgency: "low" | "medium" | "high"
- summary: one-sentence summary of the change (string)
- relevant: true if this describes a material change, false otherwise (boolean)

Return only valid JSON, no markdown."""

        response = self.client.messages.create(
            model=settings.CLAUDE_HAIKU_MODEL,
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        return _parse_json(response.content[0].text)

    # -------------------------------------------------------------------------
    # Proposal generation from RFI context (primary workflow)
    # -------------------------------------------------------------------------

    async def generate_proposal_from_rfi(self, context: dict) -> dict:
        """
        Claude Sonnet — generates a comprehensive change proposal from RFI data
        and enriched project context.
        """
        prompt = f"""You are an expert construction coordinator AI. Generate a detailed material change proposal.

Input context:
{json.dumps(context, indent=2)}

Produce a JSON proposal with exactly these fields:
- title: concise title, e.g. "Material Change: PVC → Aluminum Porthole Windows" (string)
- summary: 2-3 sentence executive summary covering what changes, why, and the impact (string)
- material_change: object with {{from, to, quantity, unit, affected_areas}} describing the change
- cost_analysis: object with:
    - old_unit_cost_eur: cost per unit of original material (number)
    - new_unit_cost_eur: cost per unit of new material (number)
    - quantity: number of units (number)
    - total_delta_eur: total cost difference — positive = more expensive (number)
    - breakdown: array of {{item, cost_eur}} line items
- confidence_factors: object with {{data_completeness, cost_certainty, specification_clarity, historical_precedent}} each 0.0–1.0
- justification: why this change makes sense (string)
- risks: array of risk strings (max 4)
- recommendation: "approve" | "review" | "reject"
- linked_rfi_id: the source RFI id from context (string)

Return only valid JSON, no markdown."""

        response = self.client.messages.create(
            model=settings.CLAUDE_SONNET_MODEL,
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        return _parse_json(response.content[0].text)

    # -------------------------------------------------------------------------
    # Legacy transcript-based methods (kept for backwards compatibility)
    # -------------------------------------------------------------------------

    async def extract_with_haiku(self, transcript: str) -> dict:
        """Legacy: extract from meeting transcript."""
        prompt = f"""Extract material change details from this construction meeting transcript.

Transcript:
{transcript}

Return a JSON object with these fields:
- location: where in the building (string)
- material_from: original material being replaced (string)
- material_to: new material requested (string)
- quantity: number of elements (number)
- elements: list of specific element descriptions (array of strings)
- cost_estimate: estimated cost in EUR (number, 0 if unknown)
- urgency: "low" | "medium" | "high"
- participants: list of people mentioned (array of strings)
- summary: one-sentence summary of the change (string)

Return only valid JSON, no markdown."""

        response = self.client.messages.create(
            model=settings.CLAUDE_HAIKU_MODEL,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        return _parse_json(response.content[0].text)

    async def generate_proposal_with_sonnet(self, context: dict) -> dict:
        """Legacy: generate proposal from transcript extraction."""
        prompt = f"""You are an AI construction coordinator. Generate a complete change proposal.

Context:
{json.dumps(context, indent=2)}

Generate a JSON proposal with:
- title: concise proposal title (string)
- summary: 2-3 sentence executive summary (string)
- cost_analysis: object with {{total_eur, breakdown: [{{item, cost}}], savings_vs_alternative}}
- confidence_factors: object with {{data_completeness, historical_precedent, cost_certainty, stakeholder_clarity}} (each 0.0-1.0)
- actions: array of 4 actions:
  1. {{type: "email", to: "...", subject: "...", body: "..."}}
  2. {{type: "acc_rfi", title: "...", description: "...", priority: "high"|"medium"|"low"}}
  3. {{type: "calendar", title: "...", description: "...", duration_minutes: 30}}
  4. {{type: "markup", element: "...", comment: "...", layer: "Material Changes"}}
- justification: why this change makes sense (string)
- risks: array of risk strings
- recommendation: "approve" | "review" | "reject"

Return only valid JSON, no markdown."""

        response = self.client.messages.create(
            model=settings.CLAUDE_SONNET_MODEL,
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        return _parse_json(response.content[0].text)


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return {"raw": text, "error": "parse_failed"}
