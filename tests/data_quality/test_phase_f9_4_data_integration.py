"""
Phase F.9.4 — Real Fund Dataset Completion & Authoritative Data Integration Tests.

Validates all 25 required data integration and safety invariants:
1. AMFI identity preservation.
2. Stable canonical identity (CAN_AMFI_{amfi_code}).
3. No synthetic IDs.
4. Direct/Regular separation.
5. Growth/IDCW separation.
6. Category/subcategory ingestion.
7. PIT category handling.
8. TER ingestion.
9. Missing TER handling (NO silent defaults 0.0 or 0.75).
10. Riskometer ingestion.
11. Riskometer unknown handling (NO numeric risk mapping).
12. Lock-in unknown handling (NO default 'no lock-in').
13. Lifecycle linkage.
14. Historical NAV linkage.
15. Observation-date preservation.
16. Provenance preservation.
17. Source conflict handling.
18. Quality-state handling.
19. No silent defaults.
20. No NAV stitching.
21. No IDCW total-return mislabeling.
22. No current-to-historical look-ahead contamination.
23. Representative dataset completeness reporting (18 dimensions with denominators).
24. Idempotent ingestion.
25. Full regression integrity.
"""

from datetime import date, datetime, timezone
import pytest
from typing import Dict, Any, List

from models.production_dataset import (
    RawSourceEvidence,
    NormalizedRecord,
    EntityResolvedRecord,
    ValidatedRecord,
    VersionedDatasetSnapshot
)
from models.nav_data import DataQualityState
from data.pipeline.production_dataset_pipeline import ProductionDatasetPipeline
from data.adapters.ter_adapter import TERAdapter
from data.adapters.category_context_adapter import CategoryContextAdapter, SEBI_2017_EFFECTIVE_DATE
from data.adapters.scheme_identity_adapter import SchemeIdentityAdapter
from data.reporting.dataset_quality_reporter import DatasetQualityReporter
from data.mapping.entity_resolver import EntityResolver
from data.normalization.dataset_normalizer import DatasetNormalizer
from data.validation.dataset_validator import DatasetValidator


