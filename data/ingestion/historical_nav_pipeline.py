"""
Resumable Historical NAV Acquisition Pipeline & Coverage Ledger Engine (Phase B.2).

Provides an idempotent, resumable, auditable, and rate-conscious pipeline for progressive
historical NAV acquisition using exclusively the official AMFI NAV History API (AMFI_OFFICIAL).

Strict Governance Guardrails:
- No bulk download of 2010-2026 in this task.
- Uses ONLY AMFI_OFFICIAL source identity.
- Preserves raw observations immutably (append/audit).
- Enforces Data Quality Reconciliation: Raw = Normalized + NAV_Quarantine + Mapping_Quarantine.
"""

import time
import json
import hashlib
import uuid
import threading
import requests
from datetime import datetime, date, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple

from db.database import DatabaseConnection
from data.ingestion.source_registry import SourceRegistry
from data.ingestion.amfi_ingestor import AMFIIngestor
from data.validation.nav_validator import NAVValidator
from data.mapping.scheme_master import SchemeMaster
from data.normalization.nav_normalizer import NAVNormalizer
from data.repositories.nav_repository import NAVRepository


class AcquisitionWindow:
    """Represents a bounded date window for historical acquisition."""

    def __init__(self, start_date: str, end_date: str, source_id: str = "AMFI_OFFICIAL"):
        self.start_date = start_date.strip()
        self.end_date = end_date.strip()
        self.source_id = source_id
        self.window_id = f"win_{source_id}_{self.start_date}_{self.end_date}"


class HistoricalNAVAcquisitionScheduler:
    """Generates bounded sequential date windows for progressive acquisition."""

    @staticmethod
    def generate_daily_windows(
        start_date_str: str,
        end_date_str: str,
        source_id: str = "AMFI_OFFICIAL"
    ) -> List[AcquisitionWindow]:
        """Generate daily acquisition windows (single-day full-universe snapshots)."""
        dt_start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        dt_end = datetime.strptime(end_date_str, "%Y-%m-%d").date()

        windows = []
        curr = dt_start
        while curr <= dt_end:
            ds = curr.strftime("%Y-%m-%d")
            windows.append(AcquisitionWindow(start_date=ds, end_date=ds, source_id=source_id))
            curr += timedelta(days=1)

        return windows

    @staticmethod
    def generate_monthly_windows(
        start_date_str: str,
        end_date_str: str,
        source_id: str = "AMFI_OFFICIAL"
    ) -> List[AcquisitionWindow]:
        """Generate monthly acquisition windows targeting the last day of each calendar month."""
        dt_start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        dt_end = datetime.strptime(end_date_str, "%Y-%m-%d").date()

        windows = []
        curr_year = dt_start.year
        curr_month = dt_start.month

        end_year = dt_end.year
        end_month = dt_end.month

        while (curr_year < end_year) or (curr_year == end_year and curr_month <= end_month):
            # Find last day of current month
            if curr_month == 12:
                next_month_first = date(curr_year + 1, 1, 1)
            else:
                next_month_first = date(curr_year, curr_month + 1, 1)
            
            last_day = next_month_first - timedelta(days=1)
            
            # Ensure within bounds
            if dt_start <= last_day <= dt_end:
                ds = last_day.strftime("%Y-%m-%d")
                windows.append(AcquisitionWindow(start_date=ds, end_date=ds, source_id=source_id))

            if curr_month == 12:
                curr_month = 1
                curr_year += 1
            else:
                curr_month += 1

        return windows

    @staticmethod
    def generate_hybrid_windows(
        daily_start_str: str,
        daily_end_str: str,
        monthly_start_str: str,
        monthly_end_str: str,
        source_id: str = "AMFI_OFFICIAL"
    ) -> List[AcquisitionWindow]:
        """Generate hybrid windows: older monthly windows + recent daily windows."""
        monthly_wins = HistoricalNAVAcquisitionScheduler.generate_monthly_windows(
            start_date_str=monthly_start_str,
            end_date_str=monthly_end_str,
            source_id=source_id
        )
        daily_wins = HistoricalNAVAcquisitionScheduler.generate_daily_windows(
            start_date_str=daily_start_str,
            end_date_str=daily_end_str,
            source_id=source_id
        )
        return monthly_wins + daily_wins


