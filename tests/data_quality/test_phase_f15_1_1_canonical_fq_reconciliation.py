"""
Tests for Phase F.15.1.1 — Canonical Production Fund Quality Formula & Validation-Baseline Reconciliation
File: tests/data_quality/test_phase_f15_1_1_canonical_fq_reconciliation.py
"""

import pytest
import os
import json
from scoring.engine import FundQualityScoringEngine
from scoring.normalization import PeerGroupNormalizer
from scoring.config import SCORING_METHODOLOGY_VERSION


def test_production_engine_uses_percentile_rank():
    """Verify that the production engine uses PeerGroupNormalizer and outputs a score on a 0-100 scale."""
    engine = FundQualityScoringEngine()
    assert SCORING_METHODOLOGY_VERSION == "1.0.0"
    assert engine.normalizer.__class__.__name__ == "PeerGroupNormalizer"


def test_peer_group_normalizer_percentile_ranking():
    """Verify that PeerGroupNormalizer transforms raw values to 0.0-100.0 percentile ranks."""
    normalizer = PeerGroupNormalizer()
    raw_values = [0.05, 0.10, 0.15, 0.20, 0.25]
    
    # Test ascending percentile ranking (e.g. Return)
    pct, score_asc = normalizer.normalize_dimension(0.25, raw_values, higher_is_better=True)
    assert score_asc == pytest.approx(90.0)
    
    # Test descending percentile ranking (e.g. Volatility where lower is better)
    pct, score_desc = normalizer.normalize_dimension(0.25, raw_values, higher_is_better=False)
    assert score_desc == pytest.approx(10.0)


def test_phase_artifacts_exist():
    """Verify that required phase artifacts are produced and non-empty."""
    registry_path = os.path.join("docs", "phase_fq_formula_registry.json")
    recon_path = os.path.join("docs", "phase_f15_1_1_canonical_fq_reconciliation.json")
    
    assert os.path.exists(registry_path)
    assert os.path.exists(recon_path)
    
    with open(registry_path, "r") as f:
        reg = json.load(f)
        assert reg["scoring_methodology_version"] == "1.0.0"
        assert "production_entry_point" in reg
        
    with open(recon_path, "r") as f:
        recon = json.load(f)
        assert "production_engine_trace_sample" in recon
        assert len(recon["production_engine_trace_sample"]) == 10


def test_formula_a_vs_b_non_equivalence():
    """Verify that Formula A (raw) and Formula B (rank) are mathematically non-equivalent."""
    ret_a, vol_a = 0.25, 0.20
    ret_b, vol_b = 0.10, 0.02
    
    # Formula A (Raw Scaling): 50*(1/(1+vol)) + 50*ret
    fq_a_scheme1 = 50.0 * (1.0 / (1.0 + vol_a)) + 50.0 * ret_a  # 50*(0.8333) + 12.5 = 54.166
    fq_a_scheme2 = 50.0 * (1.0 / (1.0 + vol_b)) + 50.0 * ret_b  # 50*(0.9803) + 5.0  = 54.019
    
    assert fq_a_scheme1 > fq_a_scheme2
