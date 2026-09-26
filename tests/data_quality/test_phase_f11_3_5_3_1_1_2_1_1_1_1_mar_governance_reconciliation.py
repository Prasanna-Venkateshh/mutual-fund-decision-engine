import json
import pytest
from pathlib import Path

RESULTS_JSON_PATH = Path("docs/phase_f11_3_5_3_1_1_2_1_1_1_1_results.json")

@pytest.fixture(scope="module")
def closure_results():
    assert RESULTS_JSON_PATH.exists(), f"Results JSON missing at {RESULTS_JSON_PATH}"
    with open(RESULTS_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def test_14_1_production_downside_mar_unchanged(closure_results):
    prod = closure_results["governed_fund_metric_methodology"]
    assert prod["source_file"] == "metrics/risk.py"
    assert prod["governed_mar_daily"] == 0.0
    assert prod["governed_mar_annualized"] == "0.0%"
    assert closure_results["current_production_methodology_changed"] is False

def test_14_2_exact_production_mar_identification(closure_results):
    prod = closure_results["governed_fund_metric_methodology"]
    assert prod["status"] == "FROZEN PRODUCTION METHODOLOGY"

def test_14_3_origin_of_6_percent_mar(closure_results):
    mar6 = closure_results["origin_of_6_percent_mar"]
    assert mar6["classification"] == "UNSUPPORTED NEW ASSUMPTION"
    assert mar6["is_governed"] is False

def test_14_4_unsupported_mar_detection(closure_results):
    status = closure_results["comparator_b_down_governance_status"]
    assert status["is_independently_governed"] is False
    assert status["governance_classification"] == "RESEARCH-ONLY SECONDARY COMPARATOR"

def test_14_5_governed_mar0_reconstruction(closure_results):
    mar0 = closure_results["governed_mar0_reconstruction"]
    assert mar0["population_n"] == 5713
    assert mar0["selected_n"] == 571
    assert "36e600b506249b5" in mar0["cohort_sha256_hash"]

def test_14_6_cohort_comparison_0_vs_6_percent(closure_results):
    comp = closure_results["cohort_comparison_0_vs_6_percent"]
    assert comp["intersection_n"] == 422
    assert comp["mar0_only_n"] == 149
    assert comp["mar6_only_n"] == 149
    assert comp["jaccard_similarity"] == 0.5861

def test_14_7_return_6_87_provenance(closure_results):
    ret = closure_results["specific_historical_artifact_provenance"]["return_6_87"]
    assert ret["exact_value"] == 6.87
    assert ret["raw_mean_mar0"] == 0.050292
    assert ret["raw_mean_mar6"] == 0.068705

def test_14_8_mdd_0_13_provenance(closure_results):
    mdd = closure_results["specific_historical_artifact_provenance"]["mdd_0_13"]
    assert mdd["exact_value"] == 0.13
    assert mdd["status"] == "RECONCILED MEAN MDD"

def test_14_9_mdd_0_00_provenance(closure_results):
    mdd = closure_results["specific_historical_artifact_provenance"]["mdd_0_00"]
    assert mdd["exact_value"] == 0.0
    assert mdd["status"] == "RECONCILED MEDIAN MDD"

def test_14_10_unresolved_narrative_classifications(closure_results):
    artifacts = closure_results["specific_historical_artifact_provenance"]
    assert artifacts["return_6_82"]["status"] == "UNRECONCILED HISTORICAL NARRATIVE VALUE — CALCULATION ORIGIN NOT REPRODUCIBLE"
    assert artifacts["mdd_0_45"]["status"] == "UNRECONCILED HISTORICAL VALUE — CALCULATION ORIGIN NOT REPRODUCIBLE FROM CURRENT DATASET"

def test_14_11_future_injection_invariance(closure_results):
    f_inj = closure_results["future_injection_invariance"]
    assert f_inj["mar0_sort_invariant"] is True
    assert f_inj["mar6_sort_invariant"] is True
    assert f_inj["result"] == "PASS"

def test_14_12_no_production_methodology_modification(closure_results):
    assert closure_results["current_production_methodology_changed"] is False
    assert closure_results["historical_pre_freeze_classification"] == "RETROSPECTIVE POINT-IN-TIME BACKTESTING — PROSPECTIVE/PRE-REGISTERED STATUS NOT PROVEN"
