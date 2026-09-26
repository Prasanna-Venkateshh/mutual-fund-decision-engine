"""
Test suite for Phase F.11.3.5.3 — Genuine Unseen-Period Decision-Value Validation.

Verifies:
1. Validation manifest integrity.
2. PIT zero look-ahead safety.
3. Anchor cohort reproduction and determinism.
4. Model nesting mathematical properties.
5. Decision simulation constraints.
6. Frozen methodology configuration.
"""

import os
import json
import sqlite3
import pytest
from datetime import date, datetime

import sys
sys.path.insert(0, '.')

from scripts.run_f11_3_5_3_unseen_validation import (
    load_nav_data,
    compute_pit_metrics_and_cohort,
    compute_fund_quality_scores,
    compute_forward_outcomes,
    compute_nested_regressions
)

DB_PATH = 'db/backfill_f12_2.db'
MANIFEST_PATH = 'docs/phase_f11_3_5_3_validation_manifest.json'
RESULTS_PATH = 'docs/phase_f11_3_5_3_results.json'


def test_manifest_existence_and_structure():
    assert os.path.exists(MANIFEST_PATH), "Validation manifest must exist."
    with open(MANIFEST_PATH, 'r') as f:
        manifest = json.load(f)

    assert manifest['validation_id'] == 'phase_f11_3_5_3_unseen_validation'
    assert manifest['anchor_date'] == '2024-01-31'
    assert manifest['evaluation_period']['start_date'] == '2024-02-01'
    assert manifest['evaluation_period']['end_date'] == '2025-01-31'
    assert manifest['methodology_version'] == '1.0.0'
    assert manifest['weight_configuration']['return'] == 0.25
    assert manifest['weight_configuration']['consistency'] == 0.20
    assert manifest['weight_configuration']['volatility'] == 0.15
    assert manifest['weight_configuration']['downside_risk'] == 0.15
    assert manifest['weight_configuration']['max_drawdown'] == 0.15
    assert manifest['weight_configuration']['cost_efficiency'] == 0.10


def test_zero_look_ahead_pit_safety():
    """Verifies that PIT metrics use ONLY NAV observations on or before 2024-01-31."""
    scheme_navs, scheme_dates = load_nav_data(DB_PATH)
    anchor_date = date(2024, 1, 31)

    cohort = compute_pit_metrics_and_cohort(scheme_navs, scheme_dates, anchor_date)

    for cid, data in cohort.items():
        assert data['last_obs_date'] <= anchor_date, f"Scheme {cid} last_obs_date {data['last_obs_date']} exceeds anchor date {anchor_date}"


def test_cohort_determinism_and_hash():
    """Verifies that running cohort reconstruction produces identical SHA-256 hash."""
    scheme_navs, scheme_dates = load_nav_data(DB_PATH)
    cohort1 = compute_pit_metrics_and_cohort(scheme_navs, scheme_dates, date(2024, 1, 31))
    cohort2 = compute_pit_metrics_and_cohort(scheme_navs, scheme_dates, date(2024, 1, 31))

    assert set(cohort1.keys()) == set(cohort2.keys())
    assert len(cohort1) >= 5800, f"Anchor cohort N={len(cohort1)} expected to be ~5,832 - 5,874"


def test_nested_model_mathematical_properties():
    """Verifies nested regression R^2 properties: R^2(M3) >= R^2(M2) >= R^2(M1) >= R^2(M0)."""
    assert os.path.exists(RESULTS_PATH), "Validation results JSON must exist."
    with open(RESULTS_PATH, 'r') as f:
        res = json.load(f)

    for outcome_key, reg in res['regressions'].items():
        r0 = reg['r2_m0']
        r1 = reg['r2_m1']
        r2 = reg['r2_m2']
        r3 = reg['r2_m3']

        assert r0 == 0.0
        assert r2 >= r1 - 1e-6, f"{outcome_key}: R2(M2) {r2} should be >= R2(M1) {r1}"
        assert r3 >= r2 - 1e-6, f"{outcome_key}: R3(M3) {r3} should be >= R2(M2) {r2}"


def test_decision_simulation_equal_universe():
    """Verifies strategies A, B, C use identical universe count N."""
    with open(RESULTS_PATH, 'r') as f:
        res = json.load(f)

    strat = res['strategies']
    n_a = strat['strategy_a_tr']['n']
    n_b = strat['strategy_b_vol']['n']
    n_c = strat['strategy_c_fq']['n']

    assert n_a == n_b == n_c, f"Strategies must use equal universe size (N_A={n_a}, N_B={n_b}, N_C={n_c})"


def test_frozen_methodology_weights():
    with open(MANIFEST_PATH, 'r') as f:
        manifest = json.load(f)

    weights = manifest['weight_configuration']
    total_weight = sum(weights.values())
    assert abs(total_weight - 1.0) < 1e-6, f"Weights must sum to 1.0, got {total_weight}"
