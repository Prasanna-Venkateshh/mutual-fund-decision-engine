"""
Phase D.6 Fund Quality Dataset Builder & Adapter Integration Test Suite.

Tests:
1. Identity Adapter resolution and quarantine.
2. Metric Adapter point-in-time calculation.
3. Incomplete history / New Fund handling (Missing != 0).
4. Point-in-time category context resolution.
5. Pre-2018 TER missing handling (None != 0.0).
6. Quantitative Data Quality and Confidence validation.
7. Dataset Builder construction and provenance preservation.
8. Anti-survivorship peer group selection.
9. Database persistence & retrieval in FundQualityDatasetRepository.
10. Absence of scoring or ranking leakage.
"""

from datetime import date, datetime, timezone
import sqlite3
import pytest

from models.fund_quality_dataset import (
    FundQualityDatasetInput,
    PlanType,
    OptionType
)
from models.metric_data import HistoryMaturityBucket
from data.adapters.scheme_identity_adapter import SchemeIdentityAdapter
from data.adapters.scoring_metric_adapter import ScoringMetricAdapter
from data.adapters.category_context_adapter import CategoryContextAdapter
from data.adapters.ter_adapter import TERAdapter
from data.adapters.maturity_adapter import MaturityAdapter
from data.validators.scoring_dataset_validator import ScoringDatasetValidator
from data.builders.fund_quality_dataset_builder import FundQualityDatasetBuilder
from data.repositories.fund_quality_dataset_repository import FundQualityDatasetRepository


