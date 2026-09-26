"""
Unit tests for Phase F.11.3.5.4.1.1 — P3/P4 Statistical Reconciliation & Full Traceability Audit
"""

import pytest
import os
import json


@pytest.fixture(scope="module")
def audit_results():
    json_path = 'docs/phase_f11_3_5_4_1_1_results.json'
    if not os.path.exists(json_path):
        from scripts.run_f11_3_5_4_1_1_forensic_closure import run_forensic_audit
        return run_forensic_audit()
    with open(json_path, 'r') as f:
        return json.load(f)


def test_p3_population_reproducibility(audit_results):
    p3 = [p for p in audit_results["period_audits"] if p["period_id"] == "P3_2022"][0]
    assert p3["population_waterfall"]["final_eligible_N"] == 4515


def test_p4_population_reproducibility(audit_results):
    p4 = [p for p in audit_results["period_audits"] if p["period_id"] == "P4_2023"][0]
    assert p4["population_waterfall"]["final_eligible_N"] == 5166


def test_p3_correlation_reproducibility(audit_results):
    p3 = [p for p in audit_results["period_audits"] if p["period_id"] == "P3_2022"][0]
    assert p3["executable_reproducible_rho"] == 0.1877
    res = audit_results["discrepancy_resolutions"]["p3_reconciliation"]
    assert res["reproducible_calculated_rho"] == 0.1877


def test_p4_correlation_reproducibility(audit_results):
    p4 = [p for p in audit_results["period_audits"] if p["period_id"] == "P4_2023"][0]
    assert p4["executable_reproducible_rho"] == -0.5737
    res = audit_results["discrepancy_resolutions"]["p4_reconciliation"]
    assert res["reproducible_calculated_rho"] == -0.5737


def test_all_five_period_correlation_reproducibility(audit_results):
    audits = audit_results["period_audits"]
    assert len(audits) == 5
    rhos = [a["executable_reproducible_rho"] for a in audits]
    assert rhos == [0.4031, 0.2935, 0.1877, -0.5737, 0.5098]


def test_positive_association_in_4_of_5_periods(audit_results):
    audits = audit_results["period_audits"]
    pos_count = sum(1 for a in audits if a["executable_reproducible_rho"] > 0)
    assert pos_count == 4


def test_representative_traces_reconstruction(audit_results):
    traces = audit_results["representative_traces"]
    assert len(traces) >= 7
    for t in traces:
        # Verify FQ formula reconstruction: 0.5 * vol_comp + 0.5 * tr_comp
        reconstructed = 0.5 * t["volatility_component"] + 0.5 * t["trailing_return_component"]
        assert abs(reconstructed - t["reconstructed_fq_score"]) < 1e-4
        # Verify forward return reconstruction: (fwd_end - fwd_start) / fwd_start
        expected_fwd_ret = (t["forward_end_nav"] - t["forward_start_nav"]) / t["forward_start_nav"]
        assert abs(expected_fwd_ret - t["reconstructed_forward_1y_return"]) < 1e-4


def test_production_methodology_unchanged(audit_results):
    assert audit_results["production_methodology_changed"] is False
