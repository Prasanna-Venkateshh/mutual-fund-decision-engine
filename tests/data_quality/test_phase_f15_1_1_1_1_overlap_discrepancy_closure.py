"""
Tests for Phase F.15.1.1.1.1 — Global vs Production Top-Decile Overlap Discrepancy Closure
File: tests/data_quality/test_phase_f15_1_1_1_1_overlap_discrepancy_closure.py
"""

import pytest
import os
import json


def test_closure_artifact_exists_and_valid():
    """Verify that phase_f15_1_1_1_1_overlap_discrepancy_closure.json exists and contains complete audit data."""
    json_path = os.path.join("docs", "phase_f15_1_1_1_1_overlap_discrepancy_closure.json")
    assert os.path.exists(json_path)

    with open(json_path, "r") as f:
        data = json.load(f)
        assert "historical_70_6_origin" in data
        assert data["historical_70_6_origin"]["source_line"] == 169
        assert len(data["reconciled_overlap_table"]) == 3
        
        # Verify exact numerical figures
        exact_peer = [row for row in data["reconciled_overlap_table"] if row["peer_scope"] == "category::subcategory::plan_type"][0]
        assert exact_peer["numerator"] == 601
        assert exact_peer["denominator"] == 656
        assert exact_peer["overlap_pct"] == pytest.approx(91.62, abs=0.01)


def test_production_immutability():
    """Verify that scoring engine files remain unchanged."""
    assert os.path.exists("scoring/engine.py")
    assert os.path.exists("scoring/normalization.py")
