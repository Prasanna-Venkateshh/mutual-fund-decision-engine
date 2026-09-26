import json
import pytest
from pathlib import Path

RESULTS_JSON_PATH = Path("docs/phase_f11_3_5_3_1_1_2_1_results.json")

@pytest.fixture(scope="module")
def closure_results():
    assert RESULTS_JSON_PATH.exists(), f"Results JSON missing at {RESULTS_JSON_PATH}"
    with open(RESULTS_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def test_10_1_strategy_a_12_23_provenance(closure_results):
    st_a = closure_results["metrics"]["strategy_a_12_23"]
    assert st_a["status"] == "RECONCILED"
    assert st_a["exact_value"] == 12.23
    assert st_a["selection_rule"] == "Top 10% Trailing 1Y Return"
    assert st_a["sample_size"] == 571

def test_10_2_strategy_a_7_56_provenance(closure_results):
    st_a_756 = closure_results["metrics"]["strategy_a_7_56"]
    assert st_a_756["status"] == "UNRECONCILED — ORIGIN NOT PROVEN"
    assert st_a_756["exact_value"] is None

def test_10_3_strategy_b_4_34_provenance(closure_results):
    st_b_434 = closure_results["metrics"]["strategy_b_4_34"]
    assert st_b_434["status"] == "RECONCILED"
    assert st_b_434["exact_value"] == 4.34
    assert st_b_434["selection_rule"] == "Lowest 10% Historical Volatility"
    assert st_b_434["sample_size"] == 571

def test_10_4_strategy_b_6_82_provenance(closure_results):
    st_b_682 = closure_results["metrics"]["strategy_b_6_82"]
    assert st_b_682["status"] == "RECONCILED AS SEPARATE DOWNSIDE RISK COMPARATOR"
    assert st_b_682["exact_value"] == 6.82
    assert st_b_682["selection_rule"] == "Lowest 10% Historical Downside Risk"
    assert st_b_682["sample_size"] == 571

def test_10_5_strategy_b_6_87_provenance(closure_results):
    st_b_687 = closure_results["metrics"]["strategy_b_6_87"]
    assert st_b_687["status"] == "RECONCILED AS SEPARATE DOWNSIDE RISK COMPARATOR"
    assert st_b_687["exact_value"] == 6.87
    assert st_b_687["selection_rule"] == "Lowest 10% Historical Downside Risk (Alternative Aggregation)"

def test_10_6_strategy_c_7_81_provenance(closure_results):
    st_c_781 = closure_results["metrics"]["strategy_c_7_81"]
    assert st_c_781["status"] == "RECONCILED"
    assert st_c_781["exact_value"] == 7.81
    assert st_c_781["selection_rule"] == "Top 10% Fund Quality Score"
    assert st_c_781["sample_size"] == 571

def test_10_7_mdd_16_83_provenance(closure_results):
    mdd = closure_results["metrics"]["mdd_16_83"]
    assert mdd["status"] == "RECONCILED"
    assert mdd["exact_value"] == 16.83
    assert mdd["metric_name"] == "MEAN INDIVIDUAL-FUND FORWARD MAXIMUM DRAWDOWN"
    assert mdd["strategy"] == "Strategy A"

def test_10_8_mdd_0_11_provenance(closure_results):
    mdd = closure_results["metrics"]["mdd_0_11"]
    assert mdd["status"] == "RECONCILED"
    assert mdd["exact_value"] == 0.11
    assert mdd["metric_name"] == "MEAN INDIVIDUAL-FUND FORWARD MAXIMUM DRAWDOWN"
    assert mdd["strategy"] == "Strategy B (Historical Volatility Sort)"

def test_10_9_mdd_0_45_provenance(closure_results):
    mdd = closure_results["metrics"]["mdd_0_45"]
    assert mdd["status"] == "RECONCILED AS MEDIAN COMPARATOR"
    assert mdd["exact_value"] == 0.45
    assert mdd["metric_name"] == "MEDIAN INDIVIDUAL-FUND FORWARD MAXIMUM DRAWDOWN"
    assert mdd["strategy"] == "Strategy B (Downside Risk Sort)"

def test_10_10_mdd_1_26_provenance(closure_results):
    mdd = closure_results["metrics"]["mdd_1_26"]
    assert mdd["status"] == "RECONCILED"
    assert mdd["exact_value"] == 1.26
    assert mdd["metric_name"] == "MEAN INDIVIDUAL-FUND FORWARD MAXIMUM DRAWDOWN"
    assert mdd["strategy"] == "Strategy C"

def test_10_11_identical_outcome_aggregation(closure_results):
    comparability = closure_results["comparability"]
    assert comparability["common_return_definition"] == "Equal-weighted arithmetic mean of individual scheme 1Y forward gross NAV returns"
    assert comparability["all_strategies_sample_size"] == 571
    assert comparability["forward_period"] == "2024-02-01 to 2025-01-31"

def test_10_12_freeze_governance_separation(closure_results):
    freeze = closure_results["freeze_governance"]
    assert freeze["current_production_methodology"] == "CURRENT PRODUCTION METHODOLOGY: FROZEN"
    assert freeze["historical_pre_anchor_freeze"] == "HISTORICAL PRE-ANCHOR FREEZE: NOT PROVEN"
    assert freeze["experiment_classification"] == "RETROSPECTIVE POINT-IN-TIME BACKTESTING — PROSPECTIVE/PRE-REGISTERED STATUS NOT PROVEN"

def test_10_13_no_production_scoring_changes(closure_results):
    assert closure_results["production_impact"]["scoring_logic_changed"] is False
    assert closure_results["production_impact"]["weights_changed"] is False
    assert closure_results["production_impact"]["suitability_changed"] is False
    assert closure_results["production_impact"]["action_logic_changed"] is False
