"""
AMFI TER Feed Adapter (Phase F.10).

Parses and normalizes raw TER disclosure items into structured dictionaries
keyed by canonical identity `CAN_AMFI_{amfi_code}`.
"""

from datetime import date, datetime, timezone
from typing import Dict, List, Any, Optional, Tuple


class TERFeedAdapter:
    """Adapter for ingesting and parsing AMFI/AMC TER disclosure feeds."""

    SOURCE_ID = "AMFI_TER_FEED"

    def parse_ter_feed_items(self, raw_items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Parses raw TER feed dictionaries.
        Returns a dictionary mapping `amfi_code` -> {
            "amfi_code": str,
            "ter_value": float,
            "effective_date": date,
            "plan_type": str,
            "source_id": str
        }
        """
        ter_map: Dict[str, Dict[str, Any]] = {}
        for item in raw_items:
            scheme_code = str(item.get("scheme_code", "")).strip()
            if not scheme_code or not scheme_code.isdigit():
                continue

            raw_ter = item.get("ter") or item.get("ter_percentage")
            if raw_ter is None:
                continue

            try:
                ter_float = float(raw_ter)
            except (ValueError, TypeError):
                continue

            eff_date = item.get("effective_date")
            if isinstance(eff_date, str):
                try:
                    eff_date = date.fromisoformat(eff_date)
                except ValueError:
                    eff_date = None

            plan_str = str(item.get("plan", "DIRECT")).strip().upper()

            ter_map[scheme_code] = {
                "amfi_code": scheme_code,
                "ter_value": ter_float,
                "ter_observation_date": eff_date,
                "plan_type": plan_str,
                "source_id": self.SOURCE_ID
            }

        return ter_map
