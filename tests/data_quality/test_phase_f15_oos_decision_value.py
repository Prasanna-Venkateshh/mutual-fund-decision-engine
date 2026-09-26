"""
Unit Test Suite for Phase F.15 Out-Of-Sample Decision-Value Validation
File: tests/data_quality/test_phase_f15_oos_decision_value.py
"""

import os
import json
import pytest

MANIFEST_FILE = "docs/phase_f15_oos_decision_value_manifest.json"
RESULTS_FILE = "docs/phase_f15_oos_decision_value_results.json"

def test_01_manifest_immutability_and_hash():
    assert os.path.exists(MANIFEST_FILE), "Manifest JSON file missing!"
    with open(MANIFEST_FILE, "r") as f:
        manifest = json.load(f)
    
    assert manifest.get("anchor_date") == "2024-01-31", "Anchor date altered!"
    assert manifest.get("manifest_hash") is not None, "Manifest hash missing!"

def test_02_population_waterfall_reconciliation():
    assert os.path.exists(RESULTS_FILE), "Results JSON file missing!"
    with open(RESULTS_FILE, "r") as f:
        res = json.load(f)
    
    wf = res["population_waterfall"]
    assert wf["total_db_schemes"] == 17507
    assert wf["active_at_anchor"] == 16808
    assert wf["final_common_cohort_N"] == 5126

def test_03_same_sample_strategy_evaluation():
    with open(RESULTS_FILE, "r") as f:
        res = json.load(f)
    
    table = res["strategy_results_table"]
    assert len(table) == 6, f"Expected 6 strategies, found {len(table)}"
    
    for s in table:
        assert s["N_selected"] == 513, f"Strategy {s['strategy_id']} did not evaluate on top decile k=513"
        assert s["mean_forward_return"] is not None
        assert s["mean_forward_mdd"] is not None

def test_04_production_promotion_not_authorized():
    with open(RESULTS_FILE, "r") as f:
        res = json.load(f)
    
    assert res["production_promotion"] == "NOT AUTHORIZED BY F.15", "Production promotion illegally granted!"

def test_05_production_methodology_unaltered():
    with open("docs/phase_f14_metric_inventory.json", "r") as f:
        inv = json.load(f)
    
    metrics = {m["metric_id"]: m for m in inv["metrics"]}
    assert metrics["FQ_F01"]["production_status"] == "PRODUCTION (50% weight in Fund Quality Score v1.0)"
    assert metrics["FQ_F02"]["production_status"] == "PRODUCTION (50% weight in Fund Quality Score v1.0)"
