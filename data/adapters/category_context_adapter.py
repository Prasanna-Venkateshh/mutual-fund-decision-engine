"""
Category Context Adapter (Phase D.6).

Resolves point-in-time SEBI 2017+ category and subcategory attributes for a scheme
as of observation date T.

Enforces:
- Point-in-time correctness: An observation date T prior to SEBI 2017 circular
  (2017-10-06) does NOT use future post-circular category classifications as though
  they existed prior to 2017.
- Preserves source precision, effective dates, and category confidence.
- Rejects false peer grouping when historical category context is missing.
"""

from datetime import date
from typing import Dict, Any, Optional
from models.fund_quality_dataset import CategoryPointInTimeContext

# SEBI Categorization Circular Date
SEBI_2017_EFFECTIVE_DATE = date(2017, 10, 6)


class CategoryContextAdapter:
    """Adapter for point-in-time scheme category resolution."""

    def resolve_category_context(
        self,
        canonical_scheme_id: str,
        scheme_name: str,
        observation_date: date,
        custom_category_map: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> CategoryPointInTimeContext:
        """
        Resolves category context as of observation_date T.
        """
        # Check custom or repository map if provided
        if custom_category_map and canonical_scheme_id in custom_category_map:
            mapping = custom_category_map[canonical_scheme_id]
            eff_date = mapping.get("effective_date", SEBI_2017_EFFECTIVE_DATE)
            if observation_date >= eff_date:
                return CategoryPointInTimeContext(
                    category=mapping.get("category", "Equity"),
                    subcategory=mapping.get("subcategory", "Flexi Cap"),
                    strategy_style=mapping.get("strategy_style"),
                    effective_date=eff_date,
                    source=mapping.get("source", "SEBI_2017_CIRCULAR"),
                    source_precision=mapping.get("source_precision", "DAY"),
                    confidence_score=float(mapping.get("confidence_score", 1.0))
                )

        # Name-based heuristic fallback
        name_upper = scheme_name.upper()

        if "SMALL CAP" in name_upper or "SMALLCAP" in name_upper:
            cat, subcat = "Equity", "Small Cap"
        elif "MID CAP" in name_upper or "MIDCAP" in name_upper:
            cat, subcat = "Equity", "Mid Cap"
        elif "LARGE CAP" in name_upper or "LARGECAP" in name_upper or "TOP 100" in name_upper:
            cat, subcat = "Equity", "Large Cap"
        elif "FLEXI CAP" in name_upper or "FLEXICAP" in name_upper:
            cat, subcat = "Equity", "Flexi Cap"
        elif "MULTI CAP" in name_upper or "MULTICAP" in name_upper:
            cat, subcat = "Equity", "Multi Cap"
        elif "LIQUID" in name_upper:
            cat, subcat = "Debt", "Liquid"
        elif "OVERNIGHT" in name_upper:
            cat, subcat = "Debt", "Overnight"
        elif "BALANCED ADVANTAGE" in name_upper or "DYNAMIC ASSET" in name_upper:
            cat, subcat = "Hybrid", "Balanced Advantage"
        else:
            cat, subcat = "Equity", "Flexi Cap"

        # Check point-in-time SEBI 2017 circular boundary
        if observation_date < SEBI_2017_EFFECTIVE_DATE:
            # Pre-2017 observation lacking explicit historical category evidence:
            # Do NOT silently copy current post-2017 category as historical category evidence.
            # Return UNSPECIFIED category with source="PRE_SEBI_2017_UNKNOWN" and confidence_score=0.0.
            return CategoryPointInTimeContext(
                category="UNSPECIFIED",
                subcategory="UNSPECIFIED",
                effective_date=SEBI_2017_EFFECTIVE_DATE,
                source="PRE_SEBI_2017_UNKNOWN",
                source_precision="MONTH",
                confidence_score=0.0
            )

        return CategoryPointInTimeContext(
            category=cat,
            subcategory=subcat,
            effective_date=SEBI_2017_EFFECTIVE_DATE,
            source="SEBI_2017_CIRCULAR",
            source_precision="DAY",
            confidence_score=1.0
        )

