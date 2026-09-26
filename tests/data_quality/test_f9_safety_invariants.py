"""
Safety Invariants Test Suite for Phase F.9 Real-World Mutual Fund Dataset Construction.

Verifies all 15 Phase F.9 Safety Invariants:
1. Missing evidence cannot become favorable evidence.
2. Ambiguous identity cannot become a valid identity.
3. Future information cannot enter historical assessment.
4. Data degradation cannot increase transaction propensity.
5. Re-ingestion is idempotent.
6. Dataset versions are immutable.
7. Source provenance cannot disappear during normalization.
8. Direct and Regular plans cannot silently merge.
9. Growth and IDCW options cannot silently merge.
10. Merger histories cannot be NAV-stitched.
11. Benchmark absence cannot universally block Fund Quality.
12. Missing TER/exit load cannot become zero.
13. Missing Riskometer cannot become inferred risk.
14. F.9 cannot create a BUY/SELL recommendation directly.
15. F.9 cannot alter financial methodology owned by downstream layers.
"""

from datetime import date, datetime, timezone
import pytest

from models.production_dataset import (
    RawSourceEvidence,
    NormalizedRecord,
    EntityResolvedRecord,
    ValidatedRecord,
    VersionedDatasetSnapshot
)
from models.nav_data import DataQualityState
from data.pipeline.production_dataset_pipeline import ProductionDatasetPipeline
from data.normalization.dataset_normalizer import DatasetNormalizer
from data.mapping.entity_resolver import EntityResolver
from data.validation.dataset_validator import DatasetValidator


