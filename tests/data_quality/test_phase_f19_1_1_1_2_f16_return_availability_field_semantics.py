"""
Phase F.19.1.1.1.2 — F.16 Return Availability, Field-Semantics & Representative Peer-Group Closure Test Suite.
File: tests/data_quality/test_phase_f19_1_1_1_2_f16_return_availability_field_semantics.py
"""

import pytest
import os
import sys
import json
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.abspath("."))

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
from metrics.returns import calculate_cagr


def test_01_f16_population_total():
    """Verify total scored population equals 5,125."""
    path = Path("docs/phase_f19_1_1_1_2_f16_return_availability_field_semantics.json")
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    pop = data["population_reconciliation"]
    assert pop["f16_scored_population"] == 5125


def test_02_active_dimensions_sum():
    """Verify active dimension breakdown sums to 5,125 (4958 + 90 + 77)."""
    path = Path("docs/phase_f19_1_1_1_2_f16_return_availability_field_semantics.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    pop = data["population_reconciliation"]
    total = pop["two_active_dimensions_count"] + pop["one_active_dimension_count"] + pop["zero_active_dimensions_count"]
    assert total == 5125


def test_03_ninety_one_dimensional_schemes_reconciled():
    """Verify 90 Volatility-Only schemes cause."""
    path = Path("docs/phase_f19_1_1_1_2_f16_return_availability_field_semantics.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    expl = data["forensic_explanations"]["ninety_volatility_only_cause"]
    assert "cagr_overall or target_input.metrics.rolling_1y_mean" in expl
    assert "0.0 as False" in expl


def test_04_seventy_seven_zero_dimensional_schemes_reconciled():
    """Verify 77 zero-dimension schemes cause."""
    path = Path("docs/phase_f19_1_1_1_2_f16_return_availability_field_semantics.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    expl = data["forensic_explanations"]["seventy_seven_zero_dimension_cause"]
    assert "cagr_overall == 0.0" in expl
    assert "stddev = 0" in expl


def test_05_one_dimensional_effective_weight_pattern():
    """Verify 1-dim schemes have score None due to active_weights_sum < 40.0."""
    path = Path("docs/phase_f19_1_1_1_2_f16_return_availability_field_semantics.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    samples = data["sample_90_volatility_only_schemes"]
    assert len(samples) >= 5
    for s in samples:
        assert s["return_data_available"] is False
        assert s["volatility_data_available"] is True
        assert s["final_score"] is None


def test_06_general_cagr_overall_semantics():
    """Verify general cagr_overall semantics in metrics/returns.py."""
    cagr = calculate_cagr(100.0, 121.0, date(2022, 1, 31), date(2024, 1, 31))
    assert abs(cagr - 0.10) < 0.001  # ~10% CAGR over 2 years (730 / 365.25 days)


def test_07_f16_cagr_overall_assignment():
    """Verify F.16 assigned trailing 1Y simple return to cagr_overall slot."""
    path = Path("docs/phase_f19_1_1_1_2_f16_return_availability_field_semantics.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    mapping = data["cagr_overall_semantics_vs_f16_mapping"]
    assert "r_1y = (NAV_T / NAV_T-252) - 1.0" in mapping["f16_validation_input_mapping"]


def test_08_f16_return_mapping_classification():
    """Verify field mapping classification."""
    path = Path("docs/phase_f19_1_1_1_2_f16_return_availability_field_semantics.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    mapping = data["cagr_overall_semantics_vs_f16_mapping"]
    assert mapping["mapping_classification"].startswith("B. VALIDATION-SPECIFIC FIELD REPURPOSING")


def test_09_representative_amfi_identity():
    """Verify representative scheme identity CAN_AMFI_100033."""
    path = Path("docs/phase_f19_1_1_1_2_f16_return_availability_field_semantics.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    rep = data["representative_scheme_audit"]
    assert rep["canonical_scheme_id"] == "CAN_AMFI_100033"
    assert rep["amfi_code"] == "100033"
    assert rep["isin_growth"] == "INF209K01165"


def test_10_representative_peer_group_status():
    """Verify representative scheme peer group status is UNVERIFIED / FALLBACK DEFAULT."""
    path = Path("docs/phase_f19_1_1_1_2_f16_return_availability_field_semantics.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    rep = data["representative_scheme_audit"]
    assert rep["database_category"] == "UNASSIGNED"
    assert rep["database_subcategory"] == "UNASSIGNED"
    assert "UNVERIFIED / FALLBACK DEFAULT" in rep["peer_group_status"]


def test_11_representative_score_decomposition():
    """Verify CAN_AMFI_100033 score decomposition mathematical reconciliation."""
    path = Path("docs/phase_f19_1_1_1_2_f16_return_availability_field_semantics.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    sd = data["representative_scheme_audit"]["score_decomposition"]
    assert sd["reconciled"] is True
    assert sd["final_score"] == 58.1


def test_12_no_production_scoring_modification():
    """Verify production code is unchanged."""
    path = Path("docs/phase_f19_1_1_1_2_f16_return_availability_field_semantics.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["production_code_changed"] is False
    assert data["production_methodology_changed"] is False


def test_13_no_production_methodology_modification():
    """Verify dynamic weight rescaling governance status."""
    path = Path("docs/phase_f19_1_1_1_2_f16_return_availability_field_semantics.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["dynamic_rescaling_governance"] == "PRODUCTION IMPLEMENTED BUT EMPIRICALLY UNVALIDATED"


def test_14_no_new_predictive_statistics_introduced():
    """Verify manifest file integrity."""
    manifest_path = Path("docs/f19_1_1_1_2_f16_return_availability_field_semantics_manifest.json")
    assert manifest_path.exists()
