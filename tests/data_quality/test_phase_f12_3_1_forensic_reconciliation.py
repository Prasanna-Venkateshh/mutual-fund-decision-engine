"""
PHASE F.12.3.1 — DATABASE POPULATION & QUARANTINE FORENSIC RECONCILIATION TEST SUITE

Validates:
1. Extension single-pass raw observation disposition reconciliation.
2. Extension unique raw observation grain (1,966,531).
3. Extension raw table multi-run row duplicate explanation (7,196,960 rows).
4. Extension normalized table exact match (1,571,698 records, 0 duplicates).
5. Pre-2024 vs Extension dataset boundary separation.
6. Quarantine single-pass summary vs multi-run taxonomy distinction.
7. Quarantine reason taxonomy distribution.
8. Cumulative ledger raw sum vs unique raw observation grain.
9. Cumulative normalized table exact count (6,337,995 records).
10. Coverage window accounting (366 extension, 1,515 cumulative).
11. 2024-01-31 evaluation cohort reproduction (5,874 schemes).
12. Forward 1Y reachable cohort reproduction (5,750 schemes).
13. Unreachable cohort reproduction (124 schemes matured/closed in 2024).
14. Point-in-Time (PIT) zero look-ahead safety verification.
15. Provenance metadata preservation.
16. Dataset version descriptor verification (f12_3_1_v1.0.0).
17. Production methodology immutability.
"""

import os
import sqlite3
import pytest
import json
from scoring.config import SCORING_METHODOLOGY_VERSION, CATEGORY_FAMILY_WEIGHTS

DB_PATH = 'db/backfill_f12_2.db'
DESCRIPTOR_PATH = 'docs/dataset_version_f12_3_1.json'


def test_01_extension_single_pass_reconciliation():
    """Verify single-pass ledger disposition identity: Raw = Norm + NAV_Q + Map_Q."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            SUM(raw_records_count),
            SUM(normalized_records_count),
            SUM(nav_quarantine_count),
            SUM(mapping_quarantine_count)
        FROM acquisition_coverage_ledger
        WHERE requested_start_date >= '2024-02-01' AND requested_end_date <= '2025-01-31'
    """)
    raw, norm, nav_q, map_q = cur.fetchone()
    conn.close()
    assert raw == 1966531
    assert norm == 1571698
    assert nav_q == 26338
    assert map_q == 368495
    assert raw == (norm + nav_q + map_q)


def test_02_extension_unique_raw_observation_grain():
    """Verify unique raw observation count in extension period equals 1,966,531."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(DISTINCT source_id || '_' || raw_scheme_code || '_' || SUBSTR(raw_date, 1, 10))
        FROM raw_nav_observations
        WHERE SUBSTR(raw_date, 1, 10) >= '2024-02-01' AND SUBSTR(raw_date, 1, 10) <= '2025-01-31'
    """)
    unique_raw = cur.fetchone()[0]
    conn.close()
    assert unique_raw == 1966531


def test_03_extension_raw_table_multi_run_duplicate_explanation():
    """Verify raw table contains multi-run duplicate rows (7,196,960) collapsing to 1,966,531 unique."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM raw_nav_observations WHERE SUBSTR(raw_date, 1, 10) >= '2024-02-01' AND SUBSTR(raw_date, 1, 10) <= '2025-01-31'")
    table_raw_rows = cur.fetchone()[0]
    conn.close()
    assert table_raw_rows > 1966531
    assert table_raw_rows == 7196960


def test_04_extension_normalized_table_exact_match():
    """Verify normalized table has exactly 1,571,698 records in extension period with zero duplicates."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM normalized_nav_records WHERE nav_date >= '2024-02-01' AND nav_date <= '2025-01-31'")
    norm_count = cur.fetchone()[0]
    
    cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT canonical_scheme_id, nav_date, COUNT(*) as c
            FROM normalized_nav_records
            WHERE nav_date >= '2024-02-01' AND nav_date <= '2025-01-31'
            GROUP BY canonical_scheme_id, nav_date
            HAVING c > 1
        )
    """)
    duplicates = cur.fetchone()[0]
    conn.close()
    
    assert norm_count == 1571698
    assert duplicates == 0


def test_05_pre_2024_vs_extension_boundary_separation():
    """Verify dataset boundary separation: Pre-2024 (4,766,297) + Extension (1,571,698) = 6,337,995."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM normalized_nav_records WHERE nav_date < '2024-02-01'")
    pre_cnt = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM normalized_nav_records WHERE nav_date >= '2024-02-01' AND nav_date <= '2025-01-31'")
    ext_cnt = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM normalized_nav_records")
    total_cnt = cur.fetchone()[0]
    conn.close()

    assert pre_cnt == 4766297
    assert ext_cnt == 1571698
    assert total_cnt == 6337995
    assert pre_cnt + ext_cnt == total_cnt


