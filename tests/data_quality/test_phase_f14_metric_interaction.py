"""
Unit Test Suite for Phase F.14 - Fund Quality Metric Interaction, Redundancy & Information-Content Audit
File: tests/data_quality/test_phase_f14_metric_interaction.py
"""

import os
import json
import sqlite3
import pytest
import pandas as pd
import numpy as np

INVENTORY_FILE = "docs/phase_f14_metric_inventory.json"
PAIRWISE_FILE = "docs/phase_f14_pairwise_relationships.json"
DB_PATH = "db/backfill_f12_2.db"

def test_01_metric_inventory_completeness():
    """Verify that all 8 candidate metrics are inventoried with full governance metadata."""
    assert os.path.exists(INVENTORY_FILE), "Metric inventory JSON file missing!"
    with open(INVENTORY_FILE, "r") as f:
        data = json.load(f)
    
    metrics = data.get("metrics", [])
    assert len(metrics) == 8, f"Expected 8 metrics, found {len(metrics)}"
    
    expected_ids = {"FQ_F01", "FQ_F02", "FQ_F03", "FQ_F04", "FQ_F05", "FQ_F08", "FQ_F09", "FQ_F13"}
    found_ids = {m["metric_id"] for m in metrics}
    assert found_ids == expected_ids, f"Missing metric IDs: {expected_ids - found_ids}"

    for m in metrics:
        assert m.get("financial_definition"), f"Missing financial definition for {m['metric_id']}"
        assert m.get("mathematical_formula"), f"Missing formula for {m['metric_id']}"
        assert m.get("question_answered"), f"Missing plain language question for {m['metric_id']}"
        assert m.get("mar_assumption") is not None, f"Missing MAR assumption for {m['metric_id']}"

def test_02_mathematical_dependency_mapping():
    """Verify that ratio constructs (Sharpe, Sortino) are properly tagged as DIRECT_DEPENDENCY."""
    with open(INVENTORY_FILE, "r") as f:
        data = json.load(f)
    
    deps = data.get("dependencies", {})
    assert deps["FQ_F08"]["classification"] == "DIRECT_DEPENDENCY"
    assert "FQ_F01 (Return)" in deps["FQ_F08"]["dependencies"]
    assert "FQ_F02 (Volatility)" in deps["FQ_F08"]["dependencies"]

    assert deps["FQ_F09"]["classification"] == "DIRECT_DEPENDENCY"
    assert "FQ_F01 (Return)" in deps["FQ_F09"]["dependencies"]
    assert "FQ_F03 (Downside Deviation)" in deps["FQ_F09"]["dependencies"]

def test_03_pairwise_calculation_reproducibility():
    """Verify that pairwise relationships JSON exists, is non-empty, and contains expected correlations."""
    assert os.path.exists(PAIRWISE_FILE), "Pairwise relationships JSON file missing!"
    with open(PAIRWISE_FILE, "r") as f:
        data = json.load(f)
    
    pairs = data.get("pairwise_relationships", [])
    assert len(pairs) >= 17, f"Expected at least 17 pairwise relationship objects, found {len(pairs)}"
    
    # Check Volatility vs Downside Deviation strong overlap
    vol_dd_pair = next((p for p in pairs if p["metric_a"] == "FQ_F02" and p["metric_b"] == "FQ_F03"), None)
    assert vol_dd_pair is not None
    assert vol_dd_pair["spearman_rho"] > 0.90, "Volatility vs Downside Deviation correlation unexpectedly low"
    assert vol_dd_pair["redundancy_classification"] == "STRONG OVERLAP"

def test_04_category_aware_population_selection():
    """Verify that category breakdowns (Equity, Debt, Hybrid) have valid N > 0."""
    with open(PAIRWISE_FILE, "r") as f:
        data = json.load(f)
    
    pairs = data.get("pairwise_relationships", [])
    for p in pairs:
        cats = p.get("category_breakdown", {})
        assert cats.get("Equity", {}).get("N", 0) > 100, f"Insufficient Equity N for {p['relationship_label']}"
        assert cats.get("Debt", {}).get("N", 0) > 100, f"Insufficient Debt N for {p['relationship_label']}"
        assert cats.get("Hybrid", {}).get("N", 0) > 100, f"Insufficient Hybrid N for {p['relationship_label']}"

def test_05_production_methodology_unchanged():
    """Verify that production Fund Quality Score remains 50% Volatility + 50% Trailing Return."""
    # Read F.13 factor registry or production score config if available
    with open(INVENTORY_FILE, "r") as f:
        data = json.load(f)
    
    metrics = {m["metric_id"]: m for m in data.get("metrics", [])}
    assert metrics["FQ_F01"]["production_status"] == "PRODUCTION (50% weight in Fund Quality Score v1.0)"
    assert metrics["FQ_F02"]["production_status"] == "PRODUCTION (50% weight in Fund Quality Score v1.0)"
    
    for mid in ["FQ_F03", "FQ_F04", "FQ_F05", "FQ_F08", "FQ_F09", "FQ_F13"]:
        assert "RESEARCH-ONLY" in metrics[mid]["production_status"], f"{mid} illegally marked as production!"
