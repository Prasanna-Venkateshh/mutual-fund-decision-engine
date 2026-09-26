"""
Phase F.12.3 Historical NAV Dataset Extension Script (2024-02-01 to 2025-01-31)

Extends real historical NAV data in db/backfill_f12_2.db from 2024-02-01 through 2025-01-31.
Preserves canonical identity, raw-to-normalized-to-quarantine disposition reconciliation,
resumability, idempotency, and point-in-time provenance.

GOVERNANCE: DATA EXTENSION ONLY. Zero prediction calculations or scoring methodology changes.
"""

import sys
import os
import time
import sqlite3
import threading
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.ingestion.historical_nav_pipeline import (
    HistoricalNAVPipeline,
    HistoricalNAVAcquisitionScheduler,
    HistoricalCoverageAnalyzer,
    AcquisitionWindow
)
from scoring.config import SCORING_METHODOLOGY_VERSION, CATEGORY_FAMILY_WEIGHTS

# Governance Immutability Assertion
assert CATEGORY_FAMILY_WEIGHTS["Equity"]["return"] == 25.0, "Production config modified -- ABORT"
assert SCORING_METHODOLOGY_VERSION == "1.0.0", "Production version modified -- ABORT"

BACKFILL_DB = "db/backfill_f12_2.db"
DATASET_VERSION = "f12_3_v1.0.0"

EXTENSION_START = "2024-02-01"
EXTENSION_END = "2025-01-31"

NUM_WORKERS = 1
DB_LOCK = threading.Lock()


def run_extension(resume: bool = True):
    print("=" * 80)
    print("PHASE F.12.3 HISTORICAL NAV DATASET EXTENSION (2024-02-01 TO 2025-01-31)")
    print("=" * 80)
    print(f"Target Database: {BACKFILL_DB}")
    print(f"Dataset Version: {DATASET_VERSION}")
    print(f"Extension Date Range: {EXTENSION_START} to {EXTENSION_END}")
    print(f"Workers: {NUM_WORKERS}")
    print("-" * 80)

    # 1. Generate daily acquisition windows
    windows = HistoricalNAVAcquisitionScheduler.generate_daily_windows(
        start_date_str=EXTENSION_START,
        end_date_str=EXTENSION_END,
        source_id="AMFI_OFFICIAL"
    )
    print(f"Generated {len(windows)} daily acquisition windows.", flush=True)

    # Clean up non-SUCCESS ledger entries for extension windows if any exist
    if os.path.exists(BACKFILL_DB):
        cleanup_conn = sqlite3.connect(BACKFILL_DB, timeout=60.0)
        cleanup_conn.execute("PRAGMA journal_mode = WAL;")
        cleanup_conn.execute("PRAGMA synchronous = NORMAL;")
        cleanup_conn.execute("""
            DELETE FROM acquisition_coverage_ledger 
            WHERE window_id LIKE 'win_AMFI_OFFICIAL_2024-%' OR window_id LIKE 'win_AMFI_OFFICIAL_2025-%'
            AND request_status NOT IN ('SUCCESS', 'SUCCESS_EMPTY');
        """)
        cleanup_conn.commit()
        cleanup_conn.close()

    # 2. Initialize pipeline
    pipeline = HistoricalNAVPipeline(
        db_path=BACKFILL_DB,
        source_id="AMFI_OFFICIAL",
        rate_limit_delay_sec=0.1,
        max_retries=3,
        backoff_factor=1.5
    )

    # 3. Resume logic
    if resume:
        with pipeline.db.get_conn() as conn:
            cursor = conn.execute("""
                SELECT window_id FROM acquisition_coverage_ledger 
                WHERE completion_status = 'COMPLETED' AND request_status IN ('SUCCESS', 'SUCCESS_EMPTY');
            """)
            completed_set = {row[0] for row in cursor.fetchall()}
        pending_windows = [w for w in windows if w.window_id not in completed_set]
        print(f"Resumability: {len(completed_set)} windows already completed. Pending: {len(pending_windows)}", flush=True)
    else:
        pending_windows = windows

    if not pending_windows:
        print("All extension windows already completed.")
        return get_extension_summary(pipeline)

    start_time = time.time()
    run_id = f"run_f12_3_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    processed_count = 0
    total_pending = len(pending_windows)

    def process_window_safe(w: AcquisitionWindow):
        nonlocal processed_count
        with DB_LOCK:
            entry = pipeline.process_window(
                window=w,
                acquisition_run_id=run_id,
                offline_fixture=None,
                resume=False,
                use_live_network=True
            )
            processed_count += 1
            if processed_count % 20 == 0 or processed_count == total_pending:
                now_str = datetime.now().strftime("%H:%M:%S")
                status = entry["request_status"]
                raw_cnt = entry["raw_records_count"]
                print(f"[{now_str}] Progress: [{processed_count}/{total_pending}] Window {w.window_id}: {status} ({raw_cnt} raw records)", flush=True)
            return entry

    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = [executor.submit(process_window_safe, w) for w in pending_windows]
        for f in as_completed(futures):
            try:
                f.result()
            except Exception as e:
                print(f"Window exception: {e}", flush=True)

    elapsed = time.time() - start_time
    print(f"Extension acquisition completed in {elapsed:.2f} seconds.", flush=True)
    return get_extension_summary(pipeline)


