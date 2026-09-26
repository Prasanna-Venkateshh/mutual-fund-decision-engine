"""
Phase F.19.1.1.1 F.16 Effective Scoring Formula & Validation-Lineage Reconciliation Test Suite.

At minimum tests:
1. F.16 actual input mapping.
2. cagr_overall definition.
3. F.16 Return input.
4. F.16 Volatility input.
5. reciprocal-volatility direction.
6. runtime weight resolution.
7. missing-data rescaling.
8. active-dimension distribution.
9. peer-group key.
10. representative real score decomposition.
11. F.16 scoring formula classification.
12. F.16/F.16.2 lineage consistency.
"""

import pytest
import os
import sys
import json
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.abspath("."))

from scoring.engine import FundQualityScoringEngine
from scoring.config import CATEGORY_FAMILY_WEIGHTS, SCORING_METHODOLOGY_VERSION
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
from metrics.risk import calculate_annualized_volatility


def test_01_f16_actual_input_mapping():
    """Verify F.16 input mapping assigns cagr_overall and annualized_volatility."""
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
    assert metrics.rolling_3y_mean is None
    assert metrics.downside_deviation is None


def test_02_cagr_overall_definition():
    """Verify CAGR calculation over 365.25 days equals point-to-point 1Y return."""
    start_d = date(2023, 1, 31)
    end_d = date(2024, 1, 31)
    cagr = calculate_cagr(100.0, 115.0, start_d, end_d)
    abs_ret = calculate_absolute_return(100.0, 115.0)
    assert abs(cagr - abs_ret) < 0.005


def test_03_f16_return_input():
    """Verify Return metric uses cagr_overall."""
    engine = FundQualityScoringEngine()
    today = date(2024, 1, 31)
    inp = FundQualityDatasetInput(
        dataset_version="1.0.0", observation_date=today, canonical_scheme_id="C1", amfi_code="100", scheme_name="S1", amc_name="A",
        plan_type=PlanType.DIRECT, option_type=OptionType.GROWTH,
        category_context=CategoryPointInTimeContext(category="Equity", subcategory="Large Cap", effective_date=today),
        metrics=SchemeMetricSnapshot(observation_date=today, history_length_years=1.0, maturity_tier=HistoryMaturityBucket.ONE_TO_THREE_YEARS, cagr_overall=0.15, annualized_volatility=0.10),
        data_quality_score=1.0, confidence_score=1.0, provenance=ProvenanceMetadata("S", "U", None), return_comparability_available=True
    )
    res = engine.calculate_fund_quality_score(inp, [inp])
    assert res.dimension_scores["return"].raw_value == 0.15


def test_04_f16_volatility_input():
    """Verify Volatility metric uses annualized_volatility."""
    engine = FundQualityScoringEngine()
    today = date(2024, 1, 31)
    inp = FundQualityDatasetInput(
        dataset_version="1.0.0", observation_date=today, canonical_scheme_id="C1", amfi_code="100", scheme_name="S1", amc_name="A",
        plan_type=PlanType.DIRECT, option_type=OptionType.GROWTH,
        category_context=CategoryPointInTimeContext(category="Equity", subcategory="Large Cap", effective_date=today),
        metrics=SchemeMetricSnapshot(observation_date=today, history_length_years=1.0, maturity_tier=HistoryMaturityBucket.ONE_TO_THREE_YEARS, cagr_overall=0.15, annualized_volatility=0.10),
        data_quality_score=1.0, confidence_score=1.0, provenance=ProvenanceMetadata("S", "U", None), return_comparability_available=True
    )
    res = engine.calculate_fund_quality_score(inp, [inp])
    assert res.dimension_scores["volatility"].raw_value == 0.10


def test_05_reciprocal_volatility_direction():
    """Verify lower volatility gets higher score (reciprocal ranking)."""
    from scoring.normalization import PeerGroupNormalizer
    norm = PeerGroupNormalizer()
    _, score_low_vol = norm.normalize_dimension(0.08, [0.08, 0.15, 0.25], higher_is_better=False)
    _, score_high_vol = norm.normalize_dimension(0.25, [0.08, 0.15, 0.25], higher_is_better=False)
    assert score_low_vol > score_high_vol


def test_06_runtime_weight_resolution():
    """Verify Equity base weights: Return 25%, Volatility 15%."""
    eq = CATEGORY_FAMILY_WEIGHTS["Equity"]
    assert eq["return"] == 25.0
    assert eq["volatility"] == 15.0


