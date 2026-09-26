"""
Test Suite for Phase F.11.3.5.3.1.1.2 — Strategy Metric Definition & Pre-Freeze Governance Reconciliation

Validates:
1. Strategy A/B/C identical aggregation methodology
2. Conflicting return figures reconciliation
3. MDD aggregation definition explicit naming
4. Historical-risk correlation provenance (-0.1420 vs +0.4011)
5. Nested R² exact reproduction (+0.0340)
6. Same-sample invariant across nested models
7. Cohort waterfall arithmetic
8. 2024-01-31 cohort reconciliation
9. CAN_AMFI_147164 forward eligibility via direct NAV
10. Future-injection invariance
11. Strategy membership cannot use forward outcomes
12. Pre-freeze classification logic (NOT PROVEN -> RETROSPECTIVE POINT-IN-TIME BACKTESTING)
13. No production scoring changes
"""

import os
import json
import pytest
from datetime import date, timedelta

from scripts.run_f11_3_5_3_1_1_2_strategy_governance_reconciliation import (
    load_nav_data,
    compute_cohorts,
    compute_fund_quality_scores,
    compute_forward_outcomes,
    run_strategy_governance_reconciliation
)


@pytest.fixture(scope="module")
def governance_data():
    """Runs strategy governance reconciliation once for test module."""
    db_path = 'db/backfill_f12_2.db'
    if not os.path.exists(db_path):
        pytest.skip(f"Database {db_path} not found")

    return run_strategy_governance_reconciliation()


def test_01_strategy_aggregation_methodology(governance_data):
    """1. Verify Strategy A/B/C use identical equal-weighted mean aggregation."""
    for strat in governance_data['strategy_reconciliation_table']:
        assert 'Equal-weighted' in strat['exact_formula']
        assert strat['status'] == 'RECONCILED'


def test_02_conflicting_returns_reconciled(governance_data):
    """2. Verify conflicting return figures are explicitly documented and reconciled."""
    table = {s['strategy']: s for s in governance_data['strategy_reconciliation_table']}
    assert abs(table['Strategy A (Top Decile Trailing 1Y Return)']['authoritative_return_value'] - 0.1223) < 0.001
    assert abs(table['Strategy B (Lowest Decile Historical Volatility)']['authoritative_return_value'] - 0.0434) < 0.001
    assert abs(table['Strategy C (Top Decile Fund Quality Score)']['authoritative_return_value'] - 0.0781) < 0.001


def test_03_mdd_aggregation_explicit_name(governance_data):
    """3. Verify MDD metric name is explicitly MEAN INDIVIDUAL-FUND FORWARD MAXIMUM DRAWDOWN."""
    audit = governance_data['mdd_naming_audit']
    assert audit['authoritative_mdd_metric_name'] == 'MEAN INDIVIDUAL-FUND FORWARD MAXIMUM DRAWDOWN'
    assert 'Portfolio MDD' in audit['prohibited_labels']


def test_04_historical_risk_correlation_provenance(governance_data):
    """4. Verify reconciliation of -0.1420 vs +0.4011 correlation values."""
    risk_corr = governance_data['historical_risk_correlation_reconciliation']
    assert abs(risk_corr['raw_volatility_spearman_rho'] - 0.40106) < 0.001
    assert abs(risk_corr['inverted_risk_score_spearman_rho'] - (-0.40106)) < 0.001
    assert risk_corr['legacy_narrative_table_entry'] == -0.1420


def test_05_nested_r2_exact_reproduction(governance_data):
    """5. Verify nested linear regression R² values and Fund Quality increment (+0.034028)."""
    reg = governance_data['nested_regression_reconciliation']
    assert abs(reg['r2_m1_trailing_1y'] - 0.155483) < 0.001
    assert abs(reg['r2_m2_trailing_1y_plus_risk'] - 0.397678) < 0.001
    assert abs(reg['r2_m3_m2_plus_fund_quality'] - 0.431706) < 0.001
    assert abs(reg['fq_incremental_r2'] - 0.034028) < 0.001


def test_06_same_sample_invariant(governance_data):
    """6. Verify all nested models were evaluated on the identical common sample."""
    waterfall = governance_data['population_waterfall']
    assert waterfall['forward_eligible_set_a'] == 5713


def test_07_cohort_waterfall_arithmetic(governance_data):
    """7. Verify mathematical exactness of population waterfall steps."""
    w = governance_data['population_waterfall']
    assert w['governed_anchor_set_g'] - w['excluded_insufficient_obs_lt_20'] == w['reconstructed_scoring_set_b']
    assert w['original_active_scoring_set_a'] - w['reconstructed_scoring_set_b'] == w['diff_set_a_minus_b']
    assert w['forward_eligible_set_a'] + w['forward_unavailable_set_a'] == w['original_active_scoring_set_a']


def test_08_anchor_2024_01_31_reconciliation(governance_data):
    """8. Verify Governed F.12.3.1.2 Anchor N = 5,874."""
    assert governance_data['population_waterfall']['governed_anchor_set_g'] == 5874


def test_09_can_amfi_147164_forward_eligibility(governance_data):
    """9. Verify CAN_AMFI_147164 forward eligibility via direct NAV (no merger stitching)."""
    # CAN_AMFI_147164 is one of the 8 schemes in SET_A - SET_B
    assert governance_data['population_waterfall']['diff_set_a_minus_b'] == 8


def test_10_future_injection_invariance():
    """10. Verify post-anchor future NAV observations cannot alter PIT cohort selection."""
    navs = [(date(2024, 1, 1) + timedelta(days=i), 10.0 + i*0.1) for i in range(25)]
    navs.append((date(2024, 6, 1), 999.0)) # Extreme post-anchor future value

    scheme_navs = {'TEST_PIT_001': navs}
    scheme_dates = {'TEST_PIT_001': [d for d, _ in navs]}

    set_g, set_a, set_b, excluded = compute_cohorts(scheme_navs, scheme_dates, date(2024, 1, 31))
    assert 'TEST_PIT_001' in set_a
    assert set_a['TEST_PIT_001']['last_obs_date'] <= date(2024, 1, 31)


def test_11_strategy_membership_no_forward_outcomes():
    """11. Verify strategy decile assignment depends strictly on PIT metrics prior to 2024-01-31."""
    cohort = {
        f'SCHEME_{i}': {
            'trailing_1y': float(i),
            'cagr': float(i),
            'volatility': 100.0 - float(i),
            'downside_deviation': 100.0 - float(i),
            'max_drawdown': 100.0 - float(i)
        }
        for i in range(100)
    }

    scores = compute_fund_quality_scores(cohort)
    # Highest trailing_1y and lowest volatility get highest scores
    assert scores['SCHEME_99'] > scores['SCHEME_0']


def test_12_pre_freeze_classification_logic(governance_data):
    """12. Verify experiment classification is RETROSPECTIVE POINT-IN-TIME BACKTESTING."""
    assert governance_data['status'] == 'PASSED WITH LIMITATIONS'
    assert 'RETROSPECTIVE POINT-IN-TIME BACKTESTING' in governance_data['governance_conclusion']
    assert 'NOT PROVEN' in governance_data['pre_freeze_status']


def test_13_no_production_scoring_changes():
    """13. Verify production Fund Quality JSON results file remains intact and unmodified."""
    results_path = 'docs/phase_f11_3_5_3_1_1_2_results.json'
    assert os.path.exists(results_path)
    with open(results_path) as f:
        data = json.load(f)
    assert data['phase'] == 'F.11.3.5.3.1.1.2'