class HistoricalNAVPipeline:
    """Resumable, Idempotent, Auditable Historical NAV Pipeline."""

    AMFI_API_BASE_URL = "https://www.amfiindia.com/api/nav-history"

    def __init__(
        self,
        db_path: str = "db/nav_database.db",
        source_id: str = "AMFI_OFFICIAL",
        rate_limit_delay_sec: float = 0.5,
        max_retries: int = 3,
        backoff_factor: float = 1.5
    ):
        self.db = DatabaseConnection(db_path)
        self.source_id = source_id
        self.registry = SourceRegistry(db=self.db)
        self.ingestor = AMFIIngestor(registry=self.registry, source_id=self.source_id)
        self.validator = NAVValidator()
        self.scheme_master = SchemeMaster()
        self.normalizer = NAVNormalizer(scheme_master=self.scheme_master)
        self.repo = NAVRepository(db=self.db)

        self.rate_limit_delay_sec = rate_limit_delay_sec
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MutualFundDecisionEngine/1.0"})
        self._lock = threading.Lock()

    def process_window(
        self,
        window: AcquisitionWindow,
        acquisition_run_id: str,
        offline_fixture: Optional[Dict[str, Any]] = None,
        resume: bool = True,
        use_live_network: bool = True
    ) -> Dict[str, Any]:
        """
        Process a single acquisition window.
        
        Resumability:
        If `resume=True` and window has already completed (`SUCCESS` or `SUCCESS_EMPTY`),
        returns cached ledger entry without fetching again.
        """
        # Check existing ledger for resumability
        if resume:
            existing = self.repo.get_ledger_entry(window.window_id)
            if existing and existing.get("completion_status") == "COMPLETED" and existing.get("request_status") in ("SUCCESS", "SUCCESS_EMPTY"):
                existing["resumed_from_cache"] = True
                return existing

        retrieval_ts = datetime.now(timezone.utc)
        endpoint_url = f"{self.AMFI_API_BASE_URL}?query_type=all_for_date&from_date={window.start_date}"

        http_status = 500
        raw_payload = None
        error_info = None
        retry_count = 0
        response_hash = None

        if use_live_network and offline_fixture is None:
            for attempt in range(1, self.max_retries + 1):
                try:
                    resp = self.session.get(endpoint_url, timeout=15, verify=True)
                    http_status = resp.status_code
                    if resp.status_code == 200:
                        try:
                            raw_payload = resp.json()
                        except Exception:
                            raw_payload = resp.text
                        response_hash = hashlib.md5(resp.content).hexdigest()
                        break
                    elif resp.status_code == 429:
                        error_info = f"HTTP Error 429 Rate Limited (Attempt {attempt})"
                        time.sleep(2.0 * attempt)
                    else:
                        error_info = f"HTTP Error {resp.status_code}: {resp.text[:200]}"
                except Exception as e:
                    error_info = f"Connection error: {str(e)}"
                    http_status = 500

                retry_count = attempt
                if attempt < self.max_retries:
                    time.sleep(self.rate_limit_delay_sec * (self.backoff_factor ** (attempt - 1)))
        elif offline_fixture is not None:
            raw_payload = offline_fixture
            http_status = 200
            if isinstance(raw_payload, (dict, list)):
                response_hash = hashlib.md5(json.dumps(raw_payload, sort_keys=True).encode("utf-8")).hexdigest()
            else:
                response_hash = hashlib.md5(str(raw_payload).encode("utf-8")).hexdigest()
        else:
            error_info = "No live network requested and no offline fixture provided."

        # Parse, validate, normalize, and save
        raw_records = []
        valid_tuples = []
        nav_quarantine_records = []
        mapping_quarantine_records = []
        normalized_records = []
        canonical_schemes_to_save = []
        mappings_to_save = []
        distinct_dates = set()

        if raw_payload:
            if isinstance(raw_payload, (dict, list)):
                raw_records = self.ingestor.parse_raw_amfi_json(raw_payload, retrieval_timestamp=retrieval_ts)
            else:
                raw_records = self.ingestor.parse_raw_amfi_text(str(raw_payload), retrieval_timestamp=retrieval_ts)

            valid_tuples, nav_quarantine_records = self.validator.process_and_quarantine(raw_records)
            normalized_records, mapping_quarantine_records = self.normalizer.normalize_batch(valid_tuples)

            saved_cids = set()
            for norm_rec in normalized_records:
                cid = norm_rec.canonical_scheme_id
                if cid not in saved_cids:
                    canonical = self.scheme_master._canonical_schemes.get(cid)
                    if canonical:
                        canonical_schemes_to_save.append(canonical)
                        mapping_key = f"{norm_rec.source_id}:{canonical.primary_amfi_code}"
                        mapping = self.scheme_master._mappings.get(mapping_key)
                        if mapping:
                            mappings_to_save.append(mapping)
                    saved_cids.add(cid)

            for rec in raw_records:
                if rec.raw_date:
                    distinct_dates.add(rec.raw_date)

        # Verify Data Quality Reconciliation Equation: Raw = Normalized + NAV_Quarantine + Mapping_Quarantine
        reconciled = (len(raw_records) == len(normalized_records) + len(nav_quarantine_records) + len(mapping_quarantine_records))
        if raw_payload and not reconciled:
            raise ValueError(f"Data Reconciliation Failure for {window.window_id}: Raw ({len(raw_records)}) != Norm ({len(normalized_records)}) + NAV_Q ({len(nav_quarantine_records)}) + Map_Q ({len(mapping_quarantine_records)})")

        # Determine Request Status
        if http_status == 200:
            if len(raw_records) > 0:
                request_status = "SUCCESS"
            else:
                request_status = "SUCCESS_EMPTY"  # e.g., pre-2010 boundary or non-trading day
        elif retry_count >= self.max_retries:
            request_status = "FAILED"
        else:
            request_status = "RETRY_REQUIRED"

        earliest_returned = min(distinct_dates) if distinct_dates else None
        latest_returned = max(distinct_dates) if distinct_dates else None

        ledger_entry = {
            "window_id": window.window_id,
            "acquisition_run_id": acquisition_run_id,
            "source_id": self.source_id,
            "requested_start_date": window.start_date,
            "requested_end_date": window.end_date,
            "retrieval_timestamp_utc": retrieval_ts.isoformat(),
            "endpoint_url": endpoint_url,
            "http_status": http_status,
            "request_status": request_status,
            "raw_records_count": len(raw_records),
            "nav_valid_records_count": len(valid_tuples),
            "nav_quarantine_count": len(nav_quarantine_records),
            "mapping_quarantine_count": len(mapping_quarantine_records),
            "normalized_records_count": len(normalized_records),
            "earliest_returned_date": earliest_returned,
            "latest_returned_date": latest_returned,
            "retry_count": retry_count,
            "error_info": error_info,
            "completion_status": "COMPLETED",
            "response_hash": response_hash,
            "resumed_from_cache": False
        }

        # Save all artifacts atomically in a single transaction
        self.repo.save_window_atomic(
            raw_records=raw_records,
            canonical_schemes=canonical_schemes_to_save,
            mappings=mappings_to_save,
            normalized_records=normalized_records,
            quarantine_records=nav_quarantine_records + mapping_quarantine_records,
            ledger_entry=ledger_entry
        )

        # Rate-limiting delay between requests if live network was used
        if use_live_network and offline_fixture is None and self.rate_limit_delay_sec > 0:
            time.sleep(self.rate_limit_delay_sec)

        return ledger_entry

    def run_acquisition_batch(
        self,
        windows: List[AcquisitionWindow],
        acquisition_run_id: Optional[str] = None,
        resume: bool = True,
        use_live_network: bool = True
    ) -> Dict[str, Any]:
        """Execute acquisition batch across multiple date windows."""
        run_id = acquisition_run_id or f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        processed_entries = []

        for window in windows:
            entry = self.process_window(
                window=window,
                acquisition_run_id=run_id,
                resume=resume,
                use_live_network=use_live_network
            )
            print(f"Processed window {window.window_id}: {entry['request_status']} ({entry['raw_records_count']} records)", flush=True)
            processed_entries.append(entry)

        return {
            "acquisition_run_id": run_id,
            "total_windows": len(windows),
            "processed_entries": processed_entries
        }


