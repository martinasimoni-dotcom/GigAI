"""
Normalization Service — Claude Haiku extracts structured data from RFIs or transcripts.
"""
from integrations.claude_client import ClaudeClient


class NormalizationService:
    def __init__(self):
        self.claude = ClaudeClient()

    async def extract_from_rfi(self, rfi_data: dict) -> dict:
        """Extract material change details from an ACC RFI dict."""
        extracted = await self.claude.extract_from_rfi(rfi_data)
        extracted["source"] = "rfi"
        return extracted

    async def extract(self, transcript: str) -> dict:
        """Legacy: Extract material change details from a meeting transcript."""
        keywords = [
            "material", "change", "replace", "upgrade", "switch",
            "porthole", "window", "door", "floor", "wall", "ceiling",
            "PVC", "wood", "concrete", "steel", "glass", "tile",
        ]
        lower = transcript.lower()
        if not any(kw.lower() in lower for kw in keywords):
            return {"relevant": False, "reason": "No material change keywords found"}

        extracted = await self.claude.extract_with_haiku(transcript)
        extracted["relevant"] = True
        extracted["source_length"] = len(transcript)
        return extracted

    def is_actionable(self, extracted: dict) -> bool:
        """Check if the extracted data has enough info to generate a proposal."""
        if not extracted.get("relevant", True):  # RFI extractions don't set relevant=False
            return False
        required = ["location", "material_from", "material_to"]
        return all(extracted.get(f) for f in required)

    def is_rfi_actionable(self, extracted: dict) -> bool:
        """Looser check for RFI extractions — material_from + material_to is enough."""
        if extracted.get("relevant") is False:
            return False
        return bool(extracted.get("material_from") and extracted.get("material_to"))
