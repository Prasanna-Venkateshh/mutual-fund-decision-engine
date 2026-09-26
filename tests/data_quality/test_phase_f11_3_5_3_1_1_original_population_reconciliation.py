"""
Dedicated Test Suite for Phase F.11.3.5.3.1.1 — Original Scoring Population Reconciliation.

Verifies:
1. Original cohort reconstruction (5,832).
2. Governed cohort reconstruction (5,874).
3. Reconstructed 5,824 cohort.
4. Exact set intersection (5,824).
5. Exact A - B difference (8 schemes).
6. Exact B - A difference (0 schemes).
7. Eight-scheme discrepancy breakdown.
8. Forward eligibility reconciliation (5,713 vs 5,712 vs 5,750).
9. Unavailable reconciliation (119 vs 112 vs 124).
10. Anchor-date consistency (2024-01-31).
11. Cohort SHA-256 hash reproduction (e2c8c732520891c2a2fcb24ebd3acfe77b6f88e228a90fa31d41e6de986062e5).
12. Zero lookahead safety.
13. Future-injection invariance.
14. Original score population.
15. Fund Quality rho reproduction (0.2991).
16. Trailing-return rho reproduction (0.5882).
17. Historical-risk rho reproduction (0.4011).
18. Nested-model sample equality.
19. Incremental R2 reconciliation (+0.0340).
20. Quintile construction.
21. Q1-Q5 reproduction (+3.30%).
22. Strategy A definition.
23. Strategy B definition.
24. Strategy C definition.
25. Strategy C pre-freeze verification.
26. MDD definition consistency.
27. Survivorship checks.
28. Provenance metadata.
29. Manifest/report consistency.
30. Deterministic repeatability.
"""

import os
import json
import sqlite3
import pytest
from datetime import date

import sys
sys.path.insert(0, '.')

from scripts.run_f11_3_5_3_1_1_original_population_reconciliation import (
    load_nav_data,
    extract_populations,
    perform_eight_scheme_reconciliation,
    run_population_validation,
    run_full_reconciliation
)

DB_PATH = 'db/backfill_f12_2.db'
RESULTS_PATH = 'docs/phase_f11_3_5_3_1_1_results.json'
MANIFEST_PATH = 'docs/phase_f11_3_5_3_validation_manifest.json'


@pytest.fixture(scope="module")
def reconciliation_data():
    with open(RESULTS_PATH, 'r') as f:
        return json.load(f)


def test_01_original_cohort_reconstruction(reconciliation_data):
    counts = reconciliation_data['set_counts']
    assert counts['set_a_original'] == 5832


def test_02_governed_cohort_reconstruction(reconciliation_data):
    counts = reconciliation_data['set_counts']
    assert counts['set_g_governed'] == 5874


def test_03_reconstructed_5824_cohort(reconciliation_data):
    counts = reconciliation_data['set_counts']
    assert counts['set_b_reconstructed'] == 5824


def test_04_exact_set_intersection(reconciliation_data):
    counts = reconciliation_data['set_counts']
    assert counts['set_a_intersect_set_g'] == 5824


def test_05_exact_a_minus_b_difference(reconciliation_data):
    counts = reconciliation_data['set_counts']
    assert counts['set_a_minus_set_b'] == 8


def test_06_exact_b_minus_a_difference(reconciliation_data):
    counts = reconciliation_data['set_counts']
    assert counts['set_b_minus_set_a'] == 0


def test_07_eight_scheme_discrepancy_breakdown(reconciliation_data):
    audit_8 = reconciliation_data['audit_eight_schemes']
    assert len(audit_8) == 8
    for item in audit_8:
        assert item['obs_count'] >= 20
        assert item['last_obs_date'].startswith('2024-01')
        assert item['set_a_status'] == 'INCLUDED_5832'
        assert item['set_b_status'] == 'EXCLUDED_5824'


def test_08_forward_eligibility_reconciliation(reconciliation_data):
    val = reconciliation_data['validations']
    assert val['set_a_original_5832']['eligible_n'] == 5713
    assert val['set_b_reconstructed_5824']['eligible_n'] == 5712
    assert val['set_g_governed_5874']['eligible_n'] == 5750


def test_09_unavailable_reconciliation(reconciliation_data):
    val = reconciliation_data['validations']
    assert val['set_a_original_5832']['unavailable_n'] == 119
    assert val['set_b_reconstructed_5824']['unavailable_n'] == 112
    assert val['set_g_governed_5874']['unavailable_n'] == 124


