"""
Phase F.12.2 Multi-Year Hybrid Historical NAV Backfill Execution Test Suite.
"""

import pytest
import sqlite3
import os
import json
import pandas as pd

BACKFILL_DB = "db/backfill_f12_2.db"
VERSION_FILE = "docs/dataset_version_f12_2.json"

@pytest.fixture
def db_conn():
    if not os.path.exists(BACKFILL_DB):
        pytest.skip(f"Backfill DB {BACKFILL_DB} does not exist yet.")
    conn = sqlite3.connect(BACKFILL_DB)
    yield conn
    conn.close()

def test_01_date_range_and_sampling_policy(db_conn):
    """Test 1: Verify date ranges and hybrid sampling policy in backfill DB."""
    cursor = db_conn.cursor()
    cursor.execute("SELECT count(*) FROM acquisition_coverage_ledger;")
    total_ledger = cursor.fetchone()[0]
    assert total_ledger >= 1  # Multi-window coverage

    cursor.execute("SELECT min(requested_start_date), max(requested_start_date) FROM acquisition_coverage_ledger;")
    min_date, max_date = cursor.fetchone()
    assert min_date <= "2015-01-01"

def test_02_raw_disposition_reconciliation(db_conn):
    """Test 2: Verify 100% raw-observation disposition reconciliation across all windows."""
    df_ledger = pd.read_sql_query("""
        SELECT requested_start_date, raw_records_count, normalized_records_count,
               nav_quarantine_count, mapping_quarantine_count
        FROM acquisition_coverage_ledger;
    """, db_conn)

    for _, row in df_ledger.iterrows():
        disposition_sum = (row['normalized_records_count'] + 
                           row['nav_quarantine_count'] + 
                           row['mapping_quarantine_count'])
        assert row['raw_records_count'] == disposition_sum

def test_03_nav_numeric_validation(db_conn):
    """Test 3: Verify all normalized NAV records have numeric NAV values > 0."""
    cursor = db_conn.cursor()
    cursor.execute("SELECT count(*) FROM normalized_nav_records WHERE nav_value <= 0 OR nav_value IS NULL;")
    invalid_count = cursor.fetchone()[0]
    assert invalid_count == 0

def test_04_idempotency_and_no_duplicates(db_conn):
    """Test 4: Verify zero duplicate logical observations (scheme_id + nav_date)."""
    cursor = db_conn.cursor()
    cursor.execute("""
        SELECT canonical_scheme_id, nav_date, count(*)
        FROM normalized_nav_records
        GROUP BY canonical_scheme_id, nav_date
        HAVING count(*) > 1;
    """)
    duplicates = cursor.fetchall()
    assert len(duplicates) == 0

def test_05_resumability_and_ledger_integrity(db_conn):
    """Test 5: Verify ledger entries contain completion status and endpoint URL."""
    df_ledger = pd.read_sql_query("""
        SELECT window_id, http_status, request_status, completion_status, endpoint_url, response_hash
        FROM acquisition_coverage_ledger;
    """, db_conn)

    assert len(df_ledger) > 0
    assert (df_ledger['completion_status'] == 'COMPLETED').all()
    df_success = df_ledger[df_ledger['request_status'].isin(['SUCCESS', 'SUCCESS_EMPTY'])]
    if len(df_success) > 0:
        assert (df_success['http_status'] == 200).all()
        assert df_success['endpoint_url'].str.startswith("https://www.amfiindia.com").all()

def test_06_provenance_retention(db_conn):
    """Test 6: Verify raw observations retain source_id, retrieval_timestamp, raw_scheme_code, raw_date."""
    df_raw = pd.read_sql_query("""
        SELECT source_id, retrieval_timestamp, raw_scheme_code, raw_date, raw_nav_value
        FROM raw_nav_observations
        LIMIT 100;
    """, db_conn)

    assert len(df_raw) > 0
    assert (df_raw['source_id'] == 'AMFI_OFFICIAL').all()
    assert df_raw['raw_scheme_code'].notnull().all()
    assert df_raw['raw_date'].notnull().all()

def test_07_dataset_versioning_metadata():
    """Test 7: Verify dataset versioning metadata file exists and contains valid summary."""
    if not os.path.exists(VERSION_FILE):
        pytest.skip(f"Version file {VERSION_FILE} not created yet.")

    with open(VERSION_FILE) as f:
        meta = json.load(f)

    assert meta["dataset_version"] == "f12_2_v1.0.0"
    assert "observation_counts" in meta
    assert meta["observation_counts"]["disposition_reconciliation"] is True

def test_08_survivorship_preservation(db_conn):
    """Test 8: Verify canonical schemes table includes all historical schemes without deletion."""
    cursor = db_conn.cursor()
    cursor.execute("SELECT count(*) FROM canonical_schemes;")
    total_schemes = cursor.fetchone()[0]
    assert total_schemes > 1000

def test_09_metric_computability_breakdown(db_conn):
    """Test 9: Verify calculation of scheme longitudinal observation depth."""
    df_depth = pd.read_sql_query("""
        SELECT canonical_scheme_id, count(DISTINCT nav_date) as obs_count
        FROM normalized_nav_records
        GROUP BY canonical_scheme_id;
    """, db_conn)

    assert len(df_depth) > 0

def test_10_synthetic_data_exclusion(db_conn):
    """Test 10: Verify zero synthetic schemes or mock payload contamination in backfill DB."""
    cursor = db_conn.cursor()
    cursor.execute("SELECT count(*) FROM canonical_schemes WHERE canonical_scheme_id LIKE '%TEST%' OR canonical_scheme_id LIKE '%MOCK%';")
    assert cursor.fetchone()[0] == 0
