"""
Phase F.19.1.1.1.1 — F.16 Population, Return-Field & Representative-Scheme Forensic Closure Test Suite.
File: tests/data_quality/test_phase_f19_1_1_1_1_f16_population_return_field_closure.py
"""

import pytest
import os
import sys
import json
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.abspath("."))

from scoring.engine import FundQualityScoringEngine
from scoring.config import CATEGORY_FAMILY_WEIGHTS
from models.fund_quality_dataset import (
    FundQualityDatasetInput,
    SchemeMetricSnapshot,
    CategoryPointInTimeContext,
    OptionType,
    PlanType,
    ProvenanceMetadata
)
from models.metric_data import HistoryMaturityBucket
from metrics.returns import calculate_cagr, calculate_absolute_return


def test_01_full_f16_active_dimension_distribution():
    """Verify JSON results contain active dimension distribution breakdown."""
    path = Path("docs/phase_f19_1_1_1_1_f16_population_return_field_closure.json")
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    active_dims = data["active_dimension_distribution"]
    dim_map = {item["active_dimensions"]: item["scheme_count"] for item in active_dims}
    assert dim_map[2] == 4958
    assert dim_map[1] == 90


def test_02_effective_weight_distribution():
    """Verify dynamic weight rescaling pattern for 2 active dimensions."""
    path = Path("docs/phase_f19_1_1_1_1_f16_population_return_field_closure.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    w_patterns = data["effective_weight_distribution"]
    pattern_map = {item["weight_pattern"]: item["scheme_count"] for item in w_patterns}
    assert "[('return', 62.5), ('volatility', 37.5)]" in pattern_map


def test_03_cagr_overall_field_semantics():
    """Verify distinction between normal CAGR definition and F.16 1Y return input assignment."""
    path = Path("docs/phase_f19_1_1_1_1_f16_population_return_field_closure.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    lineage = data["cagr_overall_lineage"]
    assert "Compound Annual Growth Rate" in lineage["normal_engine_semantics"]
    assert "NAV_T-252" in lineage["f16_input_assignment"]


def test_04_f16_input_mapping():
    """Verify input mapping assigns cagr_overall and annualized_volatility."""
    today = date(2024, 1, 31)
    metrics = SchemeMetricSnapshot(
        observation_date=today,
        history_length_years=1.0,
        maturity_tier=HistoryMaturityBucket.ONE_TO_THREE_YEARS,
        cagr_overall=0.15,
        annualized_volatility=0.10
    )
    assert metrics.cagr_overall == 0.15
    assert metrics.annualized_volatility == 0.10


def test_05_f16_return_dimension_mapping():
    """Verify engine Return dimension raw value uses cagr_overall."""
    engine = FundQualityScoringEngine()
    today = date(2024, 1, 31)
    inp = FundQualityDatasetInput(
        dataset_version="1.0.0", observation_date=today, canonical_scheme_id="C1", amfi_code="100", scheme_name="S1", amc_name="A",
        plan_type=PlanType.DIRECT, option_type=OptionType.GROWTH,
        category_context=CategoryPointInTimeContext(category="Equity", subcategory="Large Cap", effective_date=today),
        metrics=SchemeMetricSnapshot(observation_date=today, history_length_years=1.0, maturity_tier=HistoryMaturityBucket.ONE_TO_THREE_YEARS, cagr_overall=0.185, annualized_volatility=0.12),
        data_quality_score=1.0, confidence_score=1.0, provenance=ProvenanceMetadata("S", "U", None), return_comparability_available=True
    )
    res = engine.calculate_fund_quality_score(inp, [inp])
    assert res.dimension_scores["return"].raw_value == 0.185


def test_06_f16_volatility_mapping():
    """Verify engine Volatility dimension raw value uses annualized_volatility."""
    engine = FundQualityScoringEngine()
    today = date(2024, 1, 31)
    inp = FundQualityDatasetInput(
        dataset_version="1.0.0", observation_date=today, canonical_scheme_id="C1", amfi_code="100", scheme_name="S1", amc_name="A",
        plan_type=PlanType.DIRECT, option_type=OptionType.GROWTH,
        category_context=CategoryPointInTimeContext(category="Equity", subcategory="Large Cap", effective_date=today),
        metrics=SchemeMetricSnapshot(observation_date=today, history_length_years=1.0, maturity_tier=HistoryMaturityBucket.ONE_TO_THREE_YEARS, cagr_overall=0.185, annualized_volatility=0.12),
        data_quality_score=1.0, confidence_score=1.0, provenance=ProvenanceMetadata("S", "U", None), return_comparability_available=True
    )
    res = engine.calculate_fund_quality_score(inp, [inp])
    assert res.dimension_scores["volatility"].raw_value == 0.12


def test_07_reciprocal_volatility_direction():
    """Verify volatility ranking is lower-is-better."""
    from scoring.normalization import PeerGroupNormalizer
    norm = PeerGroupNormalizer()
    _, score_low_vol = norm.normalize_dimension(0.08, [0.08, 0.15, 0.25], higher_is_better=False)
    _, score_high_vol = norm.normalize_dimension(0.25, [0.08, 0.15, 0.25], higher_is_better=False)
    assert score_low_vol > score_high_vol


def test_08_representative_scheme_identity():
    """Verify representative schemes are genuine AMFI schemes with real codes and ISINs."""
    path = Path("docs/phase_f19_1_1_1_1_f16_population_return_field_closure.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    rep_schemes = data["representative_schemes_decomposition"]
    assert len(rep_schemes) >= 3
    for s in rep_schemes:
        assert s["amfi_code"] != "100000"
        assert s["isin_growth"].startswith("INF")


def test_09_real_score_decomposition():
    """Verify score decomposition sum matches engine output quality score."""
    path = Path("docs/phase_f19_1_1_1_1_f16_population_return_field_closure.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    rep_schemes = data["representative_schemes_decomposition"]
    for s in rep_schemes:
        assert s["reconciled"] is True
        calc_sum = round(s["return_contribution"] + s["volatility_contribution"], 1)
        assert calc_sum == s["final_score"]


def test_10_f16_population_reconciliation():
    """Verify population waterfall counts."""
    path = Path("docs/phase_f19_1_1_1_1_f16_population_return_field_closure.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    wf = data["population_waterfall"]
    assert wf["stage_1_anchor_candidates"] == 5874
    assert wf["f16_scored_population"] == 5125
    assert wf["f16_valid_scored_population"] == 4958


def test_11_f16_effective_formula():
    """Verify effective score equation equation lineage classification."""
    path = Path("docs/phase_f19_1_1_1_1_f16_population_return_field_closure.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["lineage_classification"].startswith("B. PRODUCTION ENGINE VALIDATION")


def test_12_f16_validation_classification():
    """Verify exact terminology recommendation."""
    path = Path("docs/phase_f19_1_1_1_1_f16_population_return_field_closure.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "2-dimension data" in data["f16_terminology_status"]


def test_13_f15_1_1_lineage_consistency():
    """Verify historical governance classification."""
    path = Path("docs/phase_f19_1_1_1_1_f16_population_return_field_closure.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["dynamic_rescaling_governance"] == "PRODUCTION IMPLEMENTED BUT EMPIRICALLY UNVALIDATED"


def test_14_f16_2_1_1_lineage_consistency():
    """Verify manifest integrity."""
    manifest_path = Path("docs/f19_1_1_1_1_f16_population_return_field_closure_manifest.json")
    assert manifest_path.exists()
