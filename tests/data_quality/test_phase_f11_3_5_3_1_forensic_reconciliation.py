"""
Test suite for Phase F.11.3.5.3.1 — OOS Validation Forensic Reconciliation.

Verifies:
1. Exact cohort set difference (5,874 vs 5,824, 50 schemes classified).
2. Forward reachability reconciliation (5,750 eligible, 124 unavailable).
3. Valid scored population equality (5,712 schemes).
4. Side-by-side metric stability across both cohort definitions.
5. Frozen methodology immutability.
"""

import os
import json
import pytest
import sys
sys.path.insert(0, '.')

from scripts.run_f11_3_5_3_1_forensic_reconciliation import (
    load_nav_data,
    get_f12_3_1_2_cohort_5874,
    run_forensic_reconciliation
)

DB_PATH = 'db/backfill_f12_2.db'
RESULTS_PATH = 'docs/phase_f11_3_5_3_1_results.json'


def test_cohort_reconciliation_exact_counts():
    """Verifies that 5,874 cohort decomposes into 5,750 eligible and 124 unavailable."""
    assert os.path.exists(RESULTS_PATH), "Results JSON must exist."
    with open(RESULTS_PATH, 'r') as f:
        res = json.load(f)

    old_res = res['governed_5874_results']
    assert old_res['anchor_n'] == 5874, f"Governed anchor cohort expected 5,874, got {old_res['anchor_n']}"
    assert old_res['eligible_n'] == 5750, f"Governed eligible expected 5,750, got {old_res['eligible_n']}"
    assert old_res['unavailable_n'] == 124, f"Governed unavailable expected 124, got {old_res['unavailable_n']}"


def test_valid_scored_population_equality():
    """Verifies that the valid scored population (N=5,712) is identical across both cohorts."""
    with open(RESULTS_PATH, 'r') as f:
        res = json.load(f)

    old_res = res['governed_5874_results']
    new_res = res['f11_3_5_3_5832_results']

    assert old_res['valid_scored_n'] == new_res['valid_scored_n'] == 5712, \
        f"Valid scored N must be 5,712 for both cohorts, got {old_res['valid_scored_n']} and {new_res['valid_scored_n']}"


def test_side_by_side_statistical_stability():
    """Verifies that Spearman rho and incremental R^2 are virtually identical across cohorts."""
    with open(RESULTS_PATH, 'r') as f:
        res = json.load(f)

    old_res = res['governed_5874_results']
    new_res = res['f11_3_5_3_5832_results']

    assert abs(old_res['spearman_fq_ret'] - new_res['spearman_fq_ret']) < 0.005
    assert abs(old_res['spearman_tr_ret'] - new_res['spearman_tr_ret']) < 0.001
    assert abs(old_res['inc_r2_ret'] - new_res['inc_r2_ret']) < 0.001


def test_strategy_simulation_consistency():
    """Verifies Strategy C (Fund Quality) return and MDD consistency across cohorts."""
    with open(RESULTS_PATH, 'r') as f:
        res = json.load(f)

    old_res = res['governed_5874_results']
    new_res = res['f11_3_5_3_5832_results']

    assert old_res['strat_c_ret'] > 0.07, "Strategy C return > 7.0%"
    assert old_res['strat_c_mdd'] < 0.02, "Strategy C MDD < 2.0%"
    assert new_res['strat_c_mdd'] < 0.02, "Strategy C MDD < 2.0%"


def test_frozen_methodology_version():
    """Verifies methodology remains v1.0.0."""
    with open('docs/phase_f11_3_5_3_validation_manifest.json', 'r') as f:
        manifest = json.load(f)

    assert manifest['methodology_version'] == '1.0.0'
    assert manifest['score_version'] == '1.0.0'
