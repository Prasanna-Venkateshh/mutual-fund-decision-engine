import json
import pytest
from pathlib import Path

JSON_PATH = Path("docs/phase_f16_2_1_multi_period_lineage_reconciliation.json")

def test_f16_2_1_json_exists():
    assert JSON_PATH.exists(), "Lineage reconciliation JSON file must exist"

def test_f16_2_1_oos_period_classification():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    oos = data["oos_summary"]
    assert oos["genuinely_unseen_oos"] == ["2024-01-31 to 2025-01-31"]
    assert oos["reused_replication"] == ["2022-01-31 to 2023-01-31", "2023-01-31 to 2024-01-31"]
    assert oos["unavailable"] == ["2021-01-31 to 2022-01-31"]
    assert data["summary_statistics"]["genuinely_unseen_oos_periods"] == 1

def test_f16_2_1_production_engine_integrity():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    assert data["governed_production_model"]["scoring_engine"] == "FundQualityScoringEngine"
    assert data["governed_production_model"]["peer_key"] == "category::subcategory::plan_type"
    assert data["production_methodology_changed"] is False

def test_f16_2_1_claim_matrix_governance():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    cm = data["claim_matrix"]
    assert cm["Multi-period forward association"] == "SUPPORTED"
    assert cm["Consistent positive association"] == "NOT SUPPORTED"
    assert cm["FQ consistently exceeds trailing return"] == "NOT SUPPORTED"
    assert cm["FQ consistently has lower MDD"] == "SUPPORTED DESCRIPTIVELY"
    assert cm["Quintile monotonicity persists"] == "NOT SUPPORTED"
    assert cm["Incremental model-fit contribution persists"] == "SUPPORTED"
    assert cm["Independent information established"] == "NOT SUPPORTED"
    assert cm["Economic benefit established"] == "NOT SUPPORTED"
    assert cm["Causal risk protection established"] == "NOT SUPPORTED"
    assert cm["Consequential decision readiness"] == "NOT SUPPORTED"
