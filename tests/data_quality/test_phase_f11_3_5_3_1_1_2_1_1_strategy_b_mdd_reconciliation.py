import json
import pytest
from pathlib import Path

RESULTS_JSON_PATH = Path("docs/phase_f11_3_5_3_1_1_2_1_1_results.json")

@pytest.fixture(scope="module")
def closure_results():
    assert RESULTS_JSON_PATH.exists(), f"Results JSON missing at {RESULTS_JSON_PATH}"
    with open(RESULTS_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def test_16_1_governed_strategy_b_definition(closure_results):
    assert closure_results["governed_strategy_b_definition"] == "LOWEST 10% HISTORICAL VOLATILITY"
    assert "vol_sorted_idx = np.argsort(hist_vol)" in closure_results["governance_provenance"]

def test_16_2_strategy_b_4_34_exact_reproduction(closure_results):
    st_b_434 = closure_results["metrics_reconciliation"]["strategy_b_4_34"]
    assert st_b_434["exact_value"] == 4.34
    assert st_b_434["reproduced_value"] == 4.34
    assert st_b_434["status"] == "4.34% = RECONCILED GOVERNED STRATEGY B RESULT"

def test_16_3_strategy_b_6_82_exact_provenance(closure_results):
    st_b_682 = closure_results["metrics_reconciliation"]["strategy_b_6_82"]
    assert st_b_682["exact_value"] == 6.82
    assert st_b_682["status"] == "6.82% = HISTORICAL NARRATIVE VALUE — CALCULATION ORIGIN NOT REPRODUCIBLE"

def test_16_4_strategy_b_6_87_exact_provenance(closure_results):
    st_b_687 = closure_results["metrics_reconciliation"]["strategy_b_6_87"]
    assert st_b_687["exact_value"] == 6.87
    assert st_b_687["reproduced_value"] == 6.87
    assert st_b_687["status"] == "RECONCILED AS SECONDARY HISTORICAL COMPARATOR (Comparator B-DOWN)"

def test_16_5_reconciliation_6_82_vs_6_87(closure_results):
    diff = closure_results["metrics_reconciliation"]["diff_6_82_vs_6_87"]
    assert diff["difference_percentage_points"] == 0.05
    assert diff["status"] == "6.82% VS 6.87% = RECONCILED"

def test_16_6_mdd_0_11_exact_reproduction(closure_results):
    mdd_011 = closure_results["metrics_reconciliation"]["mdd_0_11"]
    assert mdd_011["exact_value"] == 0.11
    assert mdd_011["reproduced_value"] == 0.11
    assert mdd_011["status"] == "0.11% = RECONCILED GOVERNED STRATEGY B MDD"

def test_16_7_mdd_0_45_exact_provenance(closure_results):
    mdd_045 = closure_results["metrics_reconciliation"]["mdd_0_45"]
    assert mdd_045["exact_value"] == 0.45
    assert mdd_045["reproduced_value"] == 0.45
    assert mdd_045["metric_name"] == "MEDIAN INDIVIDUAL-FUND FORWARD MAXIMUM DRAWDOWN"
    assert mdd_045["status"] == "RECONCILED AS SECONDARY COMPARATOR MEDIAN MDD"

def test_16_8_mdd_mean_median_definition(closure_results):
    mdd_comp = closure_results["mdd_comparability"]
    assert mdd_comp["strategy_a_mdd_mean"] == 16.83
    assert mdd_comp["strategy_b_vol_mdd_mean"] == 0.11
    assert mdd_comp["strategy_c_mdd_mean"] == 1.26
    assert mdd_comp["comparator_b_down_mdd_median"] == 0.45

def test_16_9_strategy_b_population_and_n(closure_results):
    pop = closure_results["population_reconciliation"]
    assert pop["total_eligible_scored_universe"] == 5713
    assert pop["selected_decile_n"] == 571
    assert pop["decile_fraction"] == 0.10

def test_16_10_strategy_abc_common_return_aggregation(closure_results):
    prim = closure_results["primary_authoritative_comparison"]
    assert prim["strategy_a_trailing_return"]["return"] == "12.23%"
    assert prim["strategy_b_governed_volatility"]["return"] == "4.34%"
    assert prim["strategy_c_fund_quality"]["return"] == "7.81%"

def test_16_11_future_injection_invariance(closure_results):
    f_inj = closure_results["future_injection_invariance"]
    assert f_inj["volatility_sort_invariant"] is True
    assert f_inj["downside_sort_invariant"] is True
    assert f_inj["result"] == "PASS"

def test_16_12_no_production_methodology_changes(closure_results):
    assert closure_results["current_production_methodology_changed"] is False
    assert closure_results["historical_pre_freeze_classification"] == "RETROSPECTIVE POINT-IN-TIME BACKTESTING — PROSPECTIVE/PRE-REGISTERED STATUS NOT PROVEN"
