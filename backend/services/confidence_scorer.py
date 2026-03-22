"""
Confidence Scorer — Evaluates proposal confidence against the 80% threshold.
"""
from config import settings


class ConfidenceScorer:
    THRESHOLD = settings.CONFIDENCE_AUTO_APPROVE_THRESHOLD

    def score(self, proposal_data: dict, extracted: dict) -> float:
        """
        Calculate confidence score from multiple factors.
        Returns a float between 0.0 and 1.0.
        """
        factors = {}

        # 1. Data completeness (from extraction)
        required_fields = ["location", "material_from", "material_to", "quantity"]
        filled = sum(1 for f in required_fields if extracted.get(f))
        factors["data_completeness"] = filled / len(required_fields)

        # 2. Cost certainty
        cost = proposal_data.get("cost_analysis", {}).get("total_eur", 0)
        factors["cost_certainty"] = 0.9 if cost > 0 else 0.5

        # 3. Use Claude's own confidence factors if available
        claude_factors = proposal_data.get("confidence_factors", {})
        if claude_factors:
            for k, v in claude_factors.items():
                if isinstance(v, (int, float)):
                    factors[f"claude_{k}"] = float(v)

        # 4. Historical precedent (simplified — will use pgvector later)
        factors["historical_precedent"] = 0.85  # placeholder

        # Weighted average
        weights = {
            "data_completeness": 0.25,
            "cost_certainty": 0.20,
            "historical_precedent": 0.15,
        }
        # Claude factors weighted together at 0.40
        claude_keys = [k for k in factors if k.startswith("claude_")]
        if claude_keys:
            claude_avg = sum(factors[k] for k in claude_keys) / len(claude_keys)
            factors["claude_avg"] = claude_avg
            weights["claude_avg"] = 0.40

        total_weight = sum(weights.get(k, 0) for k in factors)
        if total_weight == 0:
            return 0.75

        score = sum(factors[k] * weights.get(k, 0) for k in factors if k in weights)
        return round(min(score / total_weight, 1.0), 2)

    def is_auto_approvable(self, confidence: float) -> bool:
        return confidence >= self.THRESHOLD

    def label(self, confidence: float) -> str:
        if confidence >= 0.90:
            return "very_high"
        if confidence >= self.THRESHOLD:
            return "high"
        if confidence >= 0.60:
            return "medium"
        return "low"
