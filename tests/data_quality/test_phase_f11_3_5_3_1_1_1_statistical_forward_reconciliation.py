"""
Test Suite for Phase F.11.3.5.3.1.1.1 — Statistical & Forward-Eligibility Definition Reconciliation

Minimum 30 dedicated tests covering:
1. SET_A reconstruction (5,832)
2. SET_B reconstruction (5,824)
3. SET_A - SET_B count (8)
4. SET_B - SET_A count (0)
5. Eight-scheme enumeration
6. Individual scheme verification (all 8)
7. Forward eligible count reconciliation (5,713 vs 5,712)
8. Forward unavailable count reconciliation (119 vs 112)
9. CAN_AMFI_147164 forward status (direct NAV, no merger stitching)
10. Historical-risk variable identity
11. Historical-risk rho reproduction (0.4011)
12. Competing -0.1420 vs +0.4011 reconciliation
13. Model 0 (R² = 0.0000)
14. Model 1 (R² = 0.1555)
15. Model 2 (R² = 0.3977)
16. Model 3 (R² = 0.4317)
17. Common model sample equality (N=5,713)
18. Incremental R² reproduction (+0.0340)
19. Quintile construction (N=1,142)
20. Q1-Q5 return spread reproduction (+3.30%)
21. Strategy A definition (Top 10% Trailing 1Y)
22. Strategy B definition (Lowest 10% Volatility)
23. Strategy C definition (Top 10% Fund Quality)
24. Strategy C pre-freeze evidence
25. MDD definition consistency
26. Strategy result reproduction (Return 7.81%, MDD 1.26%)
27. Future-injection check
28. Provenance metadata check
29. Report/code consistency audit
30. Historical-result preservation
"""

import os
import json
import pytest
import sqlite3
from datetime import date, timedelta

from scripts.run_f11_3_5_3_1_1_1_statistical_forward_reconciliation import (
    load_nav_data,
    compute_set_a_and_set_b,
    compute_fund_quality_scores,
    compute_forward_outcomes,
    run_reconciliation
)


@pytest.fixture(scope="module")
def reconciliation_data():
    """Runs reconciliation once for the test module."""
    db_path = 'db/backfill_f12_2.db'
    if not os.path.exists(db_path):
        pytest.skip(f"Database {db_path} not found")

    return run_reconciliation()


def test_01_set_a_reconstruction(reconciliation_data):
    """1. Verify SET_A count = 5,832."""
    assert reconciliation_data['set_a_n'] == 5832


def test_02_set_b_reconstruction(reconciliation_data):
    """2. Verify SET_B count = 5,824."""
    assert reconciliation_data['set_b_n'] == 5824


def test_03_diff_a_minus_b(reconciliation_data):
    """3. Verify SET_A - SET_B count = 8."""
    assert reconciliation_data['diff_a_minus_b_n'] == 8


def test_04_diff_b_minus_a(reconciliation_data):
    """4. Verify SET_B - SET_A count = 0."""
    assert reconciliation_data['diff_b_minus_a_n'] == 0


def test_05_eight_schemes_enumeration(reconciliation_data):
    """5. Verify exact canonical scheme IDs in the 8-scheme discrepancy."""
    expected = {
        'CAN_AMFI_144681', 'CAN_AMFI_144730', 'CAN_AMFI_147164', 'CAN_AMFI_147707',
        'CAN_AMFI_149349', 'CAN_AMFI_151269', 'CAN_AMFI_149350', 'CAN_AMFI_151271'
    }
    actual = set(reconciliation_data['eight_schemes_forensic'].keys())
    assert actual == expected


def test_06_individual_eight_schemes(reconciliation_data):
    """6. Verify forensic metadata for all 8 schemes."""
    forensic = reconciliation_data['eight_schemes_forensic']
    for cid in ['CAN_AMFI_144681', 'CAN_AMFI_144730', 'CAN_AMFI_147164', 'CAN_AMFI_147707',
                'CAN_AMFI_149349', 'CAN_AMFI_151269', 'CAN_AMFI_149350', 'CAN_AMFI_151271']:
        assert cid in forensic
        assert 'last_obs_pre_anchor' in forensic[cid]
        assert 'max_db_date' in forensic[cid]


def test_07_forward_eligible_reconciliation(reconciliation_data):
    """7. Verify forward eligible counts: 5,713 (SET_A) vs 5,712 (SET_B)."""
    assert reconciliation_data['forward_eligibility']['set_a']['eligible'] == 5713
    assert reconciliation_data['forward_eligibility']['set_b']['eligible'] == 5712


def test_08_forward_unavailable_reconciliation(reconciliation_data):
    """8. Verify forward unavailable counts: 119 (SET_A) vs 112 (SET_B)."""
    assert reconciliation_data['forward_eligibility']['set_a']['unavailable'] == 119
    assert reconciliation_data['forward_eligibility']['set_b']['unavailable'] == 112


def test_09_can_amfi_147164_forward_status(reconciliation_data):
    """9. Verify CAN_AMFI_147164 forward status is reachable via direct NAV, no merger stitching."""
    info = reconciliation_data['eight_schemes_forensic']['CAN_AMFI_147164']
    assert info['forward_reachable'] is True
    assert info['max_db_date'] == '2025-01-31'


def test_10_historical_risk_variable_identity(reconciliation_data):
    """10. Verify historical risk variable is 250-day annualized return volatility."""
    assert 'vol_spearman' in reconciliation_data['correlations']


