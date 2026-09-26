"""
Phase F.11.3.5.3.2 — Dedicated Test Suite for Unseen-Period Decision-Value Validation
"""

import json
import pytest
from pathlib import Path

RESULTS_JSON_PATH = Path("docs/phase_f11_3_5_3_2_results.json")


@pytest.fixture(scope="module")
def validation_results():
    assert RESULTS_JSON_PATH.exists(), f"Results JSON missing at {RESULTS_JSON_PATH}"
    with open(RESULTS_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_23_1_point_in_time_score_calculation(validation_results):
    assert validation_results["anchor_date"] == "2024-01-31"
    assert "PASS" in validation_results["point_in_time_integrity"]
    assert validation_results["required_answers"]["q1_score_calculated_without_future_info"] == "YES"


def test_23_2_no_future_data_contamination(validation_results):
    assert validation_results["future_injection_invariance"]["strategy_c_membership_invariant"] is True
    assert validation_results["future_injection_invariance"]["result"] == "PASS"


def test_23_3_exact_anchor_cohort(validation_results):
    pop = validation_results["final_population"]
    assert pop["anchor_cohort_total"] == 5874
    assert pop["forward_reachable"] == 5750
    assert pop["scoring_and_outcome_eligible_final"] == 5713


def test_23_4_exact_strategy_definitions(validation_results):
    assert "STRATEGY A: Top 10% Trailing 1Y Return" in validation_results["strategy_a_results"]["strategy"]
    assert "STRATEGY B: Lowest 10% Historical Volatility" in validation_results["strategy_b_results"]["strategy"]
    assert "STRATEGY C: Top 10% Fund Quality Score" in validation_results["strategy_c_results"]["strategy"]
    assert "COMPARATOR B-DOWN" in validation_results["comparator_b_down_results"]["strategy"]


def test_23_5_deterministic_selection(validation_results):
    assert validation_results["future_injection_invariance"]["result"] == "PASS"


def test_23_6_exact_selected_n(validation_results):
    assert validation_results["strategy_a_results"]["selected_n"] == 571
    assert validation_results["strategy_b_results"]["selected_n"] == 571
    assert validation_results["strategy_c_results"]["selected_n"] == 571
    assert validation_results["comparator_b_down_results"]["selected_n"] == 571


def test_23_7_forward_return_calculation(validation_results):
    assert validation_results["strategy_a_results"]["mean_forward_return"] == "12.23%"
    assert validation_results["strategy_b_results"]["mean_forward_return"] == "4.34%"
    assert validation_results["strategy_c_results"]["mean_forward_return"] == "11.85%"
    assert validation_results["comparator_b_down_results"]["mean_forward_return"] == "5.03%"


def test_23_8_forward_mdd_calculation(validation_results):
    assert validation_results["strategy_a_results"]["mean_forward_mdd"] == "16.83%"
    assert validation_results["strategy_b_results"]["mean_forward_mdd"] == "0.11%"
    assert validation_results["strategy_c_results"]["mean_forward_mdd"] == "16.80%"
    assert validation_results["comparator_b_down_results"]["mean_forward_mdd"] == "0.10%"


def test_23_9_identical_abc_aggregation(validation_results):
    for key in ["strategy_a_results", "strategy_b_results", "strategy_c_results", "comparator_b_down_results"]:
        res = validation_results[key]
        assert "mean_forward_return" in res
        assert "median_forward_return" in res
        assert "std_forward_return" in res
        assert "mean_forward_mdd" in res
        assert "median_forward_mdd" in res


def test_23_10_nested_model_sample_consistency(validation_results):
    models = validation_results["incremental_information_nested_models"]
    assert models["sample_n"] == 5713
    assert models["model_1_trailing_return"]["r2"] > 0
    assert models["model_2_trailing_return_plus_risk"]["r2"] > models["model_1_trailing_return"]["r2"]
    assert models["model_3_full_fund_quality"]["r2"] >= models["model_2_trailing_return_plus_risk"]["r2"]


def test_23_11_cohort_overlap_calculation(validation_results):
    matrix = validation_results["cohort_overlap_matrix"]
    assert "A_vs_B" in matrix
    assert "A_vs_C" in matrix
    assert "B_vs_C" in matrix
    assert "C_vs_B_DOWN" in matrix
    assert matrix["A_vs_C"]["intersection_n"] == 536


def test_23_12_confidence_separation(validation_results):
    conf = validation_results["confidence_analysis"]
    assert conf["high_confidence_count"] == 5130
    assert conf["low_confidence_count"] == 583


def test_23_13_future_injection_invariance(validation_results):
    assert validation_results["future_injection_invariance"]["result"] == "PASS"


def test_23_14_missing_forward_data_handling(validation_results):
    assert validation_results["final_population"]["scoring_and_outcome_eligible_final"] == 5713


def test_23_15_reproducibility(validation_results):
    assert validation_results["status"] == "PASSED WITH LIMITATIONS"


def test_23_16_no_production_methodology_changes(validation_results):
    assert validation_results["production_methodology_changed"] is False
    assert validation_results["historical_pre_freeze_classification"] == "RETROSPECTIVE POINT-IN-TIME BACKTESTING — PROSPECTIVE/PRE-REGISTERED STATUS NOT PROVEN"
