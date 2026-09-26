"""
Unit Test Suite for Phase F.15.1 OOS Forensic Reconciliation
File: tests/data_quality/test_phase_f15_1_oos_forensic_reconciliation.py
"""

import os
import json
import pytest

RECON_JSON = "docs/phase_f15_1_oos_forensic_reconciliation.json"

def test_01_recon_file_exists():
    assert os.path.exists(RECON_JSON), "Forensic reconciliation JSON artifact missing!"

def test_02_population_waterfall_reconciliation():
    with open(RECON_JSON, "r") as f:
        data = json.load(f)
    
    pop = data["population_reconciliation"]
    assert pop["prior_f11_3_5_5_cohort_N"] == 5713
    assert pop["f15_cohort_N"] == 5126
    assert pop["common_cohort_N"] == 5118
    assert pop["f11_only_N"] == 595

def test_03_production_fq_return_discrepancy_explained():
    with open(RECON_JSON, "r") as f:
        data = json.load(f)
    
    table = {item["metric_population"]: item for item in data["discrepancy_reconciliation_table"]}
    assert table["Production FQ Mean Fwd Return"]["prior_f11_3_5_5_result"] == "11.85%"
    assert table["Production FQ Mean Fwd Return"]["f15_result"] == "8.12%"
    assert "Scoring Formula Difference" in table["Production FQ Mean Fwd Return"]["exact_cause"]

def test_04_mdd_discrepancy_explained():
    with open(RECON_JSON, "r") as f:
        data = json.load(f)
    
    table = {item["metric_population"]: item for item in data["discrepancy_reconciliation_table"]}
    assert table["Production FQ Mean Fwd MDD"]["prior_f11_3_5_5_result"] == "16.80%"
    assert table["Production FQ Mean Fwd MDD"]["f15_result"] == "1.36%"
    assert "158 low-volatility debt funds" in table["Production FQ Mean Fwd MDD"]["exact_cause"]

def test_05_cluster_011_explained():
    with open(RECON_JSON, "r") as f:
        data = json.load(f)
    
    table = {item["metric_population"]: item for item in data["discrepancy_reconciliation_table"]}
    assert "0.11%" in table["0.11% MDD Cluster (Vol/Downside/MDD)"]["f15_result"]
    assert "liquid/overnight debt funds" in table["0.11% MDD Cluster (Vol/Downside/MDD)"]["exact_cause"]

def test_06_production_methodology_unaltered():
    with open("docs/phase_f14_metric_inventory.json", "r") as f:
        inv = json.load(f)
    
    metrics = {m["metric_id"]: m for m in inv["metrics"]}
    assert metrics["FQ_F01"]["production_status"] == "PRODUCTION (50% weight in Fund Quality Score v1.0)"
    assert metrics["FQ_F02"]["production_status"] == "PRODUCTION (50% weight in Fund Quality Score v1.0)"
