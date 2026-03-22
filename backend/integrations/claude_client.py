import json
from anthropic import AsyncAnthropic
from config import settings


class ClaudeClient:
    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

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

Rules:
- Read the title and description carefully. Extract what is directly stated or clearly implied.
- material_from / material_to / location: infer from the title if not in the description — these are READABLE from the title, not invented.
  Examples: "Replace Bathroom Floor Tiles" → material_from="bathroom floor tiles", material_to="replacement floor tiles", location="bathroom"
  Examples: "Window Upgrade" → material_from="existing windows", material_to="upgraded windows", location="windows"
- quantity: use null if not specified in the text — never invent a number.
- cost_estimate_eur: always 0 — never estimate a cost.
- Do NOT invent product names, brands, or technical specs not mentioned.
- summary: one factual sentence describing what the RFI asks for.
- relevant: true if this is a material change request.

Return a JSON object with these fields:
- location: area or element type from the RFI (string or null)
- material_from: current material being replaced — read from title/description (string or null)
- material_to: new material requested — read from title/description, or "replacement [element]" if only replacement is implied (string or null)
- quantity: number of elements (number or null — null if not stated)
- element_ids: list of specific element IDs mentioned (array, empty if none)
- cost_estimate_eur: 0 always
- urgency: "low" | "medium" | "high" — default "medium"
- summary: one factual sentence (string)
- relevant: true if this is a material change request (boolean)

Return only valid JSON, no markdown."""

        response = await self.client.messages.create(
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
        prompt = f"""You are an expert construction coordinator AI. Generate a material change proposal based STRICTLY on the RFI data provided.

CRITICAL RULES — follow these exactly:
1. Do NOT invent costs, quantities, or specifications not present in the input.
2. If cost data is missing: set old_unit_cost_eur=0, new_unit_cost_eur=0, total_delta_eur=0, and add {{"item": "Cost not specified in RFI", "cost_eur": 0}} to the breakdown.
3. If quantity is missing: use null and note "Quantity not specified" in affected_areas.
4. Base justification only on what the RFI states — no invented reasoning.
5. Risks must be real risks for this type of change — max 3, be specific.
6. Title format: "Material Change: {{from}} → {{to}}" using actual materials from the RFI.
7. confidence_factors must honestly reflect what data is available — low scores if data is sparse.

Input context:
{json.dumps(context, indent=2)}

Produce a JSON proposal with exactly these fields:
- title: "Material Change: {{from}} → {{to}}" using actual RFI materials (string)
- summary: 2-3 sentences — what changes, why per the RFI, and expected impact (string)
- material_change: object with {{from, to, quantity (null if unknown), unit, affected_areas}}
- cost_analysis: object with:
    - old_unit_cost_eur: 0 if not in RFI (number)
    - new_unit_cost_eur: 0 if not in RFI (number)
    - quantity: from RFI or null (number or null)
    - total_delta_eur: 0 if costs unknown (number)
    - breakdown: [{{"item": "Cost not specified in RFI", "cost_eur": 0}}] if unknown
- confidence_factors: object with {{data_completeness, cost_certainty, specification_clarity, historical_precedent}} each 0.0–1.0 — score honestly, sparse RFI = low scores
- justification: based only on RFI content (string)
- risks: array of specific risks for this change, max 3 (array of strings)
- recommendation: "approve" | "review" | "reject"
- linked_rfi_id: the source RFI id from context (string)

Return only valid JSON, no markdown."""

        response = await self.client.messages.create(
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

        response = await self.client.messages.create(
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

        response = await self.client.messages.create(
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
