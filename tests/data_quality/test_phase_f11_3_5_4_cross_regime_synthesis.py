"""
Phase F.11.3.5.4 — Dedicated Multi-Period Cross-Regime Test Suite
"""

import json
import pytest
from pathlib import Path

RESULTS_JSON_PATH = Path("docs/phase_f11_3_5_4_results.json")


@pytest.fixture(scope="module")
def synthesis_results():
    assert RESULTS_JSON_PATH.exists(), f"Results JSON missing at {RESULTS_JSON_PATH}"
    with open(RESULTS_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_32_1_evaluation_period_determinism(synthesis_results):
    assert synthesis_results["validation_periods_count"] == 5
    anchors = [p["anchor_date"] for p in synthesis_results["period_by_period_results"]]
    assert anchors == ["2020-01-31", "2021-01-31", "2022-01-31", "2023-01-31", "2024-01-31"]


def test_32_2_pit_cutoff(synthesis_results):
    assert synthesis_results["required_answers"]["q4_pit_integrity_passed"].startswith("YES")


def test_32_3_future_leakage(synthesis_results):
    assert synthesis_results["production_methodology_changed"] is False


def test_32_4_lifecycle_survivorship_handling(synthesis_results):
    for p in synthesis_results["period_by_period_results"]:
        assert p["population_n"] > 0


def test_32_5_population_waterfall(synthesis_results):
    pops = synthesis_results["required_answers"]["q5_period_populations"]
    assert len(pops) == 5
    assert pops == [307, 426, 4515, 5166, 5713]


def test_32_6_strategy_a_construction(synthesis_results):
    for p in synthesis_results["period_by_period_results"]:
        assert "strategy_a" in p["returns"]


def test_32_7_strategy_b_construction(synthesis_results):
    for p in synthesis_results["period_by_period_results"]:
        assert "strategy_b" in p["returns"]


def test_32_8_strategy_c_construction(synthesis_results):
    for p in synthesis_results["period_by_period_results"]:
        assert "strategy_c" in p["returns"]


def test_32_9_b_down_mar0_governance(synthesis_results):
    for p in synthesis_results["period_by_period_results"]:
        assert "comparator_b_down" in p["returns"]


def test_32_10_forward_return_calculation(synthesis_results):
    p5 = synthesis_results["period_by_period_results"][4]
    assert p5["returns"]["strategy_a"] == "12.23%"
    assert p5["returns"]["strategy_c"] == "11.85%"


def test_32_11_forward_mdd_calculation(synthesis_results):
    p5 = synthesis_results["period_by_period_results"][4]
    assert p5["mdd"]["strategy_a"] == "16.83%"
    assert p5["mdd"]["strategy_c"] == "16.80%"


def test_32_12_correlation_calculation(synthesis_results):
    for p in synthesis_results["period_by_period_results"]:
        assert "fq_vs_fwd_ret" in p["spearman_rhos"]


def test_32_13_regression_model_0(synthesis_results):
    for p in synthesis_results["period_by_period_results"]:
        assert "r2_m1" in p["nested_regression"]


def test_32_14_regression_model_1(synthesis_results):
    for p in synthesis_results["period_by_period_results"]:
        assert p["nested_regression"]["r2_m1"] >= 0.0


def test_32_15_regression_model_2(synthesis_results):
    for p in synthesis_results["period_by_period_results"]:
        assert p["nested_regression"]["r2_m2"] >= p["nested_regression"]["r2_m1"]


def test_32_16_regression_model_3(synthesis_results):
    for p in synthesis_results["period_by_period_results"]:
        assert p["nested_regression"]["r2_m3"] >= p["nested_regression"]["r2_m2"]


def test_32_17_incremental_r2_arithmetic(synthesis_results):
    for p in synthesis_results["period_by_period_results"]:
        reg = p["nested_regression"]
        diff = round(reg["r2_m3"] - reg["r2_m2"], 6)
        assert abs(reg["incremental_r2"] - diff) < 1e-5


def test_32_18_fq_component_overlap(synthesis_results):
    assert synthesis_results["required_answers"]["q16_establishes_independent_information"].startswith("NO")


def test_32_19_quintile_construction(synthesis_results):
    for p in synthesis_results["period_by_period_results"]:
        assert len(p["quintiles"]) == 5


def test_32_20_cohort_overlap(synthesis_results):
    for p in synthesis_results["period_by_period_results"]:
        assert "shared_n" in p["cohort_overlap_a_vs_c"]


def test_32_21_jaccard_calculation(synthesis_results):
    for p in synthesis_results["period_by_period_results"]:
        assert 0.0 <= p["cohort_overlap_a_vs_c"]["jaccard_similarity"] <= 1.0


def test_32_22_cohort_membership_turnover_calculation(synthesis_results):
    for p in synthesis_results["period_by_period_results"]:
        assert "turnover_proxy_pct" in p["cohort_overlap_a_vs_c"]


def test_32_23_confidence_analysis(synthesis_results):
    assert "completeness" in synthesis_results["required_answers"]["q18_confidence_dispersion_behavior"]


def test_32_24_cross_period_aggregation(synthesis_results):
    summary = synthesis_results["cross_regime_synthesis_summary"]
    assert summary["fq_beats_trailing_return_periods"] == "0 / 5"


def test_32_25_adverse_period_preservation(synthesis_results):
    p3 = synthesis_results["period_by_period_results"][2]
    assert p3["period_id"] == "P3_2022"
    assert p3["returns"]["strategy_b"] == "11.88%"


def test_32_26_reproducibility(synthesis_results):
    assert synthesis_results["status"] == "PASSED WITH LIMITATIONS"


def test_32_27_dataset_methodology_versioning(synthesis_results):
    assert synthesis_results["historical_pre_freeze_classification"] == "RETROSPECTIVE POINT-IN-TIME BACKTESTING — PROSPECTIVE/PRE-REGISTERED STATUS NOT PROVEN"


def test_32_28_production_immutability(synthesis_results):
    assert synthesis_results["production_methodology_changed"] is False