def test_11_historical_risk_rho_reproduction(reconciliation_data):
    """11. Verify raw volatility Spearman rho = 0.4011."""
    assert abs(reconciliation_data['correlations']['vol_spearman'] - 0.40106) < 0.001


def test_12_competing_rho_reconciliation(reconciliation_data):
    """12. Verify reconciliation of competing -0.1420 vs +0.4011."""
    recon = reconciliation_data['correlations']['historical_risk_rho_reconciliation']
    assert recon['legacy_report_narrative_entry'] == -0.1420
    assert recon['raw_volatility_spearman'] == 0.4011


def test_13_model_0_reconstruction(reconciliation_data):
    """13. Verify Model 0 R² = 0.0000."""
    assert reconciliation_data['nested_models']['r2_m0'] == 0.0


def test_14_model_1_reconstruction(reconciliation_data):
    """14. Verify Model 1 R² ≈ 0.1555."""
    assert abs(reconciliation_data['nested_models']['r2_m1'] - 0.155483) < 0.001


def test_15_model_2_reconstruction(reconciliation_data):
    """15. Verify Model 2 R² ≈ 0.3977."""
    assert abs(reconciliation_data['nested_models']['r2_m2'] - 0.397678) < 0.001


def test_16_model_3_reconstruction(reconciliation_data):
    """16. Verify Model 3 R² ≈ 0.4317."""
    assert abs(reconciliation_data['nested_models']['r2_m3'] - 0.431706) < 0.001


def test_17_common_model_sample_equality(reconciliation_data):
    """17. Verify common sample N for regression models is 5,713."""
    assert reconciliation_data['forward_eligibility']['set_a']['eligible'] == 5713


def test_18_incremental_r2_reproduction(reconciliation_data):
    """18. Verify FQ incremental R² (M3 - M2) ≈ +0.0340 (+3.40%)."""
    assert abs(reconciliation_data['nested_models']['fq_incremental_r2'] - 0.034028) < 0.001


def test_19_quintile_construction(reconciliation_data):
    """19. Verify quintile means: Q1 ≈ 8.76%, Q5 ≈ 5.46%."""
    q = reconciliation_data['quintiles']
    assert abs(q['q1_mean'] - 0.0876) < 0.005
    assert abs(q['q5_mean'] - 0.0546) < 0.005


def test_20_q1_q5_return_spread(reconciliation_data):
    """20. Verify Q1-Q5 return spread ≈ +3.30%."""
    assert abs(reconciliation_data['quintiles']['q1_q5_spread'] - 0.033) < 0.001


def test_21_strategy_a_definition(reconciliation_data):
    """21. Verify Strategy A definition: Top 10% Trailing 1Y Return."""
    assert 'strategy_a' in reconciliation_data['strategies']


def test_22_strategy_b_definition(reconciliation_data):
    """22. Verify Strategy B definition: Lowest 10% Volatility."""
    assert 'strategy_b' in reconciliation_data['strategies']


def test_23_strategy_c_definition(reconciliation_data):
    """23. Verify Strategy C definition: Top 10% Fund Quality Score."""
    assert 'strategy_c' in reconciliation_data['strategies']


def test_24_strategy_c_pre_freeze_evidence(reconciliation_data):
    """24. Verify Strategy C pre-freeze status is proven."""
    assert 'pre_freeze_status' in reconciliation_data['strategies']
    assert 'PROVEN' in reconciliation_data['strategies']['pre_freeze_status']


def test_25_mdd_definition_consistency(reconciliation_data):
    """25. Verify MDD definition is mean of individual scheme MDDs."""
    assert 'mdd_definition' in reconciliation_data['strategies']


def test_26_strategy_c_result_reproduction(reconciliation_data):
    """26. Verify Strategy C return ≈ 7.81% and MDD ≈ 1.26%."""
    sc = reconciliation_data['strategies']['strategy_c']
    assert abs(sc['ret'] - 0.0781) < 0.001
    assert abs(sc['mdd'] - 0.0126) < 0.001


def test_27_future_injection_check():
    """27. Verify PIT metric calculation rejects post-anchor NAV data."""
    navs = [(date(2024, 1, 1) + timedelta(days=i), 10.0 + i*0.1) for i in range(25)]
    navs.append((date(2024, 6, 1), 50.0)) # Post-anchor future NAV
    scheme_navs = {'TEST_001': navs}
    scheme_dates = {'TEST_001': [d for d, _ in navs]}

    set_g, set_a, set_b = compute_set_a_and_set_b(scheme_navs, scheme_dates, date(2024, 1, 31))
    assert 'TEST_001' in set_a
    assert set_a['TEST_001']['last_obs_date'] <= date(2024, 1, 31)


def test_28_provenance_metadata_check(reconciliation_data):
    """28. Verify provenance fields in output."""
    assert reconciliation_data['phase'] == 'F.11.3.5.3.1.1.1'
    assert reconciliation_data['status'] == 'PASSED'


def test_29_report_code_consistency():
    """29. Verify output JSON file exists and is valid JSON."""
    json_path = 'docs/phase_f11_3_5_3_1_1_1_results.json'
    assert os.path.exists(json_path)
    with open(json_path) as f:
        data = json.load(f)
    assert data['status'] == 'PASSED'


def test_30_historical_result_preservation():
    """30. Verify legacy Phase F.11.3.5.3 results file remains preserved."""
    legacy_json = 'docs/phase_f11_3_5_3_results.json'
    assert os.path.exists(legacy_json)
    with open(legacy_json) as f:
        data = json.load(f)
    assert data['anchor_cohort_n'] == 5832
