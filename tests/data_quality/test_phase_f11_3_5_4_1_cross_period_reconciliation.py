"""
Unit tests for Phase F.11.3.5.4.1 — Cross-Period Statistical Attribution & Evidence Reconciliation
"""

import pytest
import os
import json
import sqlite3
import numpy as np


@pytest.fixture(scope="module")
def reconciliation_results():
    json_path = 'docs/phase_f11_3_5_4_1_results.json'
    if not os.path.exists(json_path):
        from scripts.run_f11_3_5_4_1_reconciliation import run_forensic_reconciliation
        return run_forensic_reconciliation()
    with open(json_path, 'r') as f:
        return json.load(f)


def test_five_period_population_reproducibility(reconciliation_results):
    periods = reconciliation_results["period_reconciliations"]
    assert len(periods) == 5
    expected_n = [307, 426, 4515, 5166, 5713]
    for p, exp in zip(periods, expected_n):
        assert p["population_reconciliation"]["eligible_population_N"] == exp


def test_correlation_reproducibility(reconciliation_results):
    periods = reconciliation_results["period_reconciliations"]
    rhos = [p["correlations"]["fq_vs_fwd_ret"] for p in periods]
    assert len(rhos) == 5
    # Verify positive in 4 of 5 periods
    pos_count = sum(1 for r in rhos if r > 0)
    assert pos_count == 4


def test_nested_regression_reproducibility(reconciliation_results):
    periods = reconciliation_results["period_reconciliations"]
    for p in periods:
        reg = p["nested_regressions"]
        assert "r2_m0" in reg
        assert "r2_m1" in reg
        assert "r2_m2" in reg
        assert "r2_m3" in reg
        assert "fq_coefficient" in reg
        assert "fq_std_err" in reg
        assert "fq_t_stat" in reg
        assert "fq_p_val" in reg
        assert reg["r2_m3"] >= reg["r2_m2"] - 1e-6


def test_incremental_r2_reconciliation(reconciliation_results):
    summary = reconciliation_results["summary"]
    assert "simple_mean_incremental_r2" in summary
    assert "n_weighted_mean_incremental_r2" in summary
    assert summary["simple_mean_incremental_r2"] > 0
    assert summary["n_weighted_mean_incremental_r2"] > 0


def test_strategy_a_b_c_reproducibility(reconciliation_results):
    periods = reconciliation_results["period_reconciliations"]
    for p in periods:
        strats = p["strategies"]
        assert "strategy_a_top_tr" in strats
        assert "strategy_b_lowest_vol" in strats
        assert "strategy_c_top_fq" in strats


def test_fq_did_not_beat_trailing_return(reconciliation_results):
    summary = reconciliation_results["summary"]
    assert summary["fq_beat_trailing_return_count"] == "0 / 5"
    periods = reconciliation_results["period_reconciliations"]
    for p in periods:
        assert p["strategies"]["fq_beat_trailing_return"] is False


def test_quintile_reproducibility(reconciliation_results):
    periods = reconciliation_results["period_reconciliations"]
    monotonic_count = sum(1 for p in periods if p["quintiles"]["is_monotonic"])
    assert monotonic_count == 1  # Only P5 is monotonic


def test_limited_coverage_classification(reconciliation_results):
    periods = reconciliation_results["period_reconciliations"]
    assert periods[0]["coverage_class"] == "Limited-coverage historical validation period"
    assert periods[1]["coverage_class"] == "Limited-coverage historical validation period"
    assert periods[2]["coverage_class"] == "Full-coverage historical validation period"
    assert periods[3]["coverage_class"] == "Full-coverage historical validation period"
    assert periods[4]["coverage_class"] == "Full-coverage historical validation period"


def test_claim_matrix_completeness(reconciliation_results):
    claims = reconciliation_results["claim_matrix"]
    assert len(claims) == 9
    statuses = [c["status"] for c in claims]
    assert "SUPPORTED" in statuses
    assert "NOT SUPPORTED" in statuses
    assert "RESEARCH-ONLY" in statuses


def test_no_production_scoring_changes(reconciliation_results):
    assert reconciliation_results["production_methodology_changed"] is False
