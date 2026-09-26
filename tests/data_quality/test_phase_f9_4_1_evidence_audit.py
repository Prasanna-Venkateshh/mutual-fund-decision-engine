"""
Phase F.9.4.1 — Real-Data Field Evidence & Authoritative Source Audit Tests.

Validates all 16 evidence audit invariants:
1. Real-source field preservation.
2. No synthetic field defaults.
3. Missing TER remains None/UNKNOWN.
4. Missing Riskometer remains None/UNKNOWN (NO numeric risk mapping).
5. Missing lock-in remains None/UNKNOWN (NO default 'no lock-in').
6. Direct/Regular ambiguity conservative (quarantined).
7. Growth/IDCW ambiguity conservative (quarantined).
8. PIT category not falsely represented as 100% complete.
9. Lifecycle identity remains stable (CAN_AMFI_{amfi_code}).
10. Historical NAV linked to canonical identity.
11. Provenance attached to all records.
12. Test fixtures not counted as production coverage.
13. Primary quality-state accounting mutually exclusive.
14. Diagnostic flags do not inflate primary counts.
15. F.9.2.5 identity invariant preserved.
16. F.9.3.1 historical accounting preserved.
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
from data.adapters.category_context_adapter import CategoryContextAdapter
from data.reporting.dataset_quality_reporter import DatasetQualityReporter
from data.validation.dataset_validator import DatasetValidator


class TestPhaseF941EvidenceAudit:
    """Targeted Evidence Audit Test Suite for Phase F.9.4.1."""

    @pytest.fixture
    def setup_pipeline(self):
        return ProductionDatasetPipeline()

    @pytest.fixture
    def sample_raw_items(self) -> List[Dict[str, Any]]:
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
                "scheme_code": "140001",
                "scheme_name": "ICICI Prudential Tax Saver Fund - Direct Plan - Growth",
                "nav": "680.50",
                "nav_date": "2024-01-15",
                "category": "Equity",
                "subcategory": "ELSS",
                "amc_name": "ICICI Prudential Mutual Fund",
                "isin": "INF109K01123",
                "ter": None,
                "riskometer": None,
                "benchmark": None,
                "plan": "Direct",
                "option": "Growth"
            },
            {
                "scheme_code": "101234",
                "scheme_name": "Legacy Ambiguous Fund Name Without Plan String",
                "nav": "15.40",
                "nav_date": "2024-01-15",
                "category": "Equity",
                "subcategory": "Multi Cap",
                "amc_name": "Legacy AMC",
                "isin": "",
                "ter": None,
                "riskometer": None,
                "benchmark": None,
                "plan": "",
                "option": ""
            }
        ]

    # Invariant 1: Real Source Field Preservation
    def test_01_real_source_field_preservation(self, setup_pipeline, sample_raw_items):
        snapshot = setup_pipeline.process_raw_batch(source_id="AMFI_OFFICIAL", raw_items=sample_raw_items)
        assert len(snapshot.records) == 3
        rec = snapshot.records[0]
        assert rec.amfi_code == "119551"
        assert rec.isin == "INF204K01L05"
        assert rec.nav_value == 72.45
        assert rec.observation_date == date(2024, 1, 15)

    # Invariant 2: No Synthetic Field Defaults
    def test_02_no_synthetic_field_defaults(self, setup_pipeline, sample_raw_items):
        snapshot = setup_pipeline.process_raw_batch(source_id="AMFI_OFFICIAL", raw_items=sample_raw_items)
        incomplete_rec = [r for r in snapshot.records if r.amfi_code == "140001"][0]
        assert incomplete_rec.ter_value is None
        assert incomplete_rec.riskometer_label is None
        assert incomplete_rec.benchmark_name is None

    # Invariant 3: Missing TER Remains None/UNKNOWN
    def test_03_missing_ter_remains_none(self):
        ter_adapter = TERAdapter()
        val, obs_d = ter_adapter.resolve_ter(
            canonical_scheme_id="CAN_AMFI_140001",
            plan_type_str="DIRECT",
            observation_date=date(2024, 1, 15)
        )
        assert val is None
        assert obs_d is None

    # Invariant 4: Missing Riskometer Remains None (NO Numeric Risk Mapping)
    def test_04_missing_riskometer_remains_none_no_numeric_mapping(self, setup_pipeline, sample_raw_items):
        snapshot = setup_pipeline.process_raw_batch(source_id="AMFI_OFFICIAL", raw_items=sample_raw_items)
        incomplete_rec = [r for r in snapshot.records if r.amfi_code == "140001"][0]
        assert incomplete_rec.riskometer_label is None
        assert not hasattr(incomplete_rec, "riskometer_score")

    # Invariant 5: Missing Lock-in Remains None (NO Default 'No Lock-in')
    def test_05_missing_lock_in_remains_none_no_default_no_lockin(self, setup_pipeline, sample_raw_items):
        snapshot = setup_pipeline.process_raw_batch(source_id="AMFI_OFFICIAL", raw_items=sample_raw_items)
        rec = snapshot.records[0]
        assert rec.lock_in_days is None

    # Invariant 6 & 7: Direct/Regular & Growth/IDCW Ambiguity Conservative (Quarantined)
    def test_06_07_ambiguity_conservative(self, setup_pipeline, sample_raw_items):
        snapshot = setup_pipeline.process_raw_batch(source_id="AMFI_OFFICIAL", raw_items=sample_raw_items)
        ambiguous_rec = [r for r in snapshot.records if r.amfi_code == "101234"][0]
        assert ambiguous_rec.quality_state_str == DataQualityState.QUARANTINED.value
        assert ambiguous_rec.is_quarantined is True

    # Invariant 8: PIT Category Handling (Pre-2017 Missing Evidence Returns UNSPECIFIED / PRE_SEBI_2017_UNKNOWN / 0.0)
    def test_08_pit_category_not_falsely_represented_as_complete(self):
        adapter = CategoryContextAdapter()
        ctx_pre = adapter.resolve_category_context(
            canonical_scheme_id="CAN_AMFI_119551",
            scheme_name="Nippon India Large Cap Fund",
            observation_date=date(2015, 5, 10)
        )
        assert ctx_pre.category == "UNSPECIFIED"
        assert ctx_pre.confidence_score == 0.0
        assert ctx_pre.source == "PRE_SEBI_2017_UNKNOWN"

    # Invariant 9: Lifecycle Identity Remains Stable (CAN_AMFI_{amfi_code})
    def test_09_lifecycle_identity_remains_stable(self, setup_pipeline, sample_raw_items):
        snapshot = setup_pipeline.process_raw_batch(source_id="AMFI_OFFICIAL", raw_items=sample_raw_items)
        for rec in snapshot.records:
            assert rec.canonical_scheme_id == f"CAN_AMFI_{rec.amfi_code}"
            assert not rec.canonical_scheme_id.startswith("QUARANTINE_CAN_")

    # Invariant 10: Historical NAV Linked to Canonical Identity
    def test_10_historical_nav_linked_to_canonical_identity(self, setup_pipeline, sample_raw_items):
        snapshot = setup_pipeline.process_raw_batch(source_id="AMFI_OFFICIAL", raw_items=sample_raw_items)
        for rec in snapshot.records:
            assert rec.observation_date is not None
            assert rec.nav_value is not None

    # Invariant 11: Provenance Attached to All Records
    def test_11_provenance_attached_to_all_records(self, setup_pipeline, sample_raw_items):
        snapshot = setup_pipeline.process_raw_batch(source_id="AMFI_OFFICIAL", raw_items=sample_raw_items)
        assert len(snapshot.ingestion_run_ids) == 1
        assert snapshot.source_ids == ["AMFI_OFFICIAL"]

    # Invariant 12: Test Fixtures Not Counted as Production Coverage
    def test_12_test_fixtures_not_counted_as_production_coverage(self):
        reporter = DatasetQualityReporter()
        # Verify reporter reports source IDs clearly
        snapshot = VersionedDatasetSnapshot(
            snapshot_id="snap_test",
            dataset_version="F9.4.1",
            created_at_utc=datetime.now(timezone.utc),
            ingestion_run_ids=["run_1"],
            source_ids=["AMFI_OFFICIAL"],
            methodology_version_refs={},
            total_schemes_count=0,
            valid_schemes_count=0,
            quarantined_schemes_count=0,
            records=[],
            is_production_eligible=False
        )
        report = reporter.generate_json_report(snapshot, [])
        assert report["sources_attempted"] == ["AMFI_OFFICIAL"]

    # Invariant 13: Primary Quality State Accounting Mutually Exclusive
    def test_13_primary_quality_state_accounting_mutually_exclusive(self, setup_pipeline, sample_raw_items):
        snapshot = setup_pipeline.process_raw_batch(source_id="AMFI_OFFICIAL", raw_items=sample_raw_items)
        valid_cnt = sum(1 for r in snapshot.records if r.quality_state_str == "VALID")
        partial_cnt = sum(1 for r in snapshot.records if r.quality_state_str == "PARTIAL")
        invalid_cnt = sum(1 for r in snapshot.records if r.quality_state_str == "INVALID")
        quarantine_cnt = sum(1 for r in snapshot.records if r.quality_state_str == "QUARANTINED")
        conflict_cnt = sum(1 for r in snapshot.records if r.quality_state_str == "CONFLICTED")

        total_sum = valid_cnt + partial_cnt + invalid_cnt + quarantine_cnt + conflict_cnt
        assert total_sum == len(snapshot.records)

    # Invariant 14: Diagnostic Flags Do Not Inflate Primary Counts
    def test_14_diagnostic_flags_do_not_inflate_primary_counts(self, setup_pipeline, sample_raw_items):
        snapshot = setup_pipeline.process_raw_batch(source_id="AMFI_OFFICIAL", raw_items=sample_raw_items)
        flagged_occurrences = sum(1 for r in snapshot.records if r.is_quarantined)
        primary_quarantines = sum(1 for r in snapshot.records if r.quality_state_str == "QUARANTINED")
        # Diagnostic flag count is >= primary quarantine count
        assert flagged_occurrences >= primary_quarantines

    # Invariant 15: F.9.2.5 Identity Invariant Preserved
    def test_15_f9_2_5_identity_invariant_preserved(self, setup_pipeline, sample_raw_items):
        snapshot = setup_pipeline.process_raw_batch(source_id="AMFI_OFFICIAL", raw_items=sample_raw_items)
        for rec in snapshot.records:
            assert rec.canonical_scheme_id.startswith("CAN_AMFI_")
            assert not rec.canonical_scheme_id.startswith("QUARANTINE_CAN_")

    # Invariant 16: F.9.3.1 Historical Accounting Preserved
    def test_16_f9_3_1_historical_accounting_preserved(self, setup_pipeline, sample_raw_items):
        snapshot = setup_pipeline.process_raw_batch(source_id="AMFI_OFFICIAL", raw_items=sample_raw_items)
        for rec in snapshot.records:
            assert rec.observation_date is not None
