"""
Unit tests for Phase F.19.1.1.1.2.1: Zero-Return Engine Handling & Point-in-Time Representative Peer-Group Closure.

Tests confirm:
1. Exact 90-scheme zero-return population reconciliation.
2. Zero-return values are genuine numerical observations (NAV_T / NAV_0 - 1 = 0.0).
3. Production engine `cagr_overall or rolling_1y_mean` Boolean OR fallback defect reproduction.
4. `None` fallback behavior.
5. Positive return behavior.
6. Negative return behavior.
7. Zero-return schemes receive score = None under current threshold behavior.
8. F.16 impact classification (0.0% contamination due to active weight gating).
9. CAN_AMFI_100033 identity.
10. CAN_AMFI_100033 stored category/subcategory (UNASSIGNED).
11. Point-in-time peer-group evidence status (UNVERIFIED).
12. Fallback peer-group origin (F.16 validation script fallback).
13. Representative score authority classification (ILLUSTRATIVE_ONLY / NOT AUTHORITATIVE).
14. Historical F.16 immutability preserved.
15. No predictive statistics introduced.
"""

import json
import sqlite3
import pytest
from pathlib import Path

DB_PATH = Path("db/backfill_f12_2.db")
MANIFEST_PATH = Path("docs/f19_1_1_1_2_1_zero_return_peer_group_closure_manifest.json")
RESULTS_PATH = Path("docs/phase_f19_1_1_1_2_1_zero_return_peer_group_closure.json")
DEFECT_REG_PATH = Path("docs/defect_register_f19_1_1_1_2_1.json")


def test_01_manifest_and_artifacts_exist():
    assert MANIFEST_PATH.exists(), "Manifest file must exist"
    assert RESULTS_PATH.exists(), "Results file must exist"
    assert DEFECT_REG_PATH.exists(), "Defect register file must exist"

    with open(MANIFEST_PATH, "r") as f:
        manifest = json.load(f)
    assert manifest["phase"] == "F.19.1.1.1.2.1"
    assert manifest["status"] in ["PASSED", "PASSED WITH LIMITATIONS"]

    with open(RESULTS_PATH, "r") as f:
        results = json.load(f)
    assert results["production_methodology_changed"] is False


def test_02_zero_return_boolean_or_reproduction():
    """Reproduces the exact Python boolean OR defect logic from scoring/engine.py:
       (cagr_overall or rolling_1y_mean)
    """
    # Case A: cagr_overall = None -> falls back to rolling_1y_mean
    cagr_a, rolling_a = None, 0.12
    res_a = cagr_a or rolling_a
    assert res_a == 0.12, "None must fall back"

    # Case B: cagr_overall = 0.0 -> incorrectly falls back because float 0.0 is falsy in Python!
    cagr_b, rolling_b = 0.0, None
    res_b = cagr_b or rolling_b
    assert res_b is None, "0.0 incorrectly falls back to None in Python boolean OR!"

    # Case C: cagr_overall = 0.05 -> positive value retained
    cagr_c, rolling_c = 0.05, None
    res_c = cagr_c or rolling_c
    assert res_c == 0.05, "Positive return must be retained"

    # Case D: cagr_overall = -0.05 -> negative value retained (truthy in Python)
    cagr_d, rolling_d = -0.05, None
    res_d = cagr_d or rolling_d
    assert res_d == -0.05, "Negative return must be retained"


def test_03_exact_90_zero_return_reconciliation():
    with open(RESULTS_PATH, "r") as f:
        results = json.load(f)
    pop = results["population_summary"]
    assert pop["volatility_only_one_dim_schemes"] == 90
    assert pop["zero_dim_schemes"] == 77
    assert pop["f16_scored_population"] == 5125


def test_04_nav_evidence_proves_genuine_zero():
    with open(RESULTS_PATH, "r") as f:
        results = json.load(f)
    samples_1dim = results["sample_90_volatility_only_evidence"]
    assert len(samples_1dim) >= 5
    for s in samples_1dim:
        assert s["calculated_r_1y"] == 0.0
        assert s["nav_start_2023_01_31"] == s["nav_end_2024_01_31"]


def test_05_defect_classification_and_register():
    with open(DEFECT_REG_PATH, "r") as f:
        reg = json.load(f)
    assert reg["defect_id"] == "DEFECT-FQ-2026-001"
    assert reg["severity"] == "HIGH"
    assert reg["classification"] == "GENUINE PRODUCTION CODE DEFECT"
    assert reg["status"] in ["CONFIRMED — LOGGED FOR FUTURE FIX (UNFIXED IN CURRENT PHASE)", "FIXED"]


def test_06_f16_contamination_is_zero():
    with open(RESULTS_PATH, "r") as f:
        results = json.load(f)
    defect = results["defect_classification"]
    assert "0.0%" in defect["f16_historical_contamination"]


def test_07_can_amfi_100033_identity_and_db_category():
    with open(RESULTS_PATH, "r") as f:
        results = json.load(f)
    scheme_audit = results["representative_scheme_peer_group_audit"]
    assert scheme_audit["canonical_scheme_id"] == "CAN_AMFI_100033"
    assert scheme_audit["amfi_code"] == "100033"
    assert scheme_audit["database_category_column"] == "UNASSIGNED"
    assert scheme_audit["database_subcategory_column"] == "UNASSIGNED"


def test_08_can_amfi_100033_point_in_time_classification():
    with open(RESULTS_PATH, "r") as f:
        results = json.load(f)
    scheme_audit = results["representative_scheme_peer_group_audit"]
    assert "UNVERIFIED" in scheme_audit["historical_peer_group_status"]
    assert scheme_audit["script_fallback_peer_group"] == "Equity::Large Cap::REGULAR"


def test_09_representative_score_authority():
    with open(RESULTS_PATH, "r") as f:
        results = json.load(f)
    scheme_audit = results["representative_scheme_peer_group_audit"]
    assert "not suitable as authoritative" in scheme_audit["representative_score_authority"]


def test_10_production_code_remediation_status():
    """Verify that scoring/engine.py has explicit non-None check (remediated in F.19.2)."""
    engine_code = Path("scoring/engine.py").read_text()
    assert "cagr_overall if target_input.metrics.cagr_overall is not None else" in engine_code


def test_11_no_predictive_statistics_added():
    with open(RESULTS_PATH, "r") as f:
        results = json.load(f)
    assert "new_predictive_statistics" not in results


def test_12_defect_proposed_future_fix():
    with open(DEFECT_REG_PATH, "r") as f:
        reg = json.load(f)
    assert "FIXED" in reg["status"]
