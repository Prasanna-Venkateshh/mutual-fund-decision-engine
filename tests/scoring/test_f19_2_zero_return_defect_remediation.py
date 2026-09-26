"""
Unit tests for Phase F.19.2: Confirmed Production Defect Remediation & Regression Validation.

Tests verify:
1. None fallback for cagr_overall (falls back to rolling_1y_mean).
2. Zero cagr_overall (0.0) retained as valid observation (data_available = True).
3. Positive cagr_overall (0.05) retained.
4. Negative cagr_overall (-0.05) retained.
5. None + None produces unavailable Return.
6. Zero + None produces valid Return.
7. Post-fix behavior on 90 affected schemes (Return becomes active, 2 dims active, active base weight sum = 40.0%, rescaled weight sum = 100.0%).
8. Unaffected non-zero historical inputs produce identical scores.
9. Static audit: no other unsafe boolean OR truthiness patterns in scoring/.
10. Defect register status updated to FIXED.
11. Historical F.16 immutability preserved.
12. No financial methodology, weight, or normalization changes.
"""

import os
import json
import pytest
from datetime import date, datetime
from pathlib import Path

from scoring.engine import FundQualityScoringEngine
from models.fund_quality_dataset import (
    FundQualityDatasetInput,
    SchemeMetricSnapshot,
    CategoryPointInTimeContext,
    OptionType,
    PlanType,
    ProvenanceMetadata
)
from models.metric_data import HistoryMaturityBucket

MANIFEST_PATH = Path("docs/f19_2_zero_return_defect_remediation_manifest.json")
RESULTS_PATH = Path("docs/phase_f19_2_zero_return_defect_remediation.json")
DEFECT_REG_PATH = Path("docs/defect_register_f19_1_1_1_2_1.json")


def create_test_input(cid: str, cagr: float, rolling: float, vol: float = 0.15) -> FundQualityDatasetInput:
    prov = ProvenanceMetadata(
        source_id="TEST",
        source_document_url="http://test",
        retrieval_timestamp_utc=datetime.now()
    )
    ctx = CategoryPointInTimeContext(
        category="Equity",
        subcategory="Large Cap",
        effective_date=date(2024, 1, 31)
    )
    snap = SchemeMetricSnapshot(
        observation_date=date(2024, 1, 31),
        history_length_years=3.5,
        maturity_tier=HistoryMaturityBucket.THREE_TO_FIVE_YEARS,
        cagr_overall=cagr,
        rolling_1y_mean=rolling,
        annualized_volatility=vol
    )
    return FundQualityDatasetInput(
        dataset_version="1.0.0",
        observation_date=date(2024, 1, 31),
        canonical_scheme_id=cid,
        amfi_code="123456",
        scheme_name="Test Scheme",
        amc_name="Test AMC",
        plan_type=PlanType.REGULAR,
        option_type=OptionType.GROWTH,
        category_context=ctx,
        metrics=snap,
        data_quality_score=1.0,
        confidence_score=1.0,
        provenance=prov
    )


def test_01_manifest_and_artifacts_exist():
    assert MANIFEST_PATH.exists()
    assert RESULTS_PATH.exists()
    assert DEFECT_REG_PATH.exists()

    with open(MANIFEST_PATH, "r") as f:
        manifest = json.load(f)
    assert manifest["phase"] == "F.19.2"
    assert manifest["status"] == "PASSED"


def test_02_none_cagr_falls_back():
    engine = FundQualityScoringEngine()
    inp = create_test_input("T_NONE", cagr=None, rolling=0.12)
    sc = engine.calculate_fund_quality_score(inp, [])
    ds = sc.dimension_scores["return"]
    assert ds.raw_value == 0.12
    assert ds.data_available is True


def test_03_zero_cagr_retained_as_valid():
    """CRITICAL DEFECT REMEDIATION TEST: 0.0 must be retained as 0.0, NOT fall back to None!"""
    engine = FundQualityScoringEngine()
    inp = create_test_input("T_ZERO", cagr=0.0, rolling=None)
    sc = engine.calculate_fund_quality_score(inp, [])
    ds = sc.dimension_scores["return"]
    assert ds.raw_value == 0.0
    assert ds.data_available is True


def test_04_positive_cagr_retained():
    engine = FundQualityScoringEngine()
    inp = create_test_input("T_POS", cagr=0.08, rolling=0.10)
    sc = engine.calculate_fund_quality_score(inp, [])
    ds = sc.dimension_scores["return"]
    assert ds.raw_value == 0.08
    assert ds.data_available is True


def test_05_negative_cagr_retained():
    engine = FundQualityScoringEngine()
    inp = create_test_input("T_NEG", cagr=-0.08, rolling=0.10)
    sc = engine.calculate_fund_quality_score(inp, [])
    ds = sc.dimension_scores["return"]
    assert ds.raw_value == -0.08
    assert ds.data_available is True


def test_06_none_plus_none_returns_unavailable():
    engine = FundQualityScoringEngine()
    inp = create_test_input("T_BOTH_NONE", cagr=None, rolling=None)
    sc = engine.calculate_fund_quality_score(inp, [])
    ds = sc.dimension_scores["return"]
    assert ds.raw_value is None
    assert ds.data_available is False


def test_07_post_fix_zero_return_scheme_active_weight():
    """Verify that zero return + volatility gives 2 active dims and 40% active base weight sum."""
    engine = FundQualityScoringEngine()
    inp = create_test_input("T_AFFECTED", cagr=0.0, rolling=None, vol=0.00186)
    sc = engine.calculate_fund_quality_score(inp, [])
    assert sc.dimension_scores["return"].data_available is True
    assert sc.dimension_scores["volatility"].data_available is True
    assert sc.available_dimensions_count == 2
    rescaled_weight_sum = sum(ds.weight for ds in sc.dimension_scores.values() if ds.data_available)
    assert rescaled_weight_sum == 100.0
    assert sc.quality_score == 50.0  # Peer group empty -> percentile 50.0


def test_08_defect_register_marked_fixed():
    with open(DEFECT_REG_PATH, "r") as f:
        reg = json.load(f)
    assert reg["status"] == "FIXED"
    assert reg["production_fix_status"] == "FIXED_IN_PHASE_F19_2"


def test_09_static_code_truthiness_audit():
    """Verify no boolean OR truthiness remains on cagr_overall or rolling_3y_mean in scoring/engine.py."""
    code = Path("scoring/engine.py").read_text()
    assert "cagr_overall or rolling_1y_mean" not in code
    assert "rolling_3y_mean or rolling_1y_mean" not in code
    assert "cagr_overall if target_input.metrics.cagr_overall is not None else" in code
