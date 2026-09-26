"""
Tests for Phase F.16.1 — Exact-Production OOS Result Forensic Reconciliation & Decision-Use Governance
File: tests/data_quality/test_phase_f16_1_exact_production_oos_forensic_reconciliation.py
"""

import pytest
import os
import json


def test_reconciliation_json_artifact_exists_and_valid():
    """Verify that phase_f16_1_exact_production_oos_forensic_reconciliation.json exists and contains exact figures."""
    json_path = os.path.join("docs", "phase_f16_1_exact_production_oos_forensic_reconciliation.json")
    assert os.path.exists(json_path)

    with open(json_path, "r") as f:
        data = json.load(f)
        assert data["population_waterfall_reconciliation"]["stage_1_anchor_nav_population"] == 5874
        assert data["population_waterfall_reconciliation"]["final_valid_scored_N"] == 4958
        assert data["population_waterfall_reconciliation"]["top_decile_k"] == 496
        assert len(data["phase_population_reconciliation_table"]) == 4
        
        # Verify strategy outputs
        strats = data["strategy_results_table"]
        strat_A = [s for s in strats if "Strategy A" in s["strategy"]][0]
        strat_B = [s for s in strats if "Strategy B" in s["strategy"]][0]
        strat_C = [s for s in strats if "Strategy C" in s["strategy"]][0]

        assert strat_A["mean_return"] == pytest.approx(0.1298, abs=0.0001)
        assert strat_A["mean_mdd"] == pytest.approx(0.1667, abs=0.0001)
        assert strat_B["mean_return"] == pytest.approx(0.0633, abs=0.0001)
        assert strat_B["mean_mdd"] == pytest.approx(0.0011, abs=0.0001)
        assert strat_C["mean_return"] == pytest.approx(0.1301, abs=0.0001)
        assert strat_C["mean_mdd"] == pytest.approx(0.1486, abs=0.0001)


def test_claim_matrix_and_governance_scoping():
    """Verify that claim matrix properly scopes decision readiness."""
    json_path = os.path.join("docs", "phase_f16_1_exact_production_oos_forensic_reconciliation.json")
    with open(json_path, "r") as f:
        data = json.load(f)
        claims = data["claim_matrix"]
        assert claims["FQ provides independent information"] == "NOT SUPPORTED (Component circularity present)"
        assert claims["FQ demonstrates causal risk protection"] == "NOT SUPPORTED (Observational correlation only)"
        assert claims["FQ demonstrates economic benefit"] == "NOT TESTABLE (Requires transaction cost & tax modeling)"
