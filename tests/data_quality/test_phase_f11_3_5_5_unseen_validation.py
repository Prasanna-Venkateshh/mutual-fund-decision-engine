"""
Unit tests for Phase F.11.3.5.5 — Genuine Unseen-Period Decision-Value Validation
"""

import pytest
import os
import json


@pytest.fixture(scope="module")
def unseen_results():
    json_path = 'docs/phase_f11_3_5_5_results.json'
    if not os.path.exists(json_path):
        from scripts.run_f11_3_5_5_unseen_validation import run_unseen_validation
        return run_unseen_validation()
    with open(json_path, 'r') as f:
        return json.load(f)


@pytest.fixture(scope="module")
def validation_manifest():
    manifest_path = 'docs/phase_f11_3_5_5_validation_manifest.json'
    assert os.path.exists(manifest_path)
    with open(manifest_path, 'r') as f:
        return json.load(f)


def test_frozen_validation_manifest(validation_manifest):
    assert validation_manifest["manifest_version"] == "F.11.3.5.5-v1.0"
    assert validation_manifest["anchor_date"] == "2024-01-31"
    assert validation_manifest["forward_start_date"] == "2024-02-01"
    assert validation_manifest["forward_end_date"] == "2025-01-31"
    assert "manifest_sha256" in validation_manifest


def test_anchor_cohort_reconciliation(unseen_results):
    pop = unseen_results["population_waterfall"]
    assert pop["anchor_cohort_total"] == 5874
    assert pop["forward_reachable_total"] == 5750
    assert pop["unavailable_total"] == 124
    assert pop["final_outcome_population"] == 5713
    assert pop["decile_cohort_size"] == 571


def test_pit_safety_audit(unseen_results):
    pit = unseen_results["pit_safety_audit"]
    assert pit["future_information_leakage_detected"] is False
    assert pit["max_observation_date_checked"] <= "2024-01-31"


def test_strategy_a_b_c_results(unseen_results):
    strats = unseen_results["strategy_results"]
    assert strats["strategy_a_top_tr"]["mean_fwd_ret"] == "12.23%"
    assert strats["strategy_b_lowest_vol"]["mean_fwd_ret"] == "4.34%"
    assert strats["strategy_c_top_fq"]["mean_fwd_ret"] == "11.85%"
    assert strats["fq_beat_trailing_return"] is False


def test_cohort_overlap_reproducibility(unseen_results):
    overlap = unseen_results["strategy_results"]["cohort_overlap_a_vs_c"]
    assert overlap["shared_n"] == 536
    assert overlap["jaccard_similarity"] == 0.8845


def test_nested_regression_results(unseen_results):
    reg = unseen_results["nested_regressions"]
    assert reg["N"] == 5713
    assert reg["r2_m1"] == 0.155483
    assert reg["r2_m2"] == 0.380564
    assert reg["r2_m3"] == 0.386438
    assert reg["incremental_r2"] == 0.005874
    assert reg["fq_beta"] == 0.935340


def test_quintile_monotonicity(unseen_results):
    q = unseen_results["quintile_results"]
    assert q["is_monotonic"] is True
    assert q["returns"] == ["12.02%", "10.18%", "8.07%", "7.10%", "3.17%"]


def test_explanation_objects_completeness(unseen_results):
    exps = unseen_results["explanation_objects"]
    assert len(exps) >= 2
    for exp in exps:
        assert "result_name" in exp
        assert "numerical_value" in exp
        assert "interpretation" in exp
        assert "non_interpretation" in exp


def test_representative_traces(unseen_results):
    traces = unseen_results["representative_traces"]
    assert len(traces) >= 5
    for t in traces:
        reconstructed = 0.5 * t["volatility_component"] + 0.5 * t["trailing_return_component"]
        assert abs(reconstructed - t["reconstructed_fq_score"]) < 1e-4


def test_claim_matrix_completeness(unseen_results):
    claims = unseen_results["claim_matrix"]
    assert len(claims) == 9
    statuses = [c["status"] for c in claims]
    assert "SUPPORTED" in statuses
    assert "NOT SUPPORTED" in statuses
    assert "RESEARCH-ONLY" in statuses


def test_no_production_scoring_changes(unseen_results):
    assert unseen_results["production_methodology_changed"] is False
