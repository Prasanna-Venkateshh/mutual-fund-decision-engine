"""
Expanded Unit Test Suite for Phase F.14.1.1 Incremental Information & Provenance Forensic Closure
File: tests/data_quality/test_phase_f14_1_1_incremental_information_closure.py
"""

import os
import json
import pytest
import numpy as np

CLOSURE_JSON = "docs/phase_f14_1_1_incremental_information_closure.json"

def test_01_closure_artifact_exists():
    assert os.path.exists(CLOSURE_JSON), "Closure JSON artifact missing!"

def test_02_symmetry_claim_correction_governance():
    with open(CLOSURE_JSON, "r") as f:
        data = json.load(f)
    
    corr = data["symmetry_claim_correction"]
    assert "CORRECTED" in corr["corrected_finding"], "Symmetry claim was not properly corrected in governance finding."
    assert corr["avg_negative_days"] < 100, "Negative day count mismatch"

def test_03_reconciliation_of_rolling_consistency_inc_r2():
    with open(CLOSURE_JSON, "r") as f:
        data = json.load(f)
    
    inc = data["incremental_r2_reconciliation"]
    assert inc["same_sample_verified"] is True, "Same-sample requirement not verified!"
    assert abs(inc["rolling_consistency_reproduced_inc_r2"] - 0.071219) < 1e-4, f"Mismatch in reproduced inc R2: {inc['rolling_consistency_reproduced_inc_r2']}"

def test_04_same_sample_candidate_matrix_completeness():
    with open(CLOSURE_JSON, "r") as f:
        data = json.load(f)
    
    matrix = data["candidate_factor_matrix"]
    assert len(matrix) == 6, f"Expected 6 candidate entries in matrix, found {len(matrix)}"
    
    # Check that all candidates use the exact same N = 4839 sample
    n_samples = {item["N_same_sample"] for item in matrix}
    assert n_samples == {4839}, f"Candidates did not use identical sample size! Found: {n_samples}"

def test_05_ratio_construct_dependency_classification():
    with open(CLOSURE_JSON, "r") as f:
        data = json.load(f)
    
    matrix = {item["candidate_id"]: item for item in data["candidate_factor_matrix"]}
    assert matrix["FQ_F08"]["dependency_classification"] == "DIRECT_DEPENDENCY", "Sharpe must be DIRECT_DEPENDENCY"
    assert matrix["FQ_F09"]["dependency_classification"] == "DIRECT_DEPENDENCY", "Sortino must be DIRECT_DEPENDENCY"
    assert matrix["FQ_F05"]["dependency_classification"] == "NO_DIRECT_DEPENDENCY", "Fund Age must be NO_DIRECT_DEPENDENCY"

def test_06_fund_age_architectural_isolation():
    with open(CLOSURE_JSON, "r") as f:
        data = json.load(f)
    
    matrix = {item["candidate_id"]: item for item in data["candidate_factor_matrix"]}
    assert "Confidence/Governance" in matrix["FQ_F05"]["interpretation"]

def test_07_traceability_sample_completeness():
    with open(CLOSURE_JSON, "r") as f:
        data = json.load(f)
    
    sample = data["traceability_sample"]
    assert sample["canonical_scheme_id"].startswith("CAN_"), "Invalid canonical scheme ID in trace sample"
    assert sample["Forward_1Y_Return"] is not None

def test_08_production_immutability_verification():
    """Verify that production weights and scoring remain strictly unchanged."""
    with open("docs/phase_f14_metric_inventory.json", "r") as f:
        inv = json.load(f)
    
    metrics = {m["metric_id"]: m for m in inv["metrics"]}
    assert metrics["FQ_F01"]["production_status"] == "PRODUCTION (50% weight in Fund Quality Score v1.0)"
    assert metrics["FQ_F02"]["production_status"] == "PRODUCTION (50% weight in Fund Quality Score v1.0)"