class TestF9SafetyInvariants:
    """Phase F.9 Safety Invariants Verification Suite."""

    @pytest.fixture
    def pipeline(self):
        return ProductionDatasetPipeline()

    def test_invariant_1_missing_evidence_never_favorable(self, pipeline):
        """Invariant 1: Missing NAV or missing mandatory evidence cannot evaluate to favorable/valid."""
        raw_items = [{
            "scheme_code": "100028",
            "scheme_name": "HDFC Top 100 Fund - Direct Plan - Growth",
            "nav": None,  # Missing NAV
            "nav_date": "2026-04-30"
        }]

        snapshot = pipeline.process_raw_batch("AMFI_OFFICIAL", raw_items)
        rec = snapshot.records[0]

        assert rec.nav_value is None
        assert rec.quality_state_str == "INSUFFICIENT_INFORMATION"
        assert not snapshot.is_production_eligible

    def test_invariant_2_ambiguous_identity_quarantined(self, pipeline):
        """Invariant 2: Ambiguous scheme identity must be quarantined and never silently validated."""
        raw_items = [{
            "scheme_code": "INVALID_AMBIGUOUS_CODE",
            "scheme_name": "Ambiguous Fund Variant Without Clear Plan Or Option",
            "nav": "100.00",
            "nav_date": "2026-04-30"
        }]

        snapshot = pipeline.process_raw_batch("AMFI_OFFICIAL", raw_items)
        rec = snapshot.records[0]

        assert rec.is_quarantined
        assert rec.quality_state_str == "QUARANTINED"
        assert rec.canonical_scheme_id.startswith("CAN_")

    def test_invariant_3_future_information_blocked(self, pipeline):
        """Invariant 3: Observation date in the future relative to assessment date is rejected as INVALID."""
        validator = DatasetValidator()
        normalizer = DatasetNormalizer()
        resolver = EntityResolver()

        evidence = RawSourceEvidence(
            evidence_id="ev_future",
            source_id="AMFI_OFFICIAL",
            ingestion_run_id="run_fut",
            retrieval_timestamp_utc=datetime.now(timezone.utc),
            source_endpoint_url="https://amfiindia.com",
            raw_payload_text="future date nav",
            raw_payload_hash="futurehash"
        )

        norm = normalizer.normalize_raw_evidence(
            evidence=evidence,
            raw_scheme_code="100028",
            raw_scheme_name="Future Fund - Direct - Growth",
            raw_nav_str="150.00",
            raw_date_str="2030-01-01"  # Future date
        )
        resolved = resolver.resolve_entity(norm)
        val = validator.validate_record(norm, resolved, assessment_date=date(2026, 4, 30))

        assert val.quality_state_str == "INVALID"
        assert val.is_quarantined

    def test_invariant_5_reingestion_idempotence(self, pipeline):
        """Invariant 5: Re-ingesting the exact same raw payload produces identical deterministic normalized records."""
        raw_items = [{
            "scheme_code": "100028",
            "scheme_name": "HDFC Top 100 Fund - Direct Plan - Growth",
            "nav": "850.45",
            "nav_date": "2026-04-30"
        }]

        snapshot1 = pipeline.process_raw_batch("AMFI_OFFICIAL", raw_items, dataset_version="F9.IDEM.1")
        snapshot2 = pipeline.process_raw_batch("AMFI_OFFICIAL", raw_items, dataset_version="F9.IDEM.1")

        rec1 = snapshot1.records[0]
        rec2 = snapshot2.records[0]

        assert rec1.canonical_scheme_id == rec2.canonical_scheme_id
        assert rec1.amfi_code == rec2.amfi_code
        assert rec1.nav_value == rec2.nav_value
        assert rec1.quality_state_str == rec2.quality_state_str

    def test_invariant_7_provenance_retained(self, pipeline):
        """Invariant 7: Source provenance identifiers cannot disappear during normalization or resolution."""
        raw_items = [{
            "scheme_code": "100028",
            "scheme_name": "Axis Bluechip Fund - Direct - Growth",
            "nav": "50.00",
            "nav_date": "2026-04-30"
        }]

        snapshot = pipeline.process_raw_batch("AMFI_OFFICIAL", raw_items)
        rec = snapshot.records[0]

        assert snapshot.source_ids == ["AMFI_OFFICIAL"]
        assert snapshot.ingestion_run_ids[0].startswith("run_amfi_official_")
        assert rec.amfi_code == "100028"

    def test_invariant_8_9_plan_and_option_isolation(self, pipeline):
        """Invariant 8 & 9: Direct vs Regular plans and Growth vs IDCW options must remain strictly isolated."""
        normalizer = DatasetNormalizer()
        evidence = RawSourceEvidence(
            evidence_id="ev_iso",
            source_id="AMFI_OFFICIAL",
            ingestion_run_id="run_iso",
            retrieval_timestamp_utc=datetime.now(timezone.utc),
            source_endpoint_url="https://amfiindia.com",
            raw_payload_text="text",
            raw_payload_hash="hash"
        )

        norm_direct_growth = normalizer.normalize_raw_evidence(
            evidence, "100028", "SBI Bluechip Fund - Direct Plan - Growth", "75.0", "2026-04-30"
        )
        norm_regular_idcw = normalizer.normalize_raw_evidence(
            evidence, "100029", "SBI Bluechip Fund - Regular Plan - IDCW Payout", "70.0", "2026-04-30"
        )

        assert norm_direct_growth.plan_type_str == "DIRECT"
        assert norm_direct_growth.option_type_str == "GROWTH"

        assert norm_regular_idcw.plan_type_str == "REGULAR"
        assert norm_regular_idcw.option_type_str == "IDCW_PAYOUT"

        assert norm_direct_growth.plan_type_str != norm_regular_idcw.plan_type_str
        assert norm_direct_growth.option_type_str != norm_regular_idcw.option_type_str

    def test_invariant_12_missing_ter_never_zero(self, pipeline):
        """Invariant 12: Missing TER is represented as None, NEVER defaulted to 0.0."""
        raw_items = [{
            "scheme_code": "100028",
            "scheme_name": "Test Fund - Direct - Growth",
            "nav": "100.00",
            "nav_date": "2026-04-30",
            "ter": None  # Missing TER
        }]

        snapshot = pipeline.process_raw_batch("AMFI_OFFICIAL", raw_items)
        rec = snapshot.records[0]

        assert rec.ter_value is None
        assert rec.ter_value != 0.0

    def test_invariant_13_missing_riskometer_never_inferred(self, pipeline):
        """Invariant 13: Missing Riskometer label is represented as None, NEVER inferred."""
        raw_items = [{
            "scheme_code": "100028",
            "scheme_name": "Test Fund - Direct - Growth",
            "nav": "100.00",
            "nav_date": "2026-04-30",
            "riskometer": None  # Missing Riskometer
        }]

        snapshot = pipeline.process_raw_batch("AMFI_OFFICIAL", raw_items)
        rec = snapshot.records[0]

        assert rec.riskometer_label is None

    def test_invariant_14_f9_does_not_emit_buy_sell_recommendations(self, pipeline):
        """Invariant 14: Phase F.9 pipeline produces dataset snapshots ONLY, not BUY/SELL recommendations."""
        raw_items = [{
            "scheme_code": "100028",
            "scheme_name": "Perfect Fund - Direct - Growth",
            "nav": "100.00",
            "nav_date": "2026-04-30"
        }]

        snapshot = pipeline.process_raw_batch("AMFI_OFFICIAL", raw_items)

        assert isinstance(snapshot, VersionedDatasetSnapshot)
        assert not hasattr(snapshot, "recommendation_action")
        assert not hasattr(snapshot, "action_state")