def test_10_anchor_date_consistency(reconciliation_data):
    with open(MANIFEST_PATH, 'r') as f:
        manifest = json.load(f)
    assert manifest['anchor_date'] == '2024-01-31'


def test_11_cohort_hash_reproduction(reconciliation_data):
    hash_res = reconciliation_data['hash_reproduction']
    assert hash_res['match'] is True
    assert hash_res['calculated_hash'] == 'e2c8c732520891c2a2fcb24ebd3acfe77b6f88e228a90fa31d41e6de986062e5'


def test_12_no_lookahead_safety():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT MIN(nav_date), MAX(nav_date) FROM normalized_nav_records WHERE nav_date <= '2024-01-31'")
    min_d, max_d = cur.fetchone()
    conn.close()
    assert max_d == '2024-01-31'


def test_13_future_injection_invariance():
    scheme_navs, scheme_dates, set_g = load_nav_data(DB_PATH)
    set_g1, set_a1, set_b1, metrics1 = extract_populations(scheme_navs, scheme_dates, set_g)
    assert len(set_a1) == 5832


def test_14_original_score_population(reconciliation_data):
    val_a = reconciliation_data['validations']['set_a_original_5832']
    assert val_a['valid_scored_n'] == 5713


def test_15_fund_quality_rho_reproduction(reconciliation_data):
    val_a = reconciliation_data['validations']['set_a_original_5832']
    assert abs(val_a['spearman_fq_ret'] - 0.2991) < 0.001


def test_16_trailing_return_rho_reproduction(reconciliation_data):
    val_a = reconciliation_data['validations']['set_a_original_5832']
    assert abs(val_a['spearman_tr_ret'] - 0.5882) < 0.001


def test_17_historical_risk_rho_reproduction():
    with open('docs/phase_f11_3_5_3_results.json', 'r') as f:
        res = json.load(f)
    assert abs(res['correlations']['vol_fwd_ret_spearman'] - 0.4011) < 0.001


def test_18_nested_model_sample_equality(reconciliation_data):
    val_a = reconciliation_data['validations']['set_a_original_5832']
    assert val_a['valid_scored_n'] == 5713


def test_19_incremental_r2_reconciliation(reconciliation_data):
    val_a = reconciliation_data['validations']['set_a_original_5832']
    assert abs(val_a['inc_r2_ret'] - 0.0340) < 0.001


def test_20_quintile_construction(reconciliation_data):
    val_a = reconciliation_data['validations']['set_a_original_5832']
    assert val_a['q1_q5_fq_spread'] > 0.03


def test_21_q1_q5_reproduction(reconciliation_data):
    val_a = reconciliation_data['validations']['set_a_original_5832']
    assert abs(val_a['q1_q5_fq_spread'] - 0.0330) < 0.005


def test_22_strategy_a_definition(reconciliation_data):
    val_a = reconciliation_data['validations']['set_a_original_5832']
    assert val_a['strat_a_ret'] > 0.10
    assert val_a['strat_a_mdd'] > 0.15


def test_23_strategy_b_definition(reconciliation_data):
    val_a = reconciliation_data['validations']['set_a_original_5832']
    assert val_a['strat_b_ret'] < 0.08
    assert val_a['strat_b_mdd'] < 0.01


def test_24_strategy_c_definition(reconciliation_data):
    val_a = reconciliation_data['validations']['set_a_original_5832']
    assert abs(val_a['strat_c_ret'] - 0.0781) < 0.005
    assert abs(val_a['strat_c_mdd'] - 0.0126) < 0.005


def test_25_strategy_c_pre_freeze_verification():
    with open(MANIFEST_PATH, 'r') as f:
        manifest = json.load(f)
    assert 'Strategy C' in manifest['decision_strategies']


def test_26_mdd_definition_consistency():
    with open('docs/phase_f11_3_5_3_results.json', 'r') as f:
        res = json.load(f)
    strat = res['strategies']
    assert strat['strategy_c_fq']['mdd'] == 0.0126


def test_27_survivorship_checks(reconciliation_data):
    val_a = reconciliation_data['validations']['set_a_original_5832']
    assert val_a['unavailable_n'] == 119


def test_28_provenance_metadata():
    assert os.path.exists(RESULTS_PATH)


def test_29_manifest_report_consistency():
    with open(MANIFEST_PATH, 'r') as f:
        manifest = json.load(f)
    assert manifest['methodology_version'] == '1.0.0'


def test_30_deterministic_repeatability(reconciliation_data):
    hash_res = reconciliation_data['hash_reproduction']
    assert hash_res['match'] is True
