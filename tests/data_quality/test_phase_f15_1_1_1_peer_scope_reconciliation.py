"""
Tests for Phase F.15.1.1.1 — Production Peer-Group Scope & Sensitivity Forensic Reconciliation
File: tests/data_quality/test_phase_f15_1_1_1_peer_scope_reconciliation.py
"""

import pytest
import os
import json
from scoring.engine import FundQualityScoringEngine
from scoring.normalization import PeerGroupNormalizer
from models.fund_quality_dataset import (
    FundQualityDatasetInput,
    SchemeMetricSnapshot,
    CategoryPointInTimeContext,
    OptionType,
    PlanType,
    ProvenanceMetadata
)
from models.metric_data import HistoryMaturityBucket
from datetime import date


def test_production_peer_group_filtering():
    """Verify that FundQualityScoringEngine isolates peers by category, subcategory, and plan_type."""
    engine = FundQualityScoringEngine()
    
    target = FundQualityDatasetInput(
        dataset_version="1.0.0",
        observation_date=date(2024, 1, 31),
        canonical_scheme_id="SCHEME_TARGET",
        amfi_code="100001",
        scheme_name="Target Fund Direct Growth",
        amc_name="AMC1",
        plan_type=PlanType.DIRECT,
        option_type=OptionType.GROWTH,
        category_context=CategoryPointInTimeContext(
            category="Equity",
            subcategory="Large Cap",
            effective_date=date(2024, 1, 31)
        ),
        metrics=SchemeMetricSnapshot(
            observation_date=date(2024, 1, 31),
            history_length_years=5.0,
            maturity_tier=HistoryMaturityBucket.THREE_TO_FIVE_YEARS,
            cagr_overall=0.15,
            annualized_volatility=0.12
        ),
        data_quality_score=1.0,
        confidence_score=1.0,
        provenance=ProvenanceMetadata(source_id="TEST", source_document_url="http://ex.com", retrieval_timestamp_utc=date(2024,1,31))
    )
    
    matching_peer = FundQualityDatasetInput(
        dataset_version="1.0.0",
        observation_date=date(2024, 1, 31),
        canonical_scheme_id="SCHEME_PEER_MATCH",
        amfi_code="100002",
        scheme_name="Peer Fund Direct Growth",
        amc_name="AMC2",
        plan_type=PlanType.DIRECT,
        option_type=OptionType.GROWTH,
        category_context=CategoryPointInTimeContext(
            category="Equity",
            subcategory="Large Cap",
            effective_date=date(2024, 1, 31)
        ),
        metrics=SchemeMetricSnapshot(
            observation_date=date(2024, 1, 31),
            history_length_years=5.0,
            maturity_tier=HistoryMaturityBucket.THREE_TO_FIVE_YEARS,
            cagr_overall=0.18,
            annualized_volatility=0.14
        ),
        data_quality_score=1.0,
        confidence_score=1.0,
        provenance=ProvenanceMetadata(source_id="TEST", source_document_url="http://ex.com", retrieval_timestamp_utc=date(2024,1,31))
    )

    non_matching_peer = FundQualityDatasetInput(
        dataset_version="1.0.0",
        observation_date=date(2024, 1, 31),
        canonical_scheme_id="SCHEME_PEER_NONMATCH",
        amfi_code="100003",
        scheme_name="Debt Fund Regular Growth",
        amc_name="AMC3",
        plan_type=PlanType.REGULAR,
        option_type=OptionType.GROWTH,
        category_context=CategoryPointInTimeContext(
            category="Debt",
            subcategory="Liquid",
            effective_date=date(2024, 1, 31)
        ),
        metrics=SchemeMetricSnapshot(
            observation_date=date(2024, 1, 31),
            history_length_years=5.0,
            maturity_tier=HistoryMaturityBucket.THREE_TO_FIVE_YEARS,
            cagr_overall=0.06,
            annualized_volatility=0.02
        ),
        data_quality_score=1.0,
        confidence_score=1.0,
        provenance=ProvenanceMetadata(source_id="TEST", source_document_url="http://ex.com", retrieval_timestamp_utc=date(2024,1,31))
    )

    result = engine.calculate_fund_quality_score(target, [target, matching_peer, non_matching_peer])
    assert result.peer_group_size == 2  # Only target and matching_peer included


def test_percentile_rank_exact_formula():
    """Verify exact formula ((rank - 0.5) / n) * 100 in PeerGroupNormalizer."""
    normalizer = PeerGroupNormalizer()
    peers = [10.0, 20.0, 30.0, 40.0]  # N = 4
    # For target 40.0: rank 4. Score = ((4 - 0.5)/4)*100 = 87.5
    _, score = normalizer.normalize_dimension(40.0, peers, higher_is_better=True)
    assert score == pytest.approx(87.5)


def test_reconciliation_artifacts_validity():
    """Verify phase JSON artifact structure and key metrics."""
    json_path = os.path.join("docs", "phase_f15_1_1_1_peer_scope_reconciliation.json")
    assert os.path.exists(json_path)
    
    with open(json_path, "r") as f:
        data = json.load(f)
        assert data["exact_production_oos_validation_status"] == "EXACT_PRODUCTION_OOS_VALIDATION_PENDING"
        assert data["reconstructed_metrics"]["formula_A_vs_B"]["pearson_r"] == pytest.approx(0.5365, abs=0.001)
        assert data["reconstructed_metrics"]["formula_A_vs_B"]["top_decile_overlap_pct"] == pytest.approx(1.98, abs=0.1)
