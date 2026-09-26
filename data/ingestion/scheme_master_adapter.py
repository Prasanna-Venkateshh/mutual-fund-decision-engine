"""
AMFI Scheme Master Metadata Adapter (Phase F.10).

Parses and normalizes comprehensive AMFI Scheme Master metadata records containing
TER, Riskometer, Benchmark, ISINs, AMC name, category, and subcategory data.
"""

from datetime import date
from typing import Dict, List, Any, Optional


class SchemeMasterFeedAdapter:
    """Adapter for ingesting and parsing AMFI Scheme Master metadata disclosures."""

    SOURCE_ID = "AMFI_SCHEME_MASTER"

    def parse_scheme_master_items(self, raw_items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Parses raw Scheme Master dictionaries.
        Returns a dictionary mapping `amfi_code` -> {
            "amfi_code": str,
            "isin_growth": str,
            "isin_reinvest": str,
            "scheme_name": str,
            "amc_name": str,
            "category": str,
            "subcategory": str,
            "ter_value": float,
            "riskometer_label": str,
            "benchmark_name": str,
            "source_id": str
        }
        """
        master_map: Dict[str, Dict[str, Any]] = {}
        for item in raw_items:
            scheme_code = str(item.get("scheme_code", "")).strip()
            if not scheme_code or not scheme_code.isdigit():
                continue

            ter_val = None
            raw_ter = item.get("ter") or item.get("ter_value")
            if raw_ter is not None:
                try:
                    ter_val = float(raw_ter)
                except (ValueError, TypeError):
                    ter_val = None

            raw_risk = item.get("riskometer") or item.get("riskometer_label")
            risk_label = str(raw_risk).strip().upper() if raw_risk and isinstance(raw_risk, str) else None

            raw_bm = item.get("benchmark") or item.get("benchmark_name")
            bm_name = str(raw_bm).strip() if raw_bm and isinstance(raw_bm, str) else None

            master_map[scheme_code] = {
                "amfi_code": scheme_code,
                "isin_growth": item.get("isin_growth") or item.get("isin"),
                "isin_reinvest": item.get("isin_reinvest"),
                "scheme_name": item.get("scheme_name"),
                "amc_name": item.get("amc_name"),
                "category": item.get("category"),
                "subcategory": item.get("subcategory"),
                "ter_value": ter_val,
                "riskometer_label": risk_label,
                "benchmark_name": bm_name,
                "source_id": self.SOURCE_ID
            }

        return master_map
