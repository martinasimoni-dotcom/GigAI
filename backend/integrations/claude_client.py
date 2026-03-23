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
- material_from, material_to, location: extract aggressively from the title and description.
  A null is only acceptable if the title is completely unintelligible.
  Use these rules in order:
    1. Explicit: description states the materials/location → use those words exactly.
    2. Implicit: title implies a change → infer from the title ("Replace X", "Upgrade Y", "New Z").
    3. Generic pattern: map common construction titles to sensible values
       e.g. "Tile Replacement" → from="existing tiles", to="new tiles", location="tiled area"
       e.g. "Window Upgrade" → from="existing windows", to="upgraded windows", location="windows"
       e.g. "Replace Bathroom Floor Tiles" → from="bathroom floor tiles", to="new floor tiles", location="bathroom"
  NEVER return null for all three fields when a title is present.
- quantity: null if not stated in the text — never invent a number.
- cost_estimate_eur: always 0 — never estimate a cost.
- urgency: "high" if title/description contains urgent/critical/immediate; otherwise "medium".
- Do NOT invent product names, brands, dimensions, or technical specs not mentioned.
- summary: one professional sentence describing what the RFI is requesting.
- relevant: true for any material, system, or finish change request.

Return a JSON object with these fields:
- location: area or element type from the RFI (string or null)
- material_from: current material being replaced — read from title/description (string or null)
- material_to: new material requested — read from title/description, or "replacement [element]" if only replacement is implied (string or null)
- quantity: number of elements (number or null — null if not stated)
- element_ids: list of specific element IDs mentioned (array, empty if none)
- cost_estimate_eur: 0 always
- urgency: "low" | "medium" | "high"
- summary: one professional sentence (string)
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
        prompt = f"""You are a proactive construction advisor AI. Generate a concrete, actionable RFI response that directly answers the question and proposes a specific solution.

RULES:
1. Open with direct_answer: "Yes", "No", or "Yes, with conditions".
2. Always propose a CONCRETE solution — specific material, standard product, or system.
   If the RFI lacks detail, apply construction best practices and state your assumptions
   in the justification. NEVER say "not specified" or "cannot estimate without data".
3. Quantities: use the value from the RFI if present. If missing, propose a sensible
   default based on the location/context and label it:
   "Assumed X units based on [context] — confirm on site."
4. Costs: always provide a concrete estimate using Italian market averages below.
   Format breakdown as: unit_cost × quantity = total.
   End the breakdown with: {{"item": "Note: Final quote required from supplier", "cost_eur": 0}}
   Italian market averages (use as baseline — do not invent figures outside these ranges):
     Wood windows:      €700–900/unit    PVC windows:      €400–600/unit
     Aluminium windows: €500–750/unit    Skylight:         €800–1,200/unit
     Wood doors:        €800–1,500/unit  Interior doors:   €500–1,200/unit
     Porcelain tiles:   €40–60/m²        Ceramic tiles:    €15–25/m²
     Parquet flooring:  €50–80/m²        Laminate:         €20–35/m²
     Plasterboard:      €15–25/m²        Insulation:       €25–45/m²
5. Timeline: realistic construction weeks split into fabrication + installation.
   Typical lead times: bespoke windows/doors 4 wks, standard tiles 1 wk, stock doors 2 wks.
6. Technical specs: include the single most relevant standard for the material type:
   Windows/doors → U-value (W/m²K) + air class | Flooring → slip R-rating + wear class
   Structural → fire rating | Finishes → durability class. Omit irrelevant specs.
7. Revit data is INTERNAL — stored in the database for the Revit plugin only.
   It is NOT displayed in the web dashboard. Provide three dedicated Revit fields:
   - revit_family_primary: best-fit Revit family (standard Autodesk naming)
   - revit_family_alternative: fallback family
   - revit_type_parameters: object with size, material, finish (and other relevant params)
   Reference families:
     Windows: M_Window-Casement-Single, M_Window-Casement-Double, M_Fixed Window, M_Window-Awning, M_Skylight
     Doors:   M_Single-Flush, M_Single-Panel, M_Double-Flush, M_Curtain Wall-Door
     Floors:  Floor-Generic, Floor-Tile, Floor-Wood
8. next_steps: 3–5 ordered actions a coordinator would actually take next.
9. Risks: 2–3 risks specific to this material type and site context.
10. Title: "RFI Response: {{short question summary}}"
11. confidence_factors scoring:
    Title + description + materials → 0.75–0.85 | Title + partial desc → 0.60–0.75
    Title only, clear intent → 0.50–0.65 | Vague title → 0.30–0.50

Input context:
{json.dumps(context, indent=2)}

Produce a JSON response with exactly these fields:
- title: "RFI Response: {{short question summary}}" (string)
- direct_answer: "Yes" | "No" | "Yes, with conditions" (string)
- summary: 2–3 sentences — open with the recommendation, name the specific solution, state expected impact (string)
- material_change: object with {{from, to, quantity, unit, affected_areas}}
- cost_analysis: object with:
    - old_unit_cost_eur: current material unit cost or 0 (number)
    - new_unit_cost_eur: proposed material unit cost from market averages (number)
    - quantity: from RFI or assumed value (number or null)
    - total_delta_eur: new_unit_cost_eur × quantity (number)
    - breakdown: array of {{item, cost_eur}} including supplier note item
- timeline_weeks: total integer weeks (number)
- timeline_breakdown: object with {{fabrication_weeks, installation_weeks, notes}} (object)
- technical_specs: object of the most relevant key/value specs for this material (object)
- revit_family_primary: best-fit Revit family name [INTERNAL] (string)
- revit_family_alternative: fallback Revit family name [INTERNAL] (string)
- revit_type_parameters: object with size/material/finish params [INTERNAL] (object)
- next_steps: array of 3–5 ordered action strings (array)
- confidence_factors: object with {{data_completeness, cost_certainty, specification_clarity, historical_precedent}} each 0.0–1.0
- justification: concrete reasoning — name the solution, state assumptions, explain why (string)
- risks: array of 2–3 material-specific risk strings (array)
- recommendation: "approve" | "approve_with_conditions" | "review_required" | "reject"
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
