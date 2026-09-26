import json
import pytest
from pathlib import Path

MANIFEST_PATH = Path("docs/f16_3_oos_data_availability_manifest.json")
RESULTS_PATH = Path("docs/phase_f16_3_oos_data_availability_audit.json")

def test_f16_3_manifest_and_results_exist():
    assert MANIFEST_PATH.exists(), "Manifest JSON file must exist"
    assert RESULTS_PATH.exists(), "Results JSON file must exist"

def test_f16_3_database_nav_bounds():
    with open(RESULTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    db_metrics = data["database_metrics"]
    assert db_metrics["minimum_nav_date"] == "2014-02-28"
    assert db_metrics["maximum_nav_date"] == "2025-01-31"
    assert db_metrics["total_nav_observations"] == 6337995
    assert db_metrics["unique_schemes_count"] == 17507

def test_f16_3_next_period_data_sufficiency():
    with open(RESULTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    next_eval = data["next_possible_anchor_evaluation"]
    assert next_eval["next_possible_anchor"] == "2025-01-31"
    assert next_eval["next_full_forward_outcome_period"] == "2025-02-01 to 2026-01-31"
    assert next_eval["forward_observations_count_after_2025_01_31"] == 0
    assert next_eval["data_sufficient_for_next_period"] is False
    assert data["outcome_analysis_performed_in_this_phase"] is False

def test_f16_3_production_engine_integrity():
    with open(RESULTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    assert data["governed_production_model"]["scoring_engine"] == "FundQualityScoringEngine"
    assert data["governed_production_model"]["peer_key"] == "category::subcategory::plan_type"
    assert data["production_methodology_changed"] is False
