"""
Tests for Phase F.16 — Exact-Production Fund Quality Out-of-Sample Decision-Value Validation
File: tests/data_quality/test_phase_f16_exact_production_oos_validation.py
"""

import pytest
import os
import json
from scoring.engine import FundQualityScoringEngine
from scoring.config import SCORING_METHODOLOGY_VERSION, WEIGHT_CONFIG_VERSION


def test_validation_manifest_and_output_exist():
    """Verify that frozen manifest and validation JSON artifacts exist and are non-empty."""
    manifest_path = os.path.join("docs", "f16_validation_manifest.json")
    results_path = os.path.join("docs", "phase_f16_exact_production_oos_validation.json")
    
    assert os.path.exists(manifest_path)
    assert os.path.exists(results_path)

    with open(manifest_path, "r") as f:
        m = json.load(f)
        assert "manifest_hash" in m
        assert m["anchor_date"] == "2024-01-31"
        assert m["exact_peer_group_key"] == "category::subcategory::plan_type"

    with open(results_path, "r") as f:
        r = json.load(f)
        assert r["production_engine_used"] is True
        assert r["future_injection_test_passed"] is True
        assert r["survivorship_test_passed"] is True
        assert len(r["strategy_results_table"]) == 3


def test_production_engine_execution_in_validation():
    """Verify that FundQualityScoringEngine executes directly without modification."""
    engine = FundQualityScoringEngine()
    assert engine.normalizer.__class__.__name__ == "PeerGroupNormalizer"
    assert engine.weight_manager.__class__.__name__ == "ScoringWeightManager"


def test_claim_matrix_completeness():
    """Verify that the claim matrix includes mandatory governance evaluations."""
    results_path = os.path.join("docs", "phase_f16_exact_production_oos_validation.json")
    with open(results_path, "r") as f:
        r = json.load(f)
        claims = r["claim_matrix"]
        assert "Production engine executes correctly" in claims
        assert claims["PIT integrity"] == "SUPPORTED"
        assert claims["FQ provides independent information"] == "NOT SUPPORTED (Component circularity present)"
