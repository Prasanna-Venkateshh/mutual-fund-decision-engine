"""
Unit tests for Phase F.13 — Fund Quality Factor Completeness, Data Readiness & Explainability Governance
"""

import pytest
import os
import json


@pytest.fixture(scope="module")
def factor_registry():
    json_path = 'docs/phase_f13_factor_registry.json'
    if not os.path.exists(json_path):
        from scripts.run_f13_factor_governance import run_factor_governance
        return run_factor_governance()
    with open(json_path, 'r') as f:
        return json.load(f)


@pytest.fixture(scope="module")
def readiness_matrix():
    matrix_path = 'docs/phase_f13_data_readiness_matrix.json'
    assert os.path.exists(matrix_path)
    with open(matrix_path, 'r') as f:
        return json.load(f)


def test_factor_registry_completeness(factor_registry):
    factors = factor_registry["canonical_factor_registry"]
    assert len(factors) == 14
    expected_ids = [f"FQ_F{i:02d}" for i in range(1, 15)]
    actual_ids = [f["factor_id"] for f in factors]
    assert actual_ids == expected_ids


def test_factor_layer_classification(factor_registry):
    factors = factor_registry["canonical_factor_registry"]
    layer_map = {f["factor_id"]: f["intended_layer"] for f in factors}
    
    # Intrinsic Fund Quality
    assert layer_map["FQ_F01"] == "FUND QUALITY"
    assert layer_map["FQ_F02"] == "FUND QUALITY"
    
    # Confidence / Evidence Depth
    assert layer_map["FQ_F05"] == "CONFIDENCE"  # Fund Age
    assert layer_map["FQ_F06"] == "CONFIDENCE"  # Fund Manager
    
    # Economic Benefit
    assert layer_map["FQ_F07"] == "ECONOMIC BENEFIT"  # TER
    
    # Suitability
    assert layer_map["FQ_F11"] == "SUITABILITY"  # Tracking Error
    assert layer_map["FQ_F14"] == "SUITABILITY"  # SEBI Riskometer


def test_pit_classification(factor_registry):
    factors = factor_registry["canonical_factor_registry"]
    pit_map = {f["factor_id"]: f["pit_requirement"] for f in factors}
    assert pit_map["FQ_F01"] == "PIT_VERIFIED"
    assert pit_map["FQ_F02"] == "PIT_VERIFIED"
    assert pit_map["FQ_F06"] == "PIT_NOT_AVAILABLE"  # Manager Tenure
    assert pit_map["FQ_F10"] == "PIT_NOT_AVAILABLE"  # Benchmark Alpha


def test_no_new_mar_assumptions(factor_registry):
    factors = factor_registry["canonical_factor_registry"]
    for f in factors:
        if "downside" in f["factor_name"].lower() or "sortino" in f["factor_name"].lower():
            assert "MAR = 0%" in f["definition"] or "MAR0" in f["factor_id"] or "MAR" in f["calculation_method"]


def test_blocked_by_data_factors(factor_registry):
    summary = factor_registry["summary"]
    assert summary["blocked_by_data_factors_count"] == 4
    blocked_ids = [f["factor_id"] for f in factor_registry["canonical_factor_registry"] if f["current_data_status"] == "BLOCKED_BY_DATA"]
    assert "FQ_F06" in blocked_ids  # Fund Manager
    assert "FQ_F10" in blocked_ids  # Benchmark Excess Return
    assert "FQ_F11" in blocked_ids  # Tracking Error
    assert "FQ_F12" in blocked_ids  # Information Ratio


def test_explainability_requirements_completeness(factor_registry):
    factors = factor_registry["canonical_factor_registry"]
    for f in factors:
        assert "explainability_requirements" in f
        assert len(f["explainability_requirements"]) > 5


def test_readiness_matrix_consistency(readiness_matrix, factor_registry):
    reg_factors = factor_registry["canonical_factor_registry"]
    mat_factors = readiness_matrix["factors"]
    assert len(mat_factors) == len(reg_factors)
    for m, r in zip(mat_factors, reg_factors):
        assert m["factor_id"] == r["factor_id"]
        assert m["intended_layer"] == r["intended_layer"]


def test_no_production_scoring_changes(factor_registry):
    assert factor_registry["production_methodology_changed"] is False
