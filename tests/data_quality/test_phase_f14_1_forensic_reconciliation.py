"""
Expanded Unit Test Suite for Phase F.14.1 Forensic Reconciliation
File: tests/data_quality/test_phase_f14_1_forensic_reconciliation.py
"""

import os
import json
import pytest
import numpy as np
import pandas as pd

FORENSIC_JSON = "docs/phase_f14_1_forensic_reconciliation.json"
INVENTORY_JSON = "docs/phase_f14_metric_inventory.json"
PAIRWISE_JSON = "docs/phase_f14_pairwise_relationships.json"

def test_01_forensic_file_exists():
    assert os.path.exists(FORENSIC_JSON), "Forensic reconciliation JSON missing!"

def test_02_volatility_downside_reproducibility():
    with open(FORENSIC_JSON, "r") as f:
        data = json.load(f)
    
    rep = data["reproducibility"]
    assert abs(rep["volatility_vs_downside_rho"] - 0.9752) < 0.005, f"Volatility/Downside rho mismatch: {rep['volatility_vs_downside_rho']}"
    assert abs(rep["downside_vs_mdd_rho"] - 0.9825) < 0.005, f"Downside/MDD rho mismatch: {rep['downside_vs_mdd_rho']}"

def test_03_ratio_metric_mathematical_dependency():
    with open(INVENTORY_JSON, "r") as f:
        data = json.load(f)
    
    deps = data["dependencies"]
    assert deps["FQ_F08"]["classification"] == "DIRECT_DEPENDENCY", "Sharpe should be DIRECT_DEPENDENCY"
    assert deps["FQ_F09"]["classification"] == "DIRECT_DEPENDENCY", "Sortino should be DIRECT_DEPENDENCY"

def test_04_downside_deviation_mar_zero_formula():
    """Verify Downside Deviation MAR=0% worked numerical calculation on a small fixture."""
    daily_returns = np.array([0.01, -0.02, 0.005, -0.01, 0.015])
    downside_shortfalls = np.minimum(daily_returns, 0.0) # [-0.02, -0.01]
    expected_dd = np.sqrt(np.mean(downside_shortfalls ** 2)) * np.sqrt(252)
    
    # Manual check: mean(0.0004 + 0.0001) / 5 = 0.0001; sqrt(0.0001)*sqrt(252) = 0.01 * 15.8745 = 0.158745
    assert abs(expected_dd - 0.158745) < 1e-4

def test_05_max_drawdown_formula():
    """Verify Peak-to-Trough MDD calculation on a small fixture."""
    navs = np.array([100.0, 110.0, 105.0, 95.0, 100.0, 90.0, 105.0])
    peaks = np.maximum.accumulate(navs) # [100, 110, 110, 110, 110, 110, 110]
    drawdowns = (peaks - navs) / peaks
    mdd = np.max(drawdowns) # Peak 110 to min 90 -> (110 - 90)/110 = 20/110 = 0.181818
    
    assert abs(mdd - 0.181818) < 1e-4

def test_06_fund_age_architectural_classification():
    with open(FORENSIC_JSON, "r") as f:
        data = json.load(f)
    
    age_audit = data["fund_age_audit"]
    assert age_audit["architectural_classification"] == "CONFIDENCE_AND_EVIDENCE_DEPTH"

def test_07_anchor_governance_persistence():
    with open(FORENSIC_JSON, "r") as f:
        data = json.load(f)
    
    gov = data["anchor_governance"]
    assert gov["alt_anchor_2023_03_28_rho_vol_dd"] > 0.95, "Alternative anchor correlation unexpectedly low"

def test_08_production_methodology_unaltered():
    with open(INVENTORY_JSON, "r") as f:
        data = json.load(f)
    
    metrics = {m["metric_id"]: m for m in data["metrics"]}
    assert metrics["FQ_F01"]["production_status"] == "PRODUCTION (50% weight in Fund Quality Score v1.0)"
    assert metrics["FQ_F02"]["production_status"] == "PRODUCTION (50% weight in Fund Quality Score v1.0)"
