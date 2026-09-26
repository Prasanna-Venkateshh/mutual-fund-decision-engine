"""
PHASE F.12.3.1.1 — CUMULATIVE RAW OBSERVATION FORENSIC RECONCILIATION TEST SUITE

Validates:
1. Cumulative coverage ledger raw sum equals 7,993,379.
2. Total DB unique raw observations equals 8,154,191.
3. Exact set difference |B - A| equals 160,812.
4. Reverse set difference |A - B| equals 0.
5. Untracked date identification (31 daily windows of Jan 2024: 2024-01-01 to 2024-01-31).
6. Tracked ledger window exact match (7,993,379 == 7,993,379, 0 diff).
7. Extension period unique raw observation count (1,966,531).
8. Pre-extension historical unique raw observation count (6,187,660).
9. Normalized table record count (6,337,995).
10. 2024-01-31 evaluation cohort size (5,874).
11. Forward 1Y reachable cohort size (5,750 / 97.89%).
12. Unreachable cohort breakdown (124 schemes matured/closed in 2024).
13. Dataset version descriptor verification (f12_3_1_1_v1.0.0).
14. Production methodology immutability.
"""

import os
import sqlite3
import pytest
import json
from scoring.config import SCORING_METHODOLOGY_VERSION, CATEGORY_FAMILY_WEIGHTS

DB_PATH = 'db/backfill_f12_2.db'
DESCRIPTOR_PATH = 'docs/dataset_version_f12_3_1_1.json'


def test_01_cumulative_ledger_raw_sum_reproduction():
    """Verify cumulative ledger raw sum equals 7,993,379 across 1,515 windows."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT SUM(raw_records_count) FROM acquisition_coverage_ledger")
    ledger_sum = cur.fetchone()[0]
    conn.close()
    assert ledger_sum == 7993379


def test_02_total_unique_raw_observation_count_reproduction():
    """Verify total DB unique raw observations equals 8,154,191."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(DISTINCT raw_scheme_code || '_' || SUBSTR(raw_date, 1, 10)) FROM raw_nav_observations")
    total_unique = cur.fetchone()[0]
    conn.close()
    assert total_unique == 8154191


def test_03_exact_set_difference_160812_reproduction():
    """Verify exact set difference |B - A| equals 160,812."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT requested_start_date FROM acquisition_coverage_ledger")
    tracked_dates = set(r[0] for r in cur.fetchall())

    cur.execute("SELECT DISTINCT SUBSTR(raw_date, 1, 10) FROM raw_nav_observations")
    all_dates = set(r[0] for r in cur.fetchall())

    untracked_dates = sorted(list(all_dates - tracked_dates))

    placeholders = ','.join(['?'] * len(untracked_dates))
    cur.execute(f"""
        SELECT COUNT(DISTINCT raw_scheme_code || '_' || SUBSTR(raw_date, 1, 10))
        FROM raw_nav_observations
        WHERE SUBSTR(raw_date, 1, 10) IN ({placeholders})
    """, untracked_dates)
    b_minus_a = cur.fetchone()[0]
    conn.close()

    assert len(untracked_dates) == 31
    assert b_minus_a == 160812


def test_04_reverse_set_difference_zero_reproduction():
    """Verify reverse set difference |A - B| equals 0 (every ledger window exists in raw table)."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT requested_start_date FROM acquisition_coverage_ledger")
    tracked_dates = set(r[0] for r in cur.fetchall())

    cur.execute("SELECT DISTINCT SUBSTR(raw_date, 1, 10) FROM raw_nav_observations")
    all_dates = set(r[0] for r in cur.fetchall())

    a_minus_b = tracked_dates - all_dates
    conn.close()
    assert len(a_minus_b) == 0


