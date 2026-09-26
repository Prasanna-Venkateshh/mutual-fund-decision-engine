import json
import pytest
from pathlib import Path

MANIFEST_PATH = Path("docs/f16_2_multi_period_validation_manifest.json")
RESULTS_PATH = Path("docs/phase_f16_2_multi_period_exact_production_oos.json")

def test_f16_2_manifest_and_results_exist():
    assert MANIFEST_PATH.exists(), "Manifest JSON file must exist"
    assert RESULTS_PATH.exists(), "Results JSON file must exist"

def test_f16_2_production_engine_integrity():
    with open(RESULTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    assert data["governed_production_model"]["scoring_engine"] == "FundQualityScoringEngine"
    assert data["governed_production_model"]["peer_key"] == "category::subcategory::plan_type"
    assert data["governed_production_model"]["normalization"] == "percentile_rank"
    assert data["production_methodology_changed"] is False

def test_f16_2_multi_period_reproducibility_and_consistency():
    with open(RESULTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    assert data["final_status"] == "PASSED WITH LIMITATIONS"
    assert data["evidence_consistency_classification"].startswith("MIXED")
    
    period_results = data.get("period_by_period_results") or data.get("period_results")
    assert len(period_results) == 3
    
    anchors = [p["anchor_date"] for p in period_results]
    assert anchors == ["2022-01-31", "2023-01-31", "2024-01-31"]

def test_f16_2_claim_matrix_integrity():
    with open(RESULTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    claim_matrix = data["claim_matrix"]
    assert claim_matrix["Exact production engine used"] == "SUPPORTED"
    assert claim_matrix["Exact production peer groups used"] == "SUPPORTED"
    assert claim_matrix["PIT integrity"] == "SUPPORTED"
    assert claim_matrix["Multi-period forward association"] == "SUPPORTED"
    assert claim_matrix["Consistent positive association"] == "NOT SUPPORTED"
    assert claim_matrix["FQ consistently exceeds trailing return"] == "NOT SUPPORTED"
    assert claim_matrix["FQ consistently has lower MDD"] == "SUPPORTED"
    assert claim_matrix["Quintile monotonicity persists"] == "NOT SUPPORTED"
    assert claim_matrix["Incremental model-fit contribution persists"] == "SUPPORTED"
    assert claim_matrix["Independent information established"] == "NOT SUPPORTED"
    assert claim_matrix["Economic benefit established"] == "NOT SUPPORTED"
    assert claim_matrix["Causal risk protection established"] == "NOT SUPPORTED"
    assert claim_matrix["Consequential decision readiness established"] == "NOT SUPPORTED"