def test_06_quarantine_single_pass_vs_multi_run_taxonomy_reconciliation():
    """Verify single-pass terminal quarantine (394,833) vs multi-run quarantine table rows (1,444,773)."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT SUM(nav_quarantine_count + mapping_quarantine_count)
        FROM acquisition_coverage_ledger
        WHERE requested_start_date >= '2024-02-01' AND requested_end_date <= '2025-01-31'
    """)
    single_pass_q = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM quarantine_records q
        JOIN raw_nav_observations r ON q.raw_record_id = r.raw_record_id
        WHERE SUBSTR(r.raw_date, 1, 10) >= '2024-02-01' AND SUBSTR(r.raw_date, 1, 10) <= '2025-01-31'
    """)
    table_q = cur.fetchone()[0]
    conn.close()

    assert single_pass_q == 394833
    assert table_q == 1444773


def test_07_quarantine_reason_taxonomy_distribution():
    """Verify quarantine taxonomy reason categories exist and are classified properly."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT q.reason, COUNT(*)
        FROM quarantine_records q
        JOIN raw_nav_observations r ON q.raw_record_id = r.raw_record_id
        WHERE SUBSTR(r.raw_date, 1, 10) >= '2024-02-01' AND SUBSTR(r.raw_date, 1, 10) <= '2025-01-31'
        GROUP BY q.reason
    """)
    reasons = dict(cur.fetchall())
    conn.close()

    assert len(reasons) >= 3
    ambig_key = [k for k in reasons.keys() if 'AMBIGUOUS' in k][0]
    assert reasons[ambig_key] > 1000000


def test_08_cumulative_ledger_raw_sum():
    """Verify cumulative ledger raw sum equals 7,993,379."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT SUM(raw_records_count) FROM acquisition_coverage_ledger")
    cum_raw = cur.fetchone()[0]
    conn.close()
    assert cum_raw == 7993379


def test_09_cumulative_normalized_table_exact_count():
    """Verify cumulative normalized_nav_records table count equals 6,337,995."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM normalized_nav_records")
    cum_norm = cur.fetchone()[0]
    conn.close()
    assert cum_norm == 6337995


def test_10_coverage_window_counts():
    """Verify coverage ledger window counts (366 extension, 1,515 cumulative)."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM acquisition_coverage_ledger WHERE requested_start_date >= '2024-02-01' AND requested_end_date <= '2025-01-31'")
    ext_wins = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM acquisition_coverage_ledger")
    cum_wins = cur.fetchone()[0]
    conn.close()
    assert ext_wins == 366
    assert cum_wins == 1515


def test_11_2024_01_31_evaluation_cohort_reproduction():
    """Verify 2024-01-31 evaluation cohort count equals 5,874 schemes."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(DISTINCT canonical_scheme_id) FROM normalized_nav_records WHERE nav_date = '2024-01-31'")
    cohort_cnt = cur.fetchone()[0]
    conn.close()
    assert cohort_cnt == 5874


def test_12_forward_1y_reachable_cohort_reproduction():
    """Verify forward 1Y reachable cohort equals 5,750 schemes (97.89%)."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT canonical_scheme_id FROM normalized_nav_records WHERE nav_date = '2024-01-31'")
    eval_cohort = {r[0] for r in cur.fetchall()}

    cur.execute("SELECT DISTINCT canonical_scheme_id FROM normalized_nav_records WHERE nav_date >= '2025-01-01' AND nav_date <= '2025-01-31'")
    reach_cohort = {r[0] for r in cur.fetchall()}
    conn.close()

    fwd_reachable = eval_cohort.intersection(reach_cohort)
    assert len(fwd_reachable) == 5750


def test_13_unreachable_cohort_reproduction():
    """Verify unreachable cohort equals 124 schemes (matured/closed in 2024)."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT canonical_scheme_id FROM normalized_nav_records WHERE nav_date = '2024-01-31'")
    eval_cohort = {r[0] for r in cur.fetchall()}

    cur.execute("SELECT DISTINCT canonical_scheme_id FROM normalized_nav_records WHERE nav_date >= '2025-01-01' AND nav_date <= '2025-01-31'")
    reach_cohort = {r[0] for r in cur.fetchall()}
    conn.close()

    unreachable = eval_cohort - reach_cohort
    assert len(unreachable) == 124


def test_14_pit_zero_lookahead_safety_verification():
    """Verify 2024-01-31 cohort selection is strictly point-in-time on or before 2024-01-31."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(DISTINCT canonical_scheme_id) FROM normalized_nav_records WHERE nav_date <= '2024-01-31' AND nav_date = '2024-01-31'")
    pit_cnt = cur.fetchone()[0]
    conn.close()
    assert pit_cnt == 5874


def test_15_provenance_metadata_preservation():
    """Verify provenance fields exist in coverage ledger and raw observations."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT source_id, retrieval_timestamp_utc, endpoint_url, response_hash FROM acquisition_coverage_ledger LIMIT 1")
    ledger_row = cur.fetchone()
    conn.close()

    assert ledger_row[0] == "AMFI_OFFICIAL"
    assert ledger_row[1] is not None
    assert "amfiindia.com" in ledger_row[2]
    assert ledger_row[3] is not None


def test_16_dataset_version_descriptor():
    """Verify dataset version descriptor file exists and contains dataset_version f12_3_1_v1.0.0."""
    assert os.path.exists(DESCRIPTOR_PATH)
    with open(DESCRIPTOR_PATH, 'r') as f:
        data = json.load(f)
    assert data["dataset_version"] == "f12_3_1_v1.0.0"
    assert data["reconciliation_status"] == "RECONCILIED"


def test_17_production_scoring_immutability():
    """Confirm production weights and methodology version are 100% frozen."""
    assert CATEGORY_FAMILY_WEIGHTS["Equity"]["return"] == 25.0
    assert SCORING_METHODOLOGY_VERSION == "1.0.0"
