"""
AMFI Riskometer Feed Adapter (Phase F.10).

Parses and normalizes raw Riskometer disclosure items into structured dictionaries
keyed by scheme code. Preserves exact published string labels without numeric risk mapping.
"""

from datetime import date
from typing import Dict, List, Any, Optional

ALLOWED_RISKOMETER_LABELS = {
    "LOW", "LOW TO MODERATE", "MODERATE", "MODERATELY HIGH", "HIGH", "VERY HIGH"
}


class RiskometerFeedAdapter:
    """Adapter for ingesting and parsing AMFI Riskometer disclosure feeds."""

    SOURCE_ID = "AMFI_RISKOMETER_FEED"

    def parse_riskometer_feed_items(self, raw_items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Parses raw Riskometer feed dictionaries.
        Returns a dictionary mapping `amfi_code` -> {
            "amfi_code": str,
            "riskometer_label": str,
            "effective_date": date,
            "source_id": str
        }
        """
        risk_map: Dict[str, Dict[str, Any]] = {}
        for item in raw_items:
            scheme_code = str(item.get("scheme_code", "")).strip()
            if not scheme_code or not scheme_code.isdigit():
                continue

            raw_label = item.get("riskometer") or item.get("riskometer_label")
            if not raw_label or not isinstance(raw_label, str):
                continue

            clean_label = raw_label.strip().upper()
            if clean_label not in ALLOWED_RISKOMETER_LABELS:
                continue

            eff_date = item.get("effective_date")
            if isinstance(eff_date, str):
                try:
                    eff_date = date.fromisoformat(eff_date)
                except ValueError:
                    eff_date = None

            risk_map[scheme_code] = {
                "amfi_code": scheme_code,
                "riskometer_label": clean_label,
                "effective_date": eff_date,
                "source_id": self.SOURCE_ID
            }

        return risk_map