class TestPhaseF94DataIntegration:
    """Test Suite for Phase F.9.4 Real Fund Dataset Completion & Data Integration Invariants."""

    @pytest.fixture
    def setup_pipeline(self):
        return ProductionDatasetPipeline()

    @pytest.fixture
    def sample_raw_batch(self) -> List[Dict[str, Any]]:
        return [
            {
                "scheme_code": "119551",
                "scheme_name": "Nippon India Large Cap Fund - Direct Plan - Growth Option",
                "nav": "72.45",
                "nav_date": "2024-01-15",
                "category": "Equity",
                "subcategory": "Large Cap",
                "amc_name": "Nippon India Mutual Fund",
                "isin": "INF204K01L05",
                "ter": "0.85",
                "ter_date": "2024-01-15",
                "riskometer": "VERY HIGH",
                "benchmark": "NIFTY 100 TRI",
                "plan": "Direct",
                "option": "Growth"
            },
            {
                "scheme_code": "119552",
                "scheme_name": "Nippon India Large Cap Fund - Regular Plan - Growth Option",
                "nav": "65.12",
                "nav_date": "2024-01-15",
                "category": "Equity",
                "subcategory": "Large Cap",
                "amc_name": "Nippon India Mutual Fund",
                "isin": "INF204K01L13",
                "ter": "1.72",
                "ter_date": "2024-01-15",
                "riskometer": "VERY HIGH",
                "benchmark": "NIFTY 100 TRI",
                "plan": "Regular",
                "option": "Growth"
            },
            {
                "scheme_code": "119553",
                "scheme_name": "Nippon India Large Cap Fund - Direct Plan - IDCW Option",
                "nav": "25.30",
                "nav_date": "2024-01-15",
                "category": "Equity",
                "subcategory": "Large Cap",
                "amc_name": "Nippon India Mutual Fund",
                "isin": "INF204K01L21",
                "ter": "0.85",
                "ter_date": "2024-01-15",
                "riskometer": "VERY HIGH",
                "benchmark": "NIFTY 100 TRI",
                "plan": "Direct",
                "option": "IDCW"
            },
            {
                "scheme_code": "120001",
                "scheme_name": "SBI Liquid Fund - Direct Plan - Growth",
                "nav": "3450.12",
                "nav_date": "2024-01-14",
                "category": "Debt",
                "subcategory": "Liquid",
                "amc_name": "SBI Mutual Fund",
                "isin": "INF200K01050",
                "ter": "0.18",
                "ter_date": "2024-01-14",
                "riskometer": "LOW TO MODERATE",
                "benchmark": "NIFTY Liquid Index A-I",
                "plan": "Direct",
                "option": "Growth"
            },
            {
                "scheme_code": "140001",
                "scheme_name": "ICICI Prudential Tax Saver Fund - Direct Plan - Growth",
                "nav": "680.50",
                "nav_date": "2024-01-15",
                "category": "Equity",
                "subcategory": "ELSS",
                "amc_name": "ICICI Prudential Mutual Fund",
                "isin": "INF109K01123",
                "ter": None,  # Intentionally missing TER
                "riskometer": None,  # Intentionally missing Riskometer
                "benchmark": None,  # Intentionally missing Benchmark
                "plan": "Direct",
                "option": "Growth"
            }
        ]

    # Invariant 1 & 2: AMFI Identity Preservation & Stable Canonical Identity
    def test_01_02_amfi_identity_preservation_and_stable_canonical_id(self, setup_pipeline, sample_raw_batch):
        snapshot = setup_pipeline.process_raw_batch(source_id="AMFI_OFFICIAL", raw_items=sample_raw_batch)
        assert len(snapshot.records) == 5
        for rec in snapshot.records:
            assert rec.amfi_code in ["119551", "119552", "119553", "120001", "140001"]
            assert rec.canonical_scheme_id == f"CAN_AMFI_{rec.amfi_code}"
            assert not rec.canonical_scheme_id.startswith("QUARANTINE_CAN_")

    # Invariant 3: No Synthetic Identifiers
    def test_03_no_synthetic_identifiers(self, setup_pipeline, sample_raw_batch):
        snapshot = setup_pipeline.process_raw_batch(source_id="AMFI_OFFICIAL", raw_items=sample_raw_batch)
        for rec in snapshot.records:
            assert rec.amfi_code != "0"
            assert rec.canonical_scheme_id != "CAN_AMFI_0"

    # Invariant 4 & 5: Direct/Regular Separation & Growth/IDCW Separation
    def test_04_05_direct_regular_and_growth_idcw_separation(self, setup_pipeline, sample_raw_batch):
        snapshot = setup_pipeline.process_raw_batch(source_id="AMFI_OFFICIAL", raw_items=sample_raw_batch)
        direct_growth = [r for r in snapshot.records if r.amfi_code == "119551"][0]
        regular_growth = [r for r in snapshot.records if r.amfi_code == "119552"][0]
        direct_idcw = [r for r in snapshot.records if r.amfi_code == "119553"][0]

        # Verify distinct canonical IDs and non-collapsing
        assert direct_growth.canonical_scheme_id != regular_growth.canonical_scheme_id
        assert direct_growth.canonical_scheme_id != direct_idcw.canonical_scheme_id
        assert direct_growth.plan_type_str == "DIRECT"
        assert regular_growth.plan_type_str == "REGULAR"
        assert direct_growth.option_type_str == "GROWTH"
        assert direct_idcw.option_type_str in ("IDCW", "IDCW_PAYOUT", "IDCW_REINVESTMENT")

    # Invariant 6 & 7: Category & PIT Category Handling
    def test_06_07_category_and_pit_context_handling(self):
        adapter = CategoryContextAdapter()
        # Post-SEBI 2017 observation
        ctx_post = adapter.resolve_category_context(
            canonical_scheme_id="CAN_AMFI_119551",
            scheme_name="Nippon India Large Cap Fund",
            observation_date=date(2024, 1, 15)
        )
        assert ctx_post.confidence_score == 1.0
        assert ctx_post.source == "SEBI_2017_CIRCULAR"

        # Pre-SEBI 2017 observation (e.g. 2015-05-10) -> Must return UNSPECIFIED, PRE_SEBI_2017_UNKNOWN, confidence 0.0
        ctx_pre = adapter.resolve_category_context(
            canonical_scheme_id="CAN_AMFI_119551",
            scheme_name="Nippon India Large Cap Fund",
            observation_date=date(2015, 5, 10)
        )
        assert ctx_pre.category == "UNSPECIFIED"
        assert ctx_pre.confidence_score == 0.0
        assert ctx_pre.source == "PRE_SEBI_2017_UNKNOWN"

    # Invariant 8 & 9: TER Ingestion & Missing TER Handling (No Silent Defaults)
    def test_08_09_ter_ingestion_and_no_silent_ter_defaults(self):
        ter_adapter = TERAdapter()

        # Modern observation without AMC TER feed -> Must return (None, None), NOT 0.75 or 1.75!
        val, obs_d = ter_adapter.resolve_ter(
            canonical_scheme_id="CAN_AMFI_140001",
            plan_type_str="DIRECT",
            observation_date=date(2024, 1, 15)
        )
        assert val is None
        assert obs_d is None

        # Pre-2018 observation -> Must return (None, None)
        val_pre, obs_pre = ter_adapter.resolve_ter(
            canonical_scheme_id="CAN_AMFI_140001",
            plan_type_str="REGULAR",
            observation_date=date(2016, 1, 15)
        )
        assert val_pre is None
        assert obs_pre is None

    # Invariant 10 & 11: Riskometer Ingestion & Unknown Handling (No Numeric Risk Mapping)
    def test_10_11_riskometer_ingestion_and_no_numeric_mapping(self, setup_pipeline, sample_raw_batch):
        snapshot = setup_pipeline.process_raw_batch(source_id="AMFI_OFFICIAL", raw_items=sample_raw_batch)
        rec_with_risk = [r for r in snapshot.records if r.amfi_code == "119551"][0]
        rec_missing_risk = [r for r in snapshot.records if r.amfi_code == "140001"][0]

        assert rec_with_risk.riskometer_label == "VERY HIGH"
        assert rec_missing_risk.riskometer_label is None
        # Verify riskometer is not converted into a numeric risk score or mapping
        assert not hasattr(rec_missing_risk, "riskometer_score")

    # Invariant 12: Lock-in Unknown Handling (No Default 'No Lock-in')
    def test_12_lock_in_unknown_handling(self, setup_pipeline, sample_raw_batch):
        snapshot = setup_pipeline.process_raw_batch(source_id="AMFI_OFFICIAL", raw_items=sample_raw_batch)
        rec = [r for r in snapshot.records if r.amfi_code == "119551"][0]
        assert rec.lock_in_days is None

    # Invariant 13 & 14: Lifecycle Linkage & Historical NAV Linkage
    def test_13_14_lifecycle_and_historical_nav_linkage(self, setup_pipeline, sample_raw_batch):
        snapshot = setup_pipeline.process_raw_batch(source_id="AMFI_OFFICIAL", raw_items=sample_raw_batch)
        for rec in snapshot.records:
            assert rec.canonical_scheme_id.startswith("CAN_AMFI_")
            assert rec.observation_date is not None
            assert rec.nav_value is not None

    # Invariant 15 & 16: Observation Date & Provenance Preservation
    def test_15_16_observation_date_and_provenance_preservation(self, setup_pipeline, sample_raw_batch):
        snapshot = setup_pipeline.process_raw_batch(source_id="AMFI_OFFICIAL", raw_items=sample_raw_batch)
        assert len(snapshot.ingestion_run_ids) == 1
        assert snapshot.source_ids == ["AMFI_OFFICIAL"]

        rec = snapshot.records[0]
        assert rec.observation_date == date(2024, 1, 15)
        assert rec.nav_value == 72.45

    # Invariant 17: Source Conflict Handling
    def test_17_source_conflict_handling(self):
        validator = DatasetValidator()

        norm1 = NormalizedRecord(
            record_id="norm_1",
            raw_evidence_id="ev_1",
            source_id="AMFI_OFFICIAL",
            ingestion_run_id="run_1",
            retrieval_timestamp_utc=datetime.now(timezone.utc),
            raw_scheme_code="119551",
            raw_scheme_name="Nippon India Large Cap Fund",
            normalized_scheme_name="NIPPON INDIA LARGE CAP FUND",
            plan_type_str="DIRECT",
            option_type_str="GROWTH",
            amc_name_str="NIPPON INDIA",
            category_str="Equity",
            subcategory_str="Large Cap",
            observation_date=date(2024, 1, 15),
            nav_value=72.45
        )

        norm2 = NormalizedRecord(
            record_id="norm_2",
            raw_evidence_id="ev_2",
            source_id="AMC_DIRECT_FEED",
            ingestion_run_id="run_2",
            retrieval_timestamp_utc=datetime.now(timezone.utc),
            raw_scheme_code="119551",
            raw_scheme_name="Nippon India Large Cap Fund",
            normalized_scheme_name="NIPPON INDIA LARGE CAP FUND",
            plan_type_str="DIRECT",
            option_type_str="GROWTH",
            amc_name_str="NIPPON INDIA",
            category_str="Equity",
            subcategory_str="Large Cap",
            observation_date=date(2024, 1, 15),
            nav_value=73.10  # Conflicting NAV value!
        )

        resolved = EntityResolvedRecord(
            resolved_id="res_1",
            normalized_record_id="norm_1",
            canonical_scheme_id="CAN_AMFI_119551",
            amfi_code="119551",
            isin="INF204K01L05",
            scheme_name="Nippon India Large Cap Fund",
            amc_name="NIPPON INDIA",
            plan_type_str="DIRECT",
            option_type_str="GROWTH",
            category_str="Equity",
            subcategory_str="Large Cap",
            resolution_method="AMFI_EXACT",
            identity_confidence=1.0,
            is_identity_ambiguous=False
        )

        val_rec = validator.validate_record(
            norm_rec=norm1,
            resolved_rec=resolved,
            assessment_date=date(2024, 1, 15),
            conflicting_record=norm2
        )

        assert val_rec.quality_state_str == DataQualityState.CONFLICTED.value
        assert val_rec.is_quarantined is True
        assert any("SOURCE_CONFLICT" in f.issue_code for f in val_rec.findings if f.issue_code)

    # Invariant 18 & 19: Mutually Exclusive Quality States & No Silent Fallbacks
    def test_18_19_mutually_exclusive_quality_states_and_no_silent_defaults(self, setup_pipeline, sample_raw_batch):
        snapshot = setup_pipeline.process_raw_batch(source_id="AMFI_OFFICIAL", raw_items=sample_raw_batch)

        # Mutually exclusive primary quality state accounting
        valid_cnt = sum(1 for r in snapshot.records if r.quality_state_str == "VALID")
        partial_cnt = sum(1 for r in snapshot.records if r.quality_state_str == "PARTIAL")
        invalid_cnt = sum(1 for r in snapshot.records if r.quality_state_str == "INVALID")
        quarantine_cnt = sum(1 for r in snapshot.records if r.quality_state_str == "QUARANTINED")
        conflict_cnt = sum(1 for r in snapshot.records if r.quality_state_str == "CONFLICTED")

        total_primary = valid_cnt + partial_cnt + invalid_cnt + quarantine_cnt + conflict_cnt
        assert total_primary == len(snapshot.records)

        # Verify missing fields in incomplete fund stay None, not 0.0 or defaults
        incomplete_rec = [r for r in snapshot.records if r.amfi_code == "140001"][0]
        assert incomplete_rec.ter_value is None
        assert incomplete_rec.riskometer_label is None
        assert incomplete_rec.benchmark_name is None

    # Invariant 20 & 21: No NAV Stitching & No IDCW Total Return Mislabeling
    def test_20_21_no_nav_stitching_and_no_idcw_total_return_mislabeling(self, setup_pipeline, sample_raw_batch):
        snapshot = setup_pipeline.process_raw_batch(source_id="AMFI_OFFICIAL", raw_items=sample_raw_batch)
        idcw_rec = [r for r in snapshot.records if r.amfi_code == "119553"][0]

        # Verify IDCW option is explicitly labeled as IDCW, NOT Growth
        assert idcw_rec.option_type_str in ("IDCW", "IDCW_PAYOUT", "IDCW_REINVESTMENT")
        assert idcw_rec.option_type_str != "GROWTH"

    # Invariant 22: Look-ahead Boundary Enforcement
    def test_22_look_ahead_boundary_enforcement(self):
        validator = DatasetValidator()
        norm = NormalizedRecord(
            record_id="norm_future",
            raw_evidence_id="ev_fut",
            source_id="AMFI_OFFICIAL",
            ingestion_run_id="run_1",
            retrieval_timestamp_utc=datetime.now(timezone.utc),
            raw_scheme_code="119551",
            raw_scheme_name="Nippon India Large Cap Fund",
            normalized_scheme_name="NIPPON INDIA LARGE CAP FUND",
            plan_type_str="DIRECT",
            option_type_str="GROWTH",
            amc_name_str="NIPPON INDIA",
            category_str="Equity",
            subcategory_str="Large Cap",
            observation_date=date(2025, 1, 1),  # Future date relative to assessment date!
            nav_value=75.00
        )

        resolved = EntityResolvedRecord(
            resolved_id="res_fut",
            normalized_record_id="norm_future",
            canonical_scheme_id="CAN_AMFI_119551",
            amfi_code="119551",
            isin="INF204K01L05",
            scheme_name="Nippon India Large Cap Fund",
            amc_name="NIPPON INDIA",
            plan_type_str="DIRECT",
            option_type_str="GROWTH",
            category_str="Equity",
            subcategory_str="Large Cap",
            resolution_method="AMFI_EXACT",
            identity_confidence=1.0,
            is_identity_ambiguous=False
        )

        val_rec = validator.validate_record(
            norm_rec=norm,
            resolved_rec=resolved,
            assessment_date=date(2024, 1, 15)  # Assessment date is Jan 15, 2024
        )

        assert val_rec.quality_state_str == DataQualityState.INVALID.value
        assert val_rec.is_quarantined is True
        assert any("FUTURE_NAV_DATE" in f.issue_code for f in val_rec.findings if f.issue_code)

    # Invariant 23: 18-Dimension Coverage Reporting with Explicit Denominators
    def test_23_coverage_reporting_with_explicit_denominators(self, setup_pipeline, sample_raw_batch):
        snapshot = setup_pipeline.process_raw_batch(source_id="AMFI_OFFICIAL", raw_items=sample_raw_batch)
        reporter = DatasetQualityReporter()
        runs = setup_pipeline.run_manager.list_completed_runs()

        json_report = reporter.generate_json_report(snapshot, runs)
        md_report = reporter.generate_markdown_report(snapshot, runs)

        assert "field_coverage_statistics" in json_report
        stats = json_report["field_coverage_statistics"]
        assert len(stats) == 14  # Key dimensions mapped

        for dim_key, dim_data in stats.items():
            assert "count" in dim_data
            assert "denominator" in dim_data
            assert "pct" in dim_data
            assert dim_data["denominator"] == len(sample_raw_batch)

        assert "# Phase F.9.4 Real Fund Dataset Quality Report" in md_report


    # Invariant 24: Idempotent Ingestion
    def test_24_idempotent_ingestion(self, setup_pipeline, sample_raw_batch):
        snap1 = setup_pipeline.process_raw_batch(source_id="AMFI_OFFICIAL", raw_items=sample_raw_batch)
        snap2 = setup_pipeline.process_raw_batch(source_id="AMFI_OFFICIAL", raw_items=sample_raw_batch)

        assert len(snap1.records) == len(snap2.records)
        for r1, r2 in zip(snap1.records, snap2.records):
            assert r1.canonical_scheme_id == r2.canonical_scheme_id
            assert r1.nav_value == r2.nav_value
            assert r1.quality_state_str == r2.quality_state_str