def test_05_untracked_date_identification():
    """Verify untracked dates are exactly 31 daily windows of Jan 2024 (2024-01-01 to 2024-01-31)."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT requested_start_date FROM acquisition_coverage_ledger")
    tracked_dates = set(r[0] for r in cur.fetchall())

    cur.execute("SELECT DISTINCT SUBSTR(raw_date, 1, 10) FROM raw_nav_observations")
    all_dates = set(r[0] for r in cur.fetchall())

    untracked_dates = sorted(list(all_dates - tracked_dates))
    conn.close()

    assert len(untracked_dates) == 31
    assert untracked_dates[0] == '2024-01-01'
    assert untracked_dates[-1] == '2024-01-31'


def test_06_tracked_window_exact_reconciliation():
    """Verify unique raw observations on tracked ledger windows equals 7,993,379 (0 difference)."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(DISTINCT raw_scheme_code || '_' || SUBSTR(raw_date, 1, 10))
        FROM raw_nav_observations
        WHERE SUBSTR(raw_date, 1, 10) IN (SELECT requested_start_date FROM acquisition_coverage_ledger)
    """)
    tracked_unique = cur.fetchone()[0]

    cur.execute("SELECT SUM(raw_records_count) FROM acquisition_coverage_ledger")
    ledger_sum = cur.fetchone()[0]
    conn.close()

    assert tracked_unique == 7993379
    assert ledger_sum == 7993379
    assert tracked_unique == ledger_sum


def test_07_extension_period_unique_raw_reconciliation():
    """Verify extension unique raw observations equals 1,966,531 across 366 daily windows."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(DISTINCT raw_scheme_code || '_' || SUBSTR(raw_date, 1, 10))
        FROM raw_nav_observations
        WHERE SUBSTR(raw_date, 1, 10) >= '2024-02-01' AND SUBSTR(raw_date, 1, 10) <= '2025-01-31'
    """)
    ext_unique = cur.fetchone()[0]

    cur.execute("""
        SELECT SUM(raw_records_count)
        FROM acquisition_coverage_ledger
        WHERE requested_start_date >= '2024-02-01' AND requested_end_date <= '2025-01-31'
    """)
    ext_ledger_sum = cur.fetchone()[0]
    conn.close()

    assert ext_unique == 1966531
    assert ext_ledger_sum == 1966531


def test_08_pre_extension_period_unique_raw_reconciliation():
    """Verify pre-extension historical unique raw observations equals 6,187,660."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(DISTINCT raw_scheme_code || '_' || SUBSTR(raw_date, 1, 10))
        FROM raw_nav_observations
        WHERE SUBSTR(raw_date, 1, 10) >= '2014-02-01' AND SUBSTR(raw_date, 1, 10) <= '2024-01-31'
    """)
    pre_unique = cur.fetchone()[0]
    conn.close()
    assert pre_unique == 6187660


def test_09_normalized_table_exact_count():
    """Verify normalized_nav_records table count equals 6,337,995."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM normalized_nav_records")
    norm_total = cur.fetchone()[0]
    conn.close()
    assert norm_total == 6337995


def test_10_2024_01_31_cohort_reproduction():
    """Verify 2024-01-31 evaluation cohort equals 5,874 schemes."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(DISTINCT canonical_scheme_id) FROM normalized_nav_records WHERE nav_date = '2024-01-31'")
    cohort_cnt = cur.fetchone()[0]
    conn.close()
    assert cohort_cnt == 5874


def test_11_forward_1y_reachable_cohort_reproduction():
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


def test_12_unreachable_cohort_reproduction():
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


def test_13_dataset_version_descriptor_verification():
    """Verify dataset version descriptor file exists and contains dataset_version f12_3_1_1_v1.0.0."""
    assert os.path.exists(DESCRIPTOR_PATH)
    with open(DESCRIPTOR_PATH, 'r') as f:
        data = json.load(f)
    assert data["dataset_version"] == "f12_3_1_1_v1.0.0"
    assert data["reconciliation_status"] == "RECONCILIED"
    assert data["forensic_proof_160812"]["set_difference_untracked_jan2024_count"] == 160812


def test_14_production_scoring_immutability():
    """Confirm production weights and scoring engine version remain 100% frozen."""
    assert CATEGORY_FAMILY_WEIGHTS["Equity"]["return"] == 25.0
    assert SCORING_METHODOLOGY_VERSION == "1.0.0"
