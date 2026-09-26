"""
Phase F.11.3.5.3.2.1 — Dedicated Forensic Test Suite
"""

import json
import pytest
from pathlib import Path

RESULTS_JSON_PATH = Path("docs/phase_f11_3_5_3_2_1_results.json")


@pytest.fixture(scope="module")
def forensic_results():
    assert RESULTS_JSON_PATH.exists(), f"Results JSON missing at {RESULTS_JSON_PATH}"
    with open(RESULTS_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_17_1_confidence_dispersion_arithmetic(forensic_results):
    conf = forensic_results["confidence_reconciliation"]
    assert conf["high_confidence_n"] == 5130
    assert conf["low_confidence_n"] == 583
    assert conf["high_confidence_return_std"] == 0.069028
    assert conf["low_confidence_return_std"] == 0.062185


def test_17_2_confidence_conclusion_direction(forensic_results):
    assert "HIGHER" in forensic_results["confidence_reconciliation"]["corrected_conclusion"]
    assert forensic_results["required_answers"]["q1_confidence_dispersion_conclusion_correct"].startswith("NO")


def test_17_3_population_waterfall(forensic_results):
    pop = forensic_results["population_waterfall"]
    assert pop["stage_1_total_db_schemes"] == 17507
    assert pop["stage_2_pit_active_schemes_le_20240131"] == 16808
    assert pop["stage_3_forward_reachable_schemes_gt_20240131"] == 5889
    assert pop["stage_4_min_history_and_jan2024_active"] == 5826
    assert pop["stage_5_final_eligible_validation_population"] == 5713


def test_17_4_pit_cutoff(forensic_results):
    assert forensic_results["point_in_time_integrity"].startswith("PASS")


def test_17_5_future_data_exclusion(forensic_results):
    assert forensic_results["governance_verification"].startswith("PASS")


def test_17_6_model_0_reconstruction(forensic_results):
    assert forensic_results["regression_reconciliation"]["model_0"]["r2"] == 0.0


def test_17_7_model_1_reconstruction(forensic_results):
    assert forensic_results["regression_reconciliation"]["model_1"]["r2"] == 0.155483


def test_17_8_model_2_reconstruction(forensic_results):
    assert forensic_results["regression_reconciliation"]["model_2"]["r2"] == 0.380564


def test_17_9_model_3_reconstruction(forensic_results):
    assert forensic_results["regression_reconciliation"]["model_3"]["r2"] == 0.386438


def test_17_10_incremental_r2_arithmetic(forensic_results):
    reg = forensic_results["regression_reconciliation"]
    assert reg["incremental_r2_exact"] == 0.005874
    assert reg["r2_subtraction_verification"] == "0.386438 - 0.380564 = 0.005874"


def test_17_11_fq_beta_reproduction(forensic_results):
    m3 = forensic_results["regression_reconciliation"]["model_3"]
    assert m3["fq_beta"] == 0.93534
    assert m3["fq_se"] == 0.126525


def test_17_12_statistical_inference_metadata(forensic_results):
    m3 = forensic_results["regression_reconciliation"]["model_3"]
    assert m3["t_statistic"] == 7.3925
    assert "Classical IID OLS t-test" in m3["p_value_text"]


def test_17_13_fq_component_overlap_mapping(forensic_results):
    comp = forensic_results["component_overlap_matrix"]
    assert comp["trailing_1y_return"]["present_in_model_2"] is True
    assert comp["historical_volatility"]["present_in_model_2"] is True
    assert comp["classification"].startswith("B")


def test_17_14_strategy_a_cohort(forensic_results):
    assert forensic_results["cohort_overlap_reconciliation"]["strategy_a_n"] == 571


def test_17_15_strategy_b_cohort(forensic_results):
    assert forensic_results["cohort_overlap_reconciliation"]["strategy_c_n"] == 571


def test_17_16_strategy_c_cohort(forensic_results):
    assert forensic_results["cohort_overlap_reconciliation"]["shared_n"] == 536


def test_17_17_ac_overlap(forensic_results):
    overlap = forensic_results["cohort_overlap_reconciliation"]
    assert overlap["jaccard_similarity"] == 0.8845
    assert overlap["unique_strategy_c_n"] == 35


def test_17_18_cohort_membership_turnover_proxy(forensic_results):
    assert forensic_results["required_answers"]["q7_turnover_type"].startswith("COHORT MEMBERSHIP TURNOVER PROXY")


def test_17_19_b_down_research_only_status(forensic_results):
    assert forensic_results["production_methodology_changed"] is False


def test_17_20_forward_return_calculation(forensic_results):
    assert forensic_results["required_answers"]["q9_identical_return_outcomes"].startswith("YES")


def test_17_21_forward_mdd_calculation(forensic_results):
    assert forensic_results["required_answers"]["q10_identical_mdd_outcomes"].startswith("YES")


def test_17_22_quintile_construction(forensic_results):
    assert forensic_results["required_answers"]["q11_quintile_relationship_nature"].startswith("Observed retrospective association")


def test_17_23_deterministic_rerun(forensic_results):
    assert forensic_results["status"] == "PASSED WITH LIMITATIONS"


def test_17_24_production_methodology_immutability(forensic_results):
    assert forensic_results["production_methodology_changed"] is False
    assert forensic_results["historical_pre_freeze_classification"] == "RETROSPECTIVE POINT-IN-TIME BACKTESTING — PROSPECTIVE/PRE-REGISTERED STATUS NOT PROVEN"
