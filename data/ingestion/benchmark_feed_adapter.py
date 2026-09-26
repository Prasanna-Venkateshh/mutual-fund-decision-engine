"""
AMFI Benchmark Feed Adapter (Phase F.10).

Parses and normalizes raw Benchmark disclosure items into structured dictionaries
keyed by scheme code.
"""

from datetime import date
from typing import Dict, List, Any, Optional


class BenchmarkFeedAdapter:
    """Adapter for ingesting and parsing AMFI Benchmark disclosure feeds."""

    SOURCE_ID = "AMFI_BENCHMARK_FEED"

    def parse_benchmark_feed_items(self, raw_items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Parses raw Benchmark feed dictionaries.
        Returns a dictionary mapping `amfi_code` -> {
            "amfi_code": str,
            "benchmark_name": str,
            "effective_date": date,
            "source_id": str
        }
        """
        benchmark_map: Dict[str, Dict[str, Any]] = {}
        for item in raw_items:
            scheme_code = str(item.get("scheme_code", "")).strip()
            if not scheme_code or not scheme_code.isdigit():
                continue

            raw_bm = item.get("benchmark") or item.get("benchmark_name")
            if not raw_bm or not isinstance(raw_bm, str):
                continue

            clean_bm = raw_bm.strip()

            eff_date = item.get("effective_date")
            if isinstance(eff_date, str):
                try:
                    eff_date = date.fromisoformat(eff_date)
                except ValueError:
                    eff_date = None

            benchmark_map[scheme_code] = {
                "amfi_code": scheme_code,
                "benchmark_name": clean_bm,
                "effective_date": eff_date,
                "source_id": self.SOURCE_ID
            }

        return benchmark_map
