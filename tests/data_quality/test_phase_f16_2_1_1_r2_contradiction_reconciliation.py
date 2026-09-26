import json
import pytest
from pathlib import Path

JSON_PATH = Path("docs/phase_f16_2_1_1_r2_contradiction_reconciliation.json")

def test_f16_2_1_1_json_exists():
    assert JSON_PATH.exists(), "R2 contradiction reconciliation JSON file must exist"

def test_f16_2_1_1_contradiction_resolution():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    assert data["authoritative_table"] == "TABLE B AUTHORITATIVE"
    assert "manual transcription errors" in data["contradiction_origin"]
    assert data["production_methodology_changed"] is False

def test_f16_2_1_1_authoritative_r2_values():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    auth_table = {item["anchor_year"]: item for item in data["authoritative_incremental_r2_by_period"]}
    
    # 2022
    assert auth_table[2022]["M1_R2"] == 0.0014
    assert auth_table[2022]["M2_R2"] == 0.0025
    assert auth_table[2022]["M3_R2"] == 0.0027
    assert auth_table[2022]["delta_R2"] == 0.0001
    assert auth_table[2022]["common_N"] == 3705
    
    # 2023
    assert auth_table[2023]["M1_R2"] == 0.0006
    assert auth_table[2023]["M2_R2"] == 0.0508
    assert auth_table[2023]["M3_R2"] == 0.1056
    assert auth_table[2023]["delta_R2"] == 0.0548
    assert auth_table[2023]["common_N"] == 4249

    # 2024
    assert auth_table[2024]["M1_R2"] == 0.2053
    assert auth_table[2024]["M2_R2"] == 0.2280
    assert auth_table[2024]["M3_R2"] == 0.3325
    assert auth_table[2024]["delta_R2"] == 0.1045
    assert auth_table[2024]["common_N"] == 4958

def test_f16_2_1_1_claim_status():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    assert "SUPPORTED" in data["claim_status"]
    assert "subject to component circularity" in data["claim_status"]
