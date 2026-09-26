import json
import pytest
from pathlib import Path

RESULTS_JSON_PATH = Path("docs/phase_f11_3_5_3_1_1_2_1_1_1_results.json")

@pytest.fixture(scope="module")
def closure_results():
    assert RESULTS_JSON_PATH.exists(), f"Results JSON missing at {RESULTS_JSON_PATH}"
    with open(RESULTS_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def test_14_1_exact_comparator_b_down_definition(closure_results):
    comp = closure_results["comparator_b_down_definition"]
    assert comp["name"] == "COMPARATOR B-DOWN"
    assert comp["governed_metric"] == "LOWEST 10% HISTORICAL DOWNSIDE DEVIATION"
    assert comp["selected_n"] == 571
    assert "7df2abfa4b0cb9" in comp["cohort_sha256_hash"]

def test_14_2_exact_571_cohort_reconstruction(closure_results):
    cohort = closure_results["cohort_reconstruction"]
    assert cohort["total_scored_universe"] == 5713
    assert cohort["selected_decile_n"] == 571
    assert cohort["intersection_with_governed_strategy_b_vol"] == 475

def test_14_3_return_6_87_reproduction(closure_results):
    ret = closure_results["return_reconciliation"]["return_6_87"]
    assert ret["exact_value"] == 6.87
    assert ret["reproduced_value"] == 6.87
    assert ret["status"] == "6.87% = RECONCILED SECONDARY COMPARATOR RETURN"

def test_14_4_return_6_82_provenance_classification(closure_results):
    ret = closure_results["return_reconciliation"]["return_6_82"]
    assert ret["exact_value"] == 6.82
    assert ret["reproduced_value"] is None
    assert ret["status"] == "6.82 STATUS = UNRECONCILED HISTORICAL NARRATIVE VALUE — CALCULATION ORIGIN NOT REPRODUCIBLE"

def test_14_5_discrepancy_6_82_vs_6_87_handling(closure_results):
    diff = closure_results["return_reconciliation"]["diff_6_82_vs_6_87"]
    assert diff["difference_percentage_points"] == 0.05
    assert diff["status"] == "6.82% VS 6.87% = UNRESOLVED DISCREPANCY"

def test_14_6_cohort_mean_mdd_reproduction(closure_results):
    mdd = closure_results["mdd_reconciliation"]["cohort_mean_mdd"]
    assert mdd["formatted"] == "0.13%"
    assert mdd["exact_metric_name"] == "MEAN INDIVIDUAL-FUND FORWARD MAXIMUM DRAWDOWN"
    assert mdd["status"] == "0.13% = RECONCILED COMPARATOR B-DOWN MEAN MDD"

def test_14_7_cohort_median_mdd_reproduction(closure_results):
    mdd = closure_results["mdd_reconciliation"]["cohort_median_mdd"]
    assert mdd["formatted"] == "0.00%"
    assert mdd["exact_metric_name"] == "MEDIAN INDIVIDUAL-FUND FORWARD MAXIMUM DRAWDOWN"
    assert mdd["status"] == "0.00% = RECONCILED COMPARATOR B-DOWN MEDIAN MDD"

def test_14_8_mdd_0_45_provenance(closure_results):
    mdd = closure_results["mdd_reconciliation"]["mdd_0_45"]
    assert mdd["exact_value"] == 0.45
    assert mdd["reproduced_value"] is None
    assert mdd["status"] == "0.45 STATUS = UNRECONCILED HISTORICAL VALUE — CALCULATION ORIGIN NOT REPRODUCIBLE FROM CURRENT DATASET"

def test_14_9_no_cross_contamination_with_strategy_b(closure_results):
    cross = closure_results["cross_contamination_prevention"]
    assert cross["cross_contamination_detected"] is False
    assert cross["governed_strategy_b"]["return"] == "4.34%"
    assert cross["comparator_b_down"]["return"] == "6.87%"

def test_14_10_abc_mdd_comparability(closure_results):
    comp = closure_results["mdd_comparability_matrix"]
    assert comp["strategy_a_mean_mdd"] == "16.83%"
    assert comp["strategy_b_governed_mean_mdd"] == "0.11%"
    assert comp["strategy_c_mean_mdd"] == "1.26%"
    assert comp["comparator_b_down_mean_mdd"] == "0.13%"

def test_14_11_future_injection_invariance(closure_results):
    f_inj = closure_results["future_injection_invariance"]
    assert f_inj["comparator_b_down_membership_invariant"] is True
    assert f_inj["result"] == "PASS"

def test_14_12_deterministic_cohort_reconstruction(closure_results):
    comp = closure_results["comparator_b_down_definition"]
    assert comp["selected_n"] == 571
    assert len(comp["cohort_sha256_hash"]) == 64