class TestFundQualityDatasetBuilder:
    """Test suite for Phase D.6 dataset construction and adapters."""

    @pytest.fixture
    def sample_nav_history(self):
        """Generates 5+ years of daily NAV history (2018 to 2023)."""
        nav_records = []
        base_date = date(2018, 1, 1)
        base_nav = 10.0
        # 2000 trading days (~5.47 years)
        for i in range(2000):
            nav_date = date.fromordinal(base_date.toordinal() + i)
            # 10% annual compound growth approximation
            val = base_nav * (1.10 ** (i / 365.25))
            nav_records.append({
                "nav_date": nav_date,
                "nav_value": round(val, 4)
            })
        return nav_records

    @pytest.fixture
    def short_nav_history(self):
        """Generates 6 months of NAV history for a new fund."""
        nav_records = []
        base_date = date(2023, 1, 1)
        base_nav = 10.0
        for i in range(180):
            nav_date = date.fromordinal(base_date.toordinal() + i)
            val = base_nav * (1.05 ** (i / 365.25))
            nav_records.append({
                "nav_date": nav_date,
                "nav_value": round(val, 4)
            })
        return nav_records

    def test_01_identity_adapter_resolution(self):
        adapter = SchemeIdentityAdapter()
        res = adapter.resolve_identity(
            amfi_code="119551",
            scheme_name="HDFC Small Cap Fund - Direct Plan - Growth Option",
            isin_growth="INF179KC1HS0"
        )
        assert res["canonical_scheme_id"] is not None
        assert res["amfi_code"] == "119551"
        assert res["plan_type"] == PlanType.DIRECT
        assert res["option_type"] == OptionType.GROWTH
        assert res["amc_name"] == "HDFC"
        assert res["is_quarantined"] is False

    def test_02_ambiguous_identity_quarantine(self):
        adapter = SchemeIdentityAdapter()
        res = adapter.resolve_identity(
            amfi_code="100001",
            scheme_name="Ambiguous Scheme Without Plan Details"
        )
        assert res["plan_type"] == PlanType.UNKNOWN
        assert res["is_quarantined"] is True
        assert len(res["quarantine_reasons"]) > 0

    def test_03_metric_adapter_snapshot_computation(self, sample_nav_history):
        adapter = ScoringMetricAdapter()
        obs_date = date(2023, 1, 1)
        snapshot = adapter.compute_metric_snapshot(
            nav_records=sample_nav_history,
            observation_date=obs_date,
            ter_value=0.75,
            ter_observation_date=obs_date
        )

        assert snapshot.maturity_tier == HistoryMaturityBucket.FIVE_TO_TEN_YEARS
        assert snapshot.history_length_years >= 4.9
        assert snapshot.cagr_overall is not None
        assert snapshot.cagr_overall > 0.05
        assert snapshot.annualized_volatility is not None
        assert snapshot.max_drawdown is not None
        assert snapshot.total_expense_ratio == 0.75

    def test_04_incomplete_history_new_fund(self, short_nav_history):
        adapter = ScoringMetricAdapter()
        obs_date = date(2023, 6, 1)
        snapshot = adapter.compute_metric_snapshot(
            nav_records=short_nav_history,
            observation_date=obs_date
        )

        assert snapshot.maturity_tier == HistoryMaturityBucket.LESS_THAN_1_YEAR
        assert snapshot.cagr_overall is None  # Missing != 0
        assert snapshot.cagr_3y is None
        assert snapshot.rolling_1y_mean is None

    def test_05_category_context_point_in_time(self):
        adapter = CategoryContextAdapter()
        # Post-2017 circular date
        obs_post = date(2020, 1, 1)
        ctx_post = adapter.resolve_category_context("scheme_1", "SBI Small Cap Fund - Direct Plan", obs_post)
        assert ctx_post.category == "Equity"
        assert ctx_post.subcategory == "Small Cap"
        assert ctx_post.source == "SEBI_2017_CIRCULAR"
        assert ctx_post.confidence_score == 1.0

        # Pre-2017 circular date - missing historical evidence returns UNSPECIFIED
        obs_pre = date(2015, 1, 1)
        ctx_pre = adapter.resolve_category_context("scheme_1", "SBI Small Cap Fund - Direct Plan", obs_pre)
        assert ctx_pre.category == "UNSPECIFIED"
        assert ctx_pre.source == "PRE_SEBI_2017_UNKNOWN"
        assert ctx_pre.confidence_score == 0.0

    def test_06_ter_adapter_missing_pre_2018(self):
        adapter = TERAdapter()
        obs_pre = date(2015, 1, 1)
        ter_val, ter_date = adapter.resolve_ter("scheme_1", "DIRECT", obs_pre)
        assert ter_val is None  # Missing != 0.0
        assert ter_date is None

    def test_07_validator_data_quality_and_confidence(self, sample_nav_history):
        builder = FundQualityDatasetBuilder()
        obs_date = date(2023, 1, 1)
        record = builder.build_dataset_input_for_scheme(
            amfi_code="119551",
            scheme_name="HDFC Small Cap Fund - Direct Plan - Growth Option",
            observation_date=obs_date,
            nav_history=sample_nav_history
        )

        assert record.data_quality_score >= 0.8
        assert record.confidence_score >= 0.8
        assert record.is_quarantined is False

    def test_08_dataset_builder_full_contract(self, sample_nav_history):
        builder = FundQualityDatasetBuilder()
        obs_date = date(2023, 1, 1)
        record = builder.build_dataset_input_for_scheme(
            amfi_code="119551",
            scheme_name="HDFC Small Cap Fund - Direct Plan - Growth Option",
            observation_date=obs_date,
            nav_history=sample_nav_history,
            source_id="AMFI_OFFICIAL",
            source_document_url="https://www.amfiindia.com/net-asset-value"
        )

        assert record.canonical_scheme_id is not None
        assert record.amfi_code == "119551"
        assert record.plan_type == PlanType.DIRECT
        assert record.option_type == OptionType.GROWTH
        assert record.provenance.source_id == "AMFI_OFFICIAL"
        assert record.provenance.source_document_url == "https://www.amfiindia.com/net-asset-value"
        assert record.provenance.retrieval_timestamp_utc is not None

    def test_09_peer_group_builder_anti_survivorship(self, sample_nav_history):
        builder = FundQualityDatasetBuilder()
        obs_date = date(2023, 1, 1)
        pool = [
            {
                "amfi_code": "119551",
                "scheme_name": "HDFC Small Cap Fund - Direct Plan - Growth Option",
                "nav_history": sample_nav_history
            },
            {
                "amfi_code": "125497",
                "scheme_name": "SBI Small Cap Fund - Direct Plan - Growth Option",
                "nav_history": sample_nav_history
            },
            {
                "amfi_code": "100002",
                "scheme_name": "Liquid Fund - Regular Plan - Growth Option",
                "nav_history": sample_nav_history
            }
        ]

        peers = builder.build_peer_dataset_for_category(
            category="Equity",
            subcategory="Small Cap",
            observation_date=obs_date,
            schemes_pool=pool
        )

        assert len(peers) == 2
        assert all(p.category_context.subcategory == "Small Cap" for p in peers)

    def test_10_dataset_repository_persistence(self, sample_nav_history):
        conn = sqlite3.connect(":memory:")
        repo = FundQualityDatasetRepository(conn)
        builder = FundQualityDatasetBuilder()
        obs_date = date(2023, 1, 1)

        record = builder.build_dataset_input_for_scheme(
            amfi_code="119551",
            scheme_name="HDFC Small Cap Fund - Direct Plan - Growth Option",
            observation_date=obs_date,
            nav_history=sample_nav_history
        )

        record_id = repo.save_dataset_record(record)
        assert record_id is not None

        retrieved = repo.get_dataset_record(
            canonical_scheme_id=record.canonical_scheme_id,
            observation_date=obs_date
        )

        assert retrieved is not None
        assert retrieved.canonical_scheme_id == record.canonical_scheme_id
        assert retrieved.amfi_code == "119551"
        assert retrieved.plan_type == PlanType.DIRECT
        assert retrieved.data_quality_score == record.data_quality_score

    def test_11_no_nav_stitching_invariant(self, sample_nav_history):
        builder = FundQualityDatasetBuilder()
        obs_date = date(2023, 1, 1)

        pred = builder.build_dataset_input_for_scheme(
            amfi_code="100001",
            scheme_name="Old Predecessor Fund - Direct Growth",
            observation_date=obs_date,
            nav_history=sample_nav_history,
            override_canonical_id="UUID_PREDECESSOR_1"
        )

        succ = builder.build_dataset_input_for_scheme(
            amfi_code="100002",
            scheme_name="New Successor Fund - Direct Growth",
            observation_date=obs_date,
            nav_history=sample_nav_history,
            override_canonical_id="UUID_SUCCESSOR_2"
        )

        assert pred.canonical_scheme_id != succ.canonical_scheme_id
        assert pred.canonical_scheme_id == "UUID_PREDECESSOR_1"
        assert succ.canonical_scheme_id == "UUID_SUCCESSOR_2"

    def test_12_no_scoring_or_ranking_leakage(self, sample_nav_history):
        builder = FundQualityDatasetBuilder()
        obs_date = date(2023, 1, 1)
        record = builder.build_dataset_input_for_scheme(
            amfi_code="119551",
            scheme_name="HDFC Small Cap Fund - Direct Plan - Growth Option",
            observation_date=obs_date,
            nav_history=sample_nav_history
        )

        # Confirm no final score, numerical weights, or buy/sell recommendations exist in contract
        assert not hasattr(record, "quality_score")
        assert not hasattr(record, "fund_rank")
        assert not hasattr(record, "buy_recommendation")
        assert not hasattr(record, "target_weight")