def get_extension_summary(pipeline: HistoricalNAVPipeline):
    conn = sqlite3.connect(BACKFILL_DB)
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            COALESCE(SUM(raw_records_count), 0),
            COALESCE(SUM(normalized_records_count), 0),
            COALESCE(SUM(nav_quarantine_count), 0),
            COALESCE(SUM(mapping_quarantine_count), 0)
        FROM acquisition_coverage_ledger
        WHERE window_id LIKE 'win_AMFI_OFFICIAL_2024-%' OR window_id LIKE 'win_AMFI_OFFICIAL_2025-%'
    """)
    total_raw, total_normalized, total_nav_quarantine, total_mapping_quarantine = cur.fetchone()

    cur.execute("""
        SELECT COUNT(DISTINCT sm.source_scheme_code) 
        FROM normalized_nav_records n
        JOIN scheme_mappings sm ON n.canonical_scheme_id = sm.canonical_scheme_id
        WHERE n.nav_date >= ?
    """, (EXTENSION_START,))
    unique_amfi = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT canonical_scheme_id) FROM normalized_nav_records WHERE nav_date >= ?", (EXTENSION_START,))
    unique_canonical = cur.fetchone()[0]

    conn.close()

    reconciled = (total_raw == total_normalized + total_nav_quarantine + total_mapping_quarantine)

    summary = {
        "dataset_version": DATASET_VERSION,
        "extension_range": f"{EXTENSION_START} to {EXTENSION_END}",
        "total_raw": total_raw,
        "total_normalized": total_normalized,
        "total_nav_quarantine": total_nav_quarantine,
        "total_mapping_quarantine": total_mapping_quarantine,
        "unique_amfi_schemes": unique_amfi,
        "unique_canonical_schemes": unique_canonical,
        "disposition_reconciled": reconciled
    }

    print("\n--- EXTENSION SUMMARY & DISPOSITION RECONCILIATION ---")
    print(f"Total Raw Records: {total_raw}")
    print(f"Total Normalized Records: {total_normalized}")
    print(f"Total NAV Quarantine: {total_nav_quarantine}")
    print(f"Total Mapping Quarantine: {total_mapping_quarantine}")
    print(f"Sum (Norm + NAV Quar + Map Quar): {total_normalized + total_nav_quarantine + total_mapping_quarantine}")
    print(f"Exact Disposition Reconciled?: {reconciled}")
    print(f"Unique AMFI Schemes: {unique_amfi}")
    print(f"Unique Canonical Schemes: {unique_canonical}")

    return summary


if __name__ == '__main__':
    run_extension()
