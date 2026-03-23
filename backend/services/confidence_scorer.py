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

        # 1. Data completeness — core fields (location, material_from, material_to) are primary;
        #    quantity is a bonus since RFIs routinely omit it.
        core_fields = ["location", "material_from", "material_to"]
        core_filled = sum(1 for f in core_fields if extracted.get(f))
        base = core_filled / len(core_fields)
        bonus = 0.10 if extracted.get("quantity") else 0.0
        factors["data_completeness"] = min(base + bonus * base, 1.0)

        # 2. Cost certainty — softer penalty when absent; RFIs routinely omit costs.
        cost_analysis = proposal_data.get("cost_analysis") or {}
        total_delta = cost_analysis.get("total_delta_eur", 0)
        factors["cost_certainty"] = 0.90 if total_delta and total_delta > 0 else 0.70

        # 3. Use Claude's own confidence factors if available
        claude_factors = proposal_data.get("confidence_factors", {})
        if claude_factors:
            for k, v in claude_factors.items():
                if isinstance(v, (int, float)):
                    factors[f"claude_{k}"] = float(v)

        # 4. Historical precedent (simplified — will use pgvector later)
        factors["historical_precedent"] = 0.85  # placeholder

        # Weighted average — data_completeness raised to 0.30; claude_avg reduced to 0.35
        weights = {
            "data_completeness": 0.30,
            "cost_certainty": 0.20,
            "historical_precedent": 0.15,
        }
        claude_keys = [k for k in factors if k.startswith("claude_")]
        if claude_keys:
            claude_avg = sum(factors[k] for k in claude_keys) / len(claude_keys)
            factors["claude_avg"] = claude_avg
            weights["claude_avg"] = 0.35

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