class HistoricalCoverageAnalyzer:
    """Coverage analysis and gap detection engine."""

    def __init__(self, db_path: str = "db/nav_database.db"):
        self.db = DatabaseConnection(db_path)
        self.repo = NAVRepository(db=self.db)

    def generate_coverage_report(self, source_id: str = "AMFI_OFFICIAL") -> Dict[str, Any]:
        """Generate comprehensive coverage and gap detection report from the coverage ledger."""
        entries = self.repo.list_ledger_entries(source_id=source_id)

        if not entries:
            return {
                "source_id": source_id,
                "total_windows_requested": 0,
                "earliest_acquired_date": None,
                "latest_acquired_date": None,
                "windows_success_with_records": 0,
                "windows_success_zero_records": 0,
                "windows_failed": 0,
                "total_raw_records": 0,
                "total_normalized_records": 0,
                "total_nav_quarantine": 0,
                "total_mapping_quarantine": 0,
                "unique_schemes_count": 0,
                "acquired_date_ranges": [],
                "failed_date_ranges": []
            }

        acquired_dates = []
        failed_dates = []
        zero_record_dates = []

        total_raw = 0
        total_norm = 0
        total_nav_q = 0
        total_map_q = 0
        success_with_records = 0
        success_zero_records = 0
        failed_count = 0

        for e in entries:
            req_date = e["requested_start_date"]
            status = e["request_status"]
            raw_cnt = e.get("raw_records_count", 0)

            total_raw += raw_cnt
            total_norm += e.get("normalized_records_count", 0)
            total_nav_q += e.get("nav_quarantine_count", 0)
            total_map_q += e.get("mapping_quarantine_count", 0)

            if status == "SUCCESS":
                success_with_records += 1
                acquired_dates.append(req_date)
            elif status == "SUCCESS_EMPTY":
                success_zero_records += 1
                zero_record_dates.append(req_date)
            else:
                failed_count += 1
                failed_dates.append(req_date)

        # Unique schemes count from DB
        with self.db.get_conn() as conn:
            cursor = conn.execute("SELECT COUNT(DISTINCT canonical_scheme_id) as cnt FROM normalized_nav_records WHERE source_id = ?", (source_id,))
            unique_schemes = cursor.fetchone()["cnt"]

        earliest_acquired = min(acquired_dates) if acquired_dates else None
        latest_acquired = max(acquired_dates) if acquired_dates else None

        return {
            "source_id": source_id,
            "total_windows_requested": len(entries),
            "earliest_acquired_date": earliest_acquired,
            "latest_acquired_date": latest_acquired,
            "windows_success_with_records": success_with_records,
            "windows_success_zero_records": success_zero_records,
            "windows_failed": failed_count,
            "total_raw_records": total_raw,
            "total_normalized_records": total_norm,
            "total_nav_quarantine": total_nav_q,
            "total_mapping_quarantine": total_map_q,
            "unique_schemes_count": unique_schemes,
            "acquired_dates": sorted(acquired_dates),
            "zero_record_dates": sorted(zero_record_dates),
            "failed_dates": sorted(failed_dates)
        }