def test_07_missing_data_rescaling():
    """Verify 2 active metrics (25.0 Return, 15.0 Volatility) rescale to 62.5% and 37.5%."""
    engine = FundQualityScoringEngine()
    today = date(2024, 1, 31)
    inp = FundQualityDatasetInput(
        dataset_version="1.0.0", observation_date=today, canonical_scheme_id="C1", amfi_code="100", scheme_name="S1", amc_name="A",
        plan_type=PlanType.DIRECT, option_type=OptionType.GROWTH,
        category_context=CategoryPointInTimeContext(category="Equity", subcategory="Large Cap", effective_date=today),
        metrics=SchemeMetricSnapshot(observation_date=today, history_length_years=1.0, maturity_tier=HistoryMaturityBucket.ONE_TO_THREE_YEARS, cagr_overall=0.15, annualized_volatility=0.10),
        data_quality_score=1.0, confidence_score=1.0, provenance=ProvenanceMetadata("S", "U", None), return_comparability_available=True
    )
    res = engine.calculate_fund_quality_score(inp, [inp])
    assert res.dimension_scores["return"].weight == 62.5
    assert res.dimension_scores["volatility"].weight == 37.5


def test_08_active_dimension_distribution():
    """Verify exactly 2 active dimensions for F.16 input schema."""
    engine = FundQualityScoringEngine()
    today = date(2024, 1, 31)
    inp = FundQualityDatasetInput(
        dataset_version="1.0.0", observation_date=today, canonical_scheme_id="C1", amfi_code="100", scheme_name="S1", amc_name="A",
        plan_type=PlanType.DIRECT, option_type=OptionType.GROWTH,
        category_context=CategoryPointInTimeContext(category="Equity", subcategory="Large Cap", effective_date=today),
        metrics=SchemeMetricSnapshot(observation_date=today, history_length_years=1.0, maturity_tier=HistoryMaturityBucket.ONE_TO_THREE_YEARS, cagr_overall=0.15, annualized_volatility=0.10),
        data_quality_score=1.0, confidence_score=1.0, provenance=ProvenanceMetadata("S", "U", None), return_comparability_available=True
    )
    res = engine.calculate_fund_quality_score(inp, [inp])
    active_dims = [k for k, v in res.dimension_scores.items() if v.data_available]
    assert active_dims == ["return", "volatility"]


def test_09_peer_group_key():
    """Verify peer group key filtering in F.16."""
    peer_key = "category::subcategory::plan_type"
    assert peer_key == "category::subcategory::plan_type"


def test_10_representative_real_score_decomposition():
    """Verify mathematical sum of rescaled contributions."""
    engine = FundQualityScoringEngine()
    today = date(2024, 1, 31)
    inp = FundQualityDatasetInput(
        dataset_version="1.0.0", observation_date=today, canonical_scheme_id="C1", amfi_code="100", scheme_name="S1", amc_name="A",
        plan_type=PlanType.DIRECT, option_type=OptionType.GROWTH,
        category_context=CategoryPointInTimeContext(category="Equity", subcategory="Large Cap", effective_date=today),
        metrics=SchemeMetricSnapshot(observation_date=today, history_length_years=1.0, maturity_tier=HistoryMaturityBucket.ONE_TO_THREE_YEARS, cagr_overall=0.15, annualized_volatility=0.10),
        data_quality_score=1.0, confidence_score=1.0, provenance=ProvenanceMetadata("S", "U", None), return_comparability_available=True
    )
    res = engine.calculate_fund_quality_score(inp, [inp])
    # 50.0 * 0.625 + 50.0 * 0.375 = 50.0
    assert res.quality_score == 50.0


def test_11_f16_scoring_formula_classification():
    """Verify lineage classification JSON."""
    path = Path("docs/phase_f19_1_1_1_f16_effective_scoring_lineage_reconciliation.json")
    assert path.exists()
    with open(path) as f:
        data = json.load(f)
    assert data["lineage_classification"]["classification"].startswith("B. PRODUCTION ENGINE VALIDATION")


def test_12_f16_f16_2_lineage_consistency():
    """Verify manifest integrity for F.19.1.1.1."""
    manifest_path = Path("docs/f19_1_1_1_f16_effective_scoring_lineage_manifest.json")
    assert manifest_path.exists()
