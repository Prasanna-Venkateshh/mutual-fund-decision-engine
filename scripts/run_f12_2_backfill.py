"""
Phase F.12.2 Multi-Year Hybrid Historical NAV Backfill Execution Runner Script

Executes the authorized 10-year hybrid backfill (3Y daily + 7Y monthly) against the live AMFI API
into the dedicated database db/backfill_f12_2.db using polite sequential HTTP acquisition with locked SQLite serialization.
"""

import sys
import os
import json
import time
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.ingestion.historical_nav_pipeline import HistoricalNAVPipeline, HistoricalNAVAcquisitionScheduler, HistoricalCoverageAnalyzer, AcquisitionWindow

BACKFILL_DB = "db/backfill_f12_2.db"
DATASET_VERSION = "f12_2_v1.0.0"

# Governance Date Boundaries
MONTHLY_START = "2014-02-01"
MONTHLY_END = "2021-01-31"  # 84 monthly windows
DAILY_START = "2021-02-01"
DAILY_END = "2024-01-31"    # 1,095 daily windows

# Sequential acquisition — NUM_WORKERS=1 ensures no concurrent SQLite writes
NUM_WORKERS = 1
DB_LOCK = threading.Lock()

def run_backfill(resume: bool = True):
    print("============================================================")
    print("PHASE F.12.2 MULTI-YEAR HYBRID HISTORICAL NAV BACKFILL")
    print("============================================================")
    print(f"Target Database: {BACKFILL_DB}")
    print(f"Dataset Version: {DATASET_VERSION}")
    print(f"Monthly Tail Scope (7Y): {MONTHLY_START} to {MONTHLY_END}")
    print(f"Daily Scope (3Y): {DAILY_START} to {DAILY_END}")
    print(f"Concurrent HTTP Workers: {NUM_WORKERS}")
    print("------------------------------------------------------------")

    # Generate windows first (no DB I/O)
    print("Generating acquisition windows...", flush=True)
    windows = HistoricalNAVAcquisitionScheduler.generate_hybrid_windows(
        daily_start_str=DAILY_START,
        daily_end_str=DAILY_END,
        monthly_start_str=MONTHLY_START,
        monthly_end_str=MONTHLY_END,
        source_id="AMFI_OFFICIAL"
    )
    monthly_count = len(HistoricalNAVAcquisitionScheduler.generate_monthly_windows(MONTHLY_START, MONTHLY_END))
    daily_count = len(HistoricalNAVAcquisitionScheduler.generate_daily_windows(DAILY_START, DAILY_END))
    print(f"Total Acquisition Windows Generated: {len(windows)}", flush=True)
    print(f"  - Monthly Windows (Years 4-10): {monthly_count}", flush=True)
    print(f"  - Daily Windows (Years 1-3): {daily_count}", flush=True)
    print("------------------------------------------------------------", flush=True)

    # Clean up non-SUCCESS ledger entries from previous interrupted runs
    # (resume will re-acquire them cleanly)
    if os.path.exists(BACKFILL_DB):
        print("Cleaning up non-SUCCESS ledger entries from prior runs...", flush=True)
        cleanup_conn = sqlite3.connect(BACKFILL_DB, timeout=60.0)
        cleanup_conn.execute("PRAGMA journal_mode = WAL;")
        cleanup_conn.execute("PRAGMA synchronous = NORMAL;")
        cleanup_conn.execute("DELETE FROM acquisition_coverage_ledger WHERE request_status NOT IN ('SUCCESS', 'SUCCESS_EMPTY');")
        cleanup_conn.commit()
        cleanup_conn.close()
        print("Cleanup done.", flush=True)

    # Initialize pipeline (DB connection + schema validation)
    print("Initializing pipeline...", flush=True)
    pipeline = HistoricalNAVPipeline(
        db_path=BACKFILL_DB,
        source_id="AMFI_OFFICIAL",
        rate_limit_delay_sec=0.2,
        max_retries=3,
        backoff_factor=1.5
    )
    print("Pipeline initialized.", flush=True)

    # Filter completed windows if resume=True
    if resume:
        print("Reading completion ledger for resume...", flush=True)
        with pipeline.db.get_conn() as conn:
            cursor = conn.execute("SELECT window_id FROM acquisition_coverage_ledger WHERE completion_status = 'COMPLETED' AND request_status IN ('SUCCESS', 'SUCCESS_EMPTY');")
            completed_set = {row[0] for row in cursor.fetchall()}
        print(f"Resumability: {len(completed_set)} windows already completed. Pending to acquire: {len(windows) - len(completed_set)}", flush=True)
        pending_windows = [w for w in windows if w.window_id not in completed_set]
    else:
        pending_windows = windows
        print(f"Full run: {len(pending_windows)} windows to acquire.", flush=True)

    if not pending_windows:
        print("All windows already completed. Nothing to acquire.")
        return {}

    start_time = time.time()
    run_id = f"run_f12_2_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    processed_count = 0
    total_pending = len(pending_windows)
    print(f"Starting acquisition run: {run_id}", flush=True)

    def process_window_safe(w: AcquisitionWindow):
        nonlocal processed_count
        # Delegate entirely to pipeline.process_window with use_live_network=True.
        # The pipeline has its own retry logic, shared session, and rate-limit handling.
        # DB_LOCK serializes all SQLite writes across the (single) worker thread.
        with DB_LOCK:
            entry = pipeline.process_window(
                window=w,
                acquisition_run_id=run_id,
                offline_fixture=None,
                resume=False,
                use_live_network=True
            )
            processed_count += 1
            now_str = datetime.now().strftime("%H:%M:%S")
            status = entry["request_status"]
            raw_cnt = entry["raw_records_count"]
            err = entry.get("error_info") or ""
            err_snippet = f" | {err[:80]}" if err and status not in ("SUCCESS", "SUCCESS_EMPTY") else ""
            print(f"[{now_str}] Progress: [{processed_count}/{total_pending}] Window {w.window_id}: {status} ({raw_cnt} records){err_snippet}", flush=True)
            return entry

    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = [executor.submit(process_window_safe, w) for w in pending_windows]
        for f in as_completed(futures):
            try:
                f.result()
            except Exception as e:
                print(f"Window exception: {e}", flush=True)

    elapsed = time.time() - start_time

    # Coverage summary
    analyzer = HistoricalCoverageAnalyzer(db_path=BACKFILL_DB)
    coverage = analyzer.generate_coverage_report(source_id="AMFI_OFFICIAL")

    db_size_bytes = os.path.getsize(BACKFILL_DB) if os.path.exists(BACKFILL_DB) else 0
    db_size_mb = db_size_bytes / (1024 * 1024)

    summary = {
        "dataset_version": DATASET_VERSION,
        "run_id": run_id,
        "execution_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "backfill_scope": {
            "backfill_start_date": MONTHLY_START,
            "backfill_end_date": DAILY_END,
            "monthly_start_date": MONTHLY_START,
            "monthly_end_date": MONTHLY_END,
            "daily_start_date": DAILY_START,
            "daily_end_date": DAILY_END,
        },
        "windows_summary": {
            "total_windows_requested": len(windows),
            "monthly_windows": monthly_count,
            "daily_windows": daily_count,
            "windows_success_with_records": coverage["windows_success_with_records"],
            "windows_success_zero_records": coverage["windows_success_zero_records"],
            "windows_failed": coverage["windows_failed"]
        },
        "observation_counts": {
            "total_raw_records": coverage["total_raw_records"],
            "total_normalized_records": coverage["total_normalized_records"],
            "total_nav_quarantine": coverage["total_nav_quarantine"],
            "total_mapping_quarantine": coverage["total_mapping_quarantine"],
            "disposition_reconciliation": (
                coverage["total_raw_records"] == 
                coverage["total_normalized_records"] + coverage["total_nav_quarantine"] + coverage["total_mapping_quarantine"]
            )
        },
        "scheme_coverage": {
            "unique_canonical_schemes": coverage["unique_schemes_count"],
            "earliest_acquired_date": coverage["earliest_acquired_date"],
            "latest_acquired_date": coverage["latest_acquired_date"]
        },
        "performance": {
            "elapsed_seconds": round(elapsed, 2),
            "average_seconds_per_window": round(elapsed / len(windows), 3) if windows else 0,
            "database_size_mb": round(db_size_mb, 2)
        }
    }

    # Save summary metadata
    with open("docs/dataset_version_f12_2.json", "w") as f:
        json.dump(summary, f, indent=2)

    print("\n============================================================")
    print("BACKFILL EXECUTION COMPLETED")
    print("============================================================")
    print(f"Elapsed Time: {elapsed:.2f} seconds ({elapsed/60:.2f} minutes)")
    print(f"Database Size: {db_size_mb:.2f} MB")
    print(f"Raw Observations: {coverage['total_raw_records']}")
    print(f"Normalized Records: {coverage['total_normalized_records']}")
    print(f"NAV Quarantine: {coverage['total_nav_quarantine']}")
    print(f"Mapping Quarantine: {coverage['total_mapping_quarantine']}")
    print(f"Unique Canonical Schemes: {coverage['unique_schemes_count']}")
    print(f"Disposition Conservation: {summary['observation_counts']['disposition_reconciliation']}")
    print("============================================================")

    return summary

if __name__ == "__main__":
    run_backfill(resume=True)
