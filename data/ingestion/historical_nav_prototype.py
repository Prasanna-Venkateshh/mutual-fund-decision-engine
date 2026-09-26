"""
Controlled Historical NAV Retrieval Prototype (Phase B).

Executes controlled empirical retrieval experiments against official AMFI historical NAV feeds
to determine actual historical depth, scheme coverage, duplicate behavior, and provenance preservation.

Strict Scope Guardrails:
- Prototype only.
- Uses ONLY AMFI Official source (AMFI_OFFICIAL).
- No scoring, backtesting, TER, benchmark, or lifecycle ingestion.
"""

import time
import requests
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from db.database import DatabaseConnection
from data.ingestion.source_registry import SourceRegistry
from data.ingestion.amfi_ingestor import AMFIIngestor
from data.validation.nav_validator import NAVValidator
from data.mapping.scheme_master import SchemeMaster
from data.normalization.nav_normalizer import NAVNormalizer
from data.repositories.nav_repository import NAVRepository


class HistoricalNAVPrototype:
    """Controlled Historical NAV Acquisition Prototype Adapter."""

    AMFI_API_BASE_URL = "https://www.amfiindia.com/api/nav-history"

    def __init__(self, db_path: str = ":memory:"):
        self.db = DatabaseConnection(db_path)
        self.registry = SourceRegistry(db=self.db)
        self.ingestor = AMFIIngestor(registry=self.registry, source_id="AMFI_OFFICIAL")
        self.validator = NAVValidator()
        self.scheme_master = SchemeMaster()
        self.normalizer = NAVNormalizer(scheme_master=self.scheme_master)
        self.repo = NAVRepository(db=self.db)

    def fetch_historical_date_window(
        self,
        date_str: str,
        offline_fixture: Optional[Dict[str, Any]] = None,
        use_live_network: bool = True
    ) -> Dict[str, Any]:
        """
        Execute controlled historical NAV retrieval for a single target date.
        
        Target date format: YYYY-MM-DD (e.g. 2025-01-15, 2020-01-15, 2015-01-15, 2010-01-15, 2006-01-15).
        """
        start_time = time.time()
        retrieval_ts = datetime.now(timezone.utc)
        endpoint_url = f"{self.AMFI_API_BASE_URL}?query_type=all_for_date&from_date={date_str}"

        http_status = 200
        raw_payload = None
        error_msg = None

        if offline_fixture is not None:
            raw_payload = offline_fixture
            http_status = 200
        elif use_live_network:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            try:
                resp = requests.get(endpoint_url, headers=headers, timeout=15, verify=False)
                http_status = resp.status_code
                if resp.status_code == 200:
                    raw_payload = resp.json()
                else:
                    error_msg = f"HTTP Error {resp.status_code}: {resp.text[:200]}"
            except Exception as e:
                http_status = 500
                error_msg = str(e)
        else:
            error_msg = "No live network requested and no offline fixture provided."

        elapsed_sec = round(time.time() - start_time, 3)

        # Process raw payload through pipeline if data is present
        raw_records = []
        valid_tuples = []
        quarantine_records = []
        normalized_records = []
        distinct_schemes = set()
        distinct_dates = set()

        if raw_payload and isinstance(raw_payload, dict):
            raw_records = self.ingestor.parse_raw_amfi_json(raw_payload, retrieval_timestamp=retrieval_ts)
            self.repo.save_raw_observations(raw_records)

            valid_tuples, quarantine_records = self.validator.process_and_quarantine(raw_records)
            normalized_records, norm_quarantine = self.normalizer.normalize_batch(valid_tuples)
            quarantine_records.extend(norm_quarantine)

            # Persist canonical schemes, mappings, normalized records, and quarantine
            for norm_rec in normalized_records:
                canonical = self.scheme_master._canonical_schemes.get(norm_rec.canonical_scheme_id)
                if canonical:
                    self.repo.save_canonical_scheme(canonical)
                    mapping = self.scheme_master._mappings.get(f"{norm_rec.source_id}:{norm_rec.canonical_scheme_id}")
                    if mapping:
                        self.repo.save_scheme_mapping(mapping)

            self.repo.save_normalized_records(normalized_records)
            self.repo.save_quarantine_records(quarantine_records)

            for rec in raw_records:
                if rec.raw_scheme_code:
                    distinct_schemes.add(rec.raw_scheme_code)
                if rec.raw_date:
                    distinct_dates.add(rec.raw_date)

        earliest_obs = min(distinct_dates) if distinct_dates else None
        latest_obs = max(distinct_dates) if distinct_dates else None

        return {
            "requested_date": date_str,
            "endpoint_url": endpoint_url,
            "http_status": http_status,
            "response_time_sec": elapsed_sec,
            "retrieval_timestamp_utc": retrieval_ts.isoformat(),
            "raw_records_count": len(raw_records),
            "distinct_schemes_count": len(distinct_schemes),
            "distinct_dates_count": len(distinct_dates),
            "earliest_observation": earliest_obs,
            "latest_observation": latest_obs,
            "valid_records_count": len(valid_tuples),
            "quarantined_records_count": len(quarantine_records),
            "normalized_records_count": len(normalized_records),
            "error": error_msg
        }

    def run_controlled_prototype_suite(self, date_windows: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Run prototype across multiple date windows."""
        windows = date_windows or ["2025-01-15", "2020-01-15", "2015-01-15", "2010-01-15", "2006-01-15"]
        results = []
        for w in windows:
            res = self.fetch_historical_date_window(w, use_live_network=True)
            results.append(res)
        return results
