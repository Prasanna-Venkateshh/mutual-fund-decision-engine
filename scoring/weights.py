"""
Category-Family Weight Manager & Dynamic Downside Adjuster (Phase E).

Manages V1 category-family fixed weight resolution and bounded objective
downside importance adjustments.

Enforces:
- Weights sum to exactly 100.0%.
- Objective category/subcategory context ONLY (NO investor risk tolerance inside Fund Quality).
- Explicit multiplier bounds [0.80, 1.20].
- Deterministic, explainable re-normalization.
"""

from typing import Dict
from scoring.config import CATEGORY_FAMILY_WEIGHTS, DYNAMIC_DOWNSIDE_BOUNDS


class ScoringWeightManager:
    """Manager for category-family fixed weights and bounded dynamic downside scaling."""

    HIGH_VOLATILITY_SUBCATEGORIES = {
        "Small Cap", "Mid Cap", "Sectoral", "Thematic", "SmallCap", "MidCap"
    }

    def resolve_category_family(self, category: str) -> str:
        """Maps category string to category family key."""
        cat_upper = category.upper()
        if "EQUITY" in cat_upper:
            return "Equity"
        elif "DEBT" in cat_upper:
            return "Debt"
        elif "HYBRID" in cat_upper:
            return "Hybrid"
        return "Other"

    def get_dimension_weights(
        self,
        category: str,
        subcategory: str
    ) -> Dict[str, float]:
        """
        Resolves dimension weights for a category and subcategory.
        Applies dynamic downside scaling if subcategory is high-volatility,
        re-normalizing weights so they sum to 100.0%.
        """
        family = self.resolve_category_family(category)
        base = dict(CATEGORY_FAMILY_WEIGHTS.get(family, CATEGORY_FAMILY_WEIGHTS["Other"]))

        # Check objective dynamic downside scaling
        multiplier = 1.0
        if any(h.upper() in subcategory.upper() for h in self.HIGH_VOLATILITY_SUBCATEGORIES):
            multiplier = DYNAMIC_DOWNSIDE_BOUNDS["high_volatility_multiplier"]

        # Clamp multiplier within bounds [0.80, 1.20]
        multiplier = max(
            DYNAMIC_DOWNSIDE_BOUNDS["min_multiplier"],
            min(DYNAMIC_DOWNSIDE_BOUNDS["max_multiplier"], multiplier)
        )

        if multiplier != 1.0 and "downside_risk" in base:
            # Scale downside risk weight
            base["downside_risk"] = round(base["downside_risk"] * multiplier, 2)
            # Re-normalize so sum equals 100.0%
            total_sum = sum(base.values())
            for key in base:
                base[key] = round((base[key] / total_sum) * 100.0, 2)

        return base
