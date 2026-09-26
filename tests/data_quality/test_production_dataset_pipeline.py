"""
Unit and Integration Tests for Production Dataset Pipeline (Phase F.9).

Tests 5-layer pipeline execution:
- Layer A: Raw Source Evidence Preservation
- Layer B: Deterministic Field Normalization
- Layer C: Canonical Entity Resolution
- Layer D: Structural & Quality Validation
- Layer E: Versioned Dataset Snapshot & Ingestion Run Audit
- Downstream FundQualityDatasetBuilder integration
"""

from datetime import date, datetime, timezone
import pytest

from models.production_dataset import (
    RawSourceEvidence,
    NormalizedRecord,
    EntityResolvedRecord,
    ValidatedRecord,
    VersionedDatasetSnapshot,
    CoverageStatus
)
from models.nav_data import DataQualityState
from data.pipeline.production_dataset_pipeline import ProductionDatasetPipeline
from data.normalization.dataset_normalizer import DatasetNormalizer
from data.mapping.entity_resolver import EntityResolver
from data.validation.dataset_validator import DatasetValidator
from data.ingestion.ingestion_run_manager import IngestionRunManager


class TestProductionDatasetPipeline:
    """Test suite for Phase F.9 production data pipeline."""

    @pytest.fixture
    def pipeline(self):
        return ProductionDatasetPipeline()

    def test_layer_a_raw_evidence_preservation(self, pipeline):
        raw_items = [{
            "scheme_code": "100028",
            "scheme_name": "HDFC Top 100 Fund - Direct Plan - Growth",
            "nav": "850.45",
            "nav_date": "2026-04-30"
        }]

        snapshot = pipeline.process_raw_batch(
            source_id="AMFI_OFFICIAL",
            raw_items=raw_items,
            dataset_version="F9.TEST.1",
            assessment_date=date(2026, 4, 30)
        )

        assert snapshot.snapshot_id.startswith("snap_F9_TEST_1_")
        assert len(snapshot.records) == 1
        rec = snapshot.records[0]

        assert rec.amfi_code == "100028"
        assert rec.nav_value == 850.45
        assert rec.plan_type_str == "DIRECT"
        assert rec.option_type_str == "GROWTH"
        assert rec.quality_state_str == "VALID"
        assert not rec.is_quarantined

    def test_layer_b_deterministic_normalization(self, pipeline):
        normalizer = DatasetNormalizer()
        evidence = RawSourceEvidence(
            evidence_id="ev_test_1",
            source_id="AMFI_OFFICIAL",
            ingestion_run_id="run_123",
            retrieval_timestamp_utc=datetime.now(timezone.utc),
            source_endpoint_url="https://amfiindia.com",
            raw_payload_text="raw payload",
            raw_payload_hash="hash123"
        )

        norm = normalizer.normalize_raw_evidence(
            evidence=evidence,
            raw_scheme_code="100028",
            raw_scheme_name="SBI Bluechip Fund - Direct Plan - IDCW Reinvestment",
            raw_nav_str=" 75.1234 ",
            raw_date_str="30-Apr-2026",
            raw_ter_str=" 0.85 ",
            raw_riskometer_str="VERY HIGH"
        )

        assert norm.raw_scheme_code == "100028"
        assert norm.plan_type_str == "DIRECT"
        assert norm.option_type_str == "IDCW_REINVESTMENT"
        assert norm.observation_date == date(2026, 4, 30)
        assert norm.nav_value == 75.1234
        assert norm.ter_value == 0.85
        assert norm.riskometer_label == "VERY HIGH"

    def test_layer_c_entity_resolution_and_quarantine(self, pipeline):
        raw_items = [
            {
                "scheme_code": "100028",
                "scheme_name": "ICICI Prudential Bluechip Fund - Direct Plan - Growth",
                "nav": "100.50",
                "nav_date": "2026-04-30"
            },
            {
                "scheme_code": "UNMAPPED_CODE",
                "scheme_name": "Ambiguous Unknown Fund Name",
                "nav": "50.00",
                "nav_date": "2026-04-30"
            }
        ]

        snapshot = pipeline.process_raw_batch(
            source_id="AMFI_OFFICIAL",
            raw_items=raw_items,
            dataset_version="F9.TEST.2"
        )

        assert len(snapshot.records) == 2
        valid_rec = [r for r in snapshot.records if r.amfi_code == "100028"][0]
        quarantine_rec = [r for r in snapshot.records if r.amfi_code == "UNMAPPED_CODE"][0]

        assert valid_rec.quality_state_str == "VALID"
        assert not valid_rec.is_quarantined

        assert quarantine_rec.is_quarantined
        assert quarantine_rec.quality_state_str == "QUARANTINED"
        assert any("Identity resolution ambiguous" in reason for reason in quarantine_rec.quarantine_reasons)

    def test_layer_d_structural_and_range_bound_validation(self, pipeline):
        validator = DatasetValidator()
        normalizer = DatasetNormalizer()
        resolver = EntityResolver()

        evidence = RawSourceEvidence(
            evidence_id="ev_test_bad",
            source_id="AMFI_OFFICIAL",
            ingestion_run_id="run_bad",
            retrieval_timestamp_utc=datetime.now(timezone.utc),
            source_endpoint_url="https://amfiindia.com",
            raw_payload_text="bad nav payload",
            raw_payload_hash="badhash"
        )

        norm = normalizer.normalize_raw_evidence(
            evidence=evidence,
            raw_scheme_code="100028",
            raw_scheme_name="Test Bad Fund - Direct - Growth",
            raw_nav_str="-10.50",  # Invalid negative NAV
            raw_date_str="2026-04-30",
            raw_ter_str="150.0"   # TER > 100% invalid
        )
        resolved = resolver.resolve_entity(norm)
        val = validator.validate_record(norm, resolved, assessment_date=date(2026, 4, 30))

        assert val.quality_state_str == "INVALID"
        assert val.is_quarantined
        assert any("Non-positive NAV" in r for r in val.quarantine_reasons)

    def test_ingestion_run_manager_audit_logging(self):
        manager = IngestionRunManager()
        run_id = manager.start_run(source_id="AMFI_OFFICIAL", requested_date_range="2026-04-01:2026-04-30")

        manager.record_metrics(run_id=run_id, total=10, valid=8, invalid=1, quarantined=1)
        completed = manager.complete_run(run_id=run_id, status="SUCCESS")

        assert completed.run_id == run_id
        assert completed.source_id == "AMFI_OFFICIAL"
        assert completed.total_records_processed == 10
        assert completed.valid_record_count == 8
        assert completed.invalid_record_count == 1
        assert completed.quarantined_record_count == 1
        assert completed.retrieval_status == "SUCCESS"

    def test_downstream_fund_quality_dataset_builder_integration(self, pipeline):
        raw_items = [{
            "scheme_code": "100028",
            "scheme_name": "Nippon India Small Cap Fund - Direct Plan - Growth",
            "nav": "125.75",
            "nav_date": "2026-04-30",
            "ter": "0.72",
            "category": "EQUITY",
            "subcategory": "SMALL_CAP"
        }]

        snapshot = pipeline.process_raw_batch(
            source_id="AMFI_OFFICIAL",
            raw_items=raw_items,
            dataset_version="F9.TEST.3"
        )
        val_rec = snapshot.records[0]

        nav_history = [
            {"date": date(2026, 4, 30), "nav": 125.75},
            {"date": date(2025, 4, 30), "nav": 100.00},
            {"date": date(2024, 4, 30), "nav": 80.00},
            {"date": date(2023, 4, 30), "nav": 65.00},
        ]

        fq_input = pipeline.convert_to_fund_quality_dataset_input(
            val_record=val_rec,
            nav_history=nav_history
        )

        assert fq_input.amfi_code == "100028"
        assert fq_input.plan_type.value == "DIRECT"
        assert fq_input.option_type.value == "GROWTH"
        assert fq_input.category_context.category == "EQUITY"
        assert fq_input.category_context.subcategory == "SMALL_CAP"
        assert fq_input.metrics.total_expense_ratio == 0.72
        assert fq_input.provenance.source_id == "AMFI_OFFICIAL"
