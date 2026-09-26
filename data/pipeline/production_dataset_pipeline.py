"""
Production Dataset Pipeline (Phase F.9).

Orchestrates the complete 5-layer mutual-fund data pipeline:
- Layer A: Raw Source Evidence Preservation
- Layer B: Deterministic Field Normalization
- Layer C: Canonical Entity Resolution
- Layer D: Structural & Data Quality Validation
- Layer E: Versioned Dataset Snapshot Construction & Coverage Ledger Integration

Provides seamless integration to downstream FundQualityDatasetBuilder.
"""

from datetime import date, datetime, timezone
import hashlib
import uuid
from typing import List, Dict, Any, Optional, Tuple

from models.production_dataset import (
    RawSourceEvidence,
    NormalizedRecord,
    EntityResolvedRecord,
    ValidatedRecord,
    SchemeCoverageSnapshot,
    CoverageStatus,
    IngestionRunRecord,
    VersionedDatasetSnapshot
)
from models.fund_quality_dataset import (
    FundQualityDatasetInput,
    ProvenanceMetadata,
    CategoryPointInTimeContext,
    SchemeMetricSnapshot,
    PlanType,
    OptionType,
    FundMaturityTier
)
from data.ingestion.ingestion_run_manager import IngestionRunManager
from data.ingestion.source_registry import SourceRegistry
from data.normalization.dataset_normalizer import DatasetNormalizer
from data.mapping.entity_resolver import EntityResolver
from data.validation.dataset_validator import DatasetValidator
from data.builders.fund_quality_dataset_builder import FundQualityDatasetBuilder
from models.nav_data import DataQualityState


class ProductionDatasetPipeline:
    """End-to-End Production Mutual-Fund Dataset Pipeline."""

    DEFAULT_DATASET_VERSION = "F9.1.0"

    def __init__(
        self,
        source_registry: Optional[SourceRegistry] = None,
        run_manager: Optional[IngestionRunManager] = None,
        normalizer: Optional[DatasetNormalizer] = None,
        resolver: Optional[EntityResolver] = None,
        validator: Optional[DatasetValidator] = None,
        builder: Optional[FundQualityDatasetBuilder] = None
    ):
        self.source_registry = source_registry or SourceRegistry()
        self.run_manager = run_manager or IngestionRunManager()
        self.normalizer = normalizer or DatasetNormalizer()
        self.resolver = resolver or EntityResolver()
        self.validator = validator or DatasetValidator()
        self.builder = builder or FundQualityDatasetBuilder()

    def process_raw_batch(
        self,
        source_id: str,
        raw_items: List[Dict[str, Any]],
        dataset_version: str = DEFAULT_DATASET_VERSION,
        assessment_date: Optional[date] = None,
        source_endpoint_url: str = "https://www.amfiindia.com/net-asset-value"
    ) -> VersionedDatasetSnapshot:
        """
        Executes the 5-layer pipeline over a batch of raw source items and produces a VersionedDatasetSnapshot.
        """
        run_id = self.run_manager.start_run(source_id=source_id)
        now_utc = datetime.now(timezone.utc)

        raw_evidence_list: List[RawSourceEvidence] = []
        normalized_list: List[NormalizedRecord] = []
        resolved_list: List[EntityResolvedRecord] = []
        validated_list: List[ValidatedRecord] = []

        valid_cnt = 0
        partial_cnt = 0
        invalid_cnt = 0
        quarantine_cnt = 0
        conflict_cnt = 0

        # Process each raw record through Layers A, B, C, D
        for idx, item in enumerate(raw_items):
            payload_str = str(item)
            payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()
            evidence_id = f"ev_{source_id.lower()}_{idx}_{payload_hash[:8]}"

            # Layer A: Raw Source Evidence
            evidence = RawSourceEvidence(
                evidence_id=evidence_id,
                source_id=source_id,
                ingestion_run_id=run_id,
                retrieval_timestamp_utc=now_utc,
                source_endpoint_url=item.get("source_url", source_endpoint_url),
                raw_payload_text=payload_str,
                raw_payload_hash=payload_hash,
                publication_date=item.get("publication_date"),
                line_number=idx + 1
            )
            raw_evidence_list.append(evidence)

            # Layer B: Normalization
            norm_rec = self.normalizer.normalize_raw_evidence(
                evidence=evidence,
                raw_scheme_code=str(item.get("scheme_code", "")),
                raw_scheme_name=str(item.get("scheme_name", "")),
                raw_nav_str=str(item.get("nav", "")) if item.get("nav") is not None else "",
                raw_date_str=str(item.get("nav_date", "")) if item.get("nav_date") is not None else "",
                raw_category_str=item.get("category"),
                raw_subcategory_str=item.get("subcategory"),
                raw_amc_name_str=item.get("amc_name"),
                raw_ter_str=str(item.get("ter")) if item.get("ter") is not None else None,
                raw_ter_date_str=str(item.get("ter_date")) if item.get("ter_date") is not None else None,
                raw_exit_load_str=item.get("exit_load"),
                raw_riskometer_str=item.get("riskometer"),
                raw_benchmark_str=item.get("benchmark"),
                raw_isin_str=item.get("isin"),
                raw_plan_str=item.get("plan"),
                raw_option_str=item.get("option")
            )
            normalized_list.append(norm_rec)

            # Layer C: Entity Resolution
            resolved_rec = self.resolver.resolve_entity(norm_rec)
            resolved_list.append(resolved_rec)

            # Layer D: Validation
            val_rec = self.validator.validate_record(
                norm_rec=norm_rec,
                resolved_rec=resolved_rec,
                assessment_date=assessment_date
            )
            validated_list.append(val_rec)

            # Count metrics based on mutually exclusive primary quality state
            if val_rec.quality_state_str == DataQualityState.VALID.value:
                valid_cnt += 1
            elif val_rec.quality_state_str == DataQualityState.PARTIAL.value:
                partial_cnt += 1
            elif val_rec.quality_state_str == DataQualityState.INVALID.value:
                invalid_cnt += 1
            elif val_rec.quality_state_str == DataQualityState.CONFLICTED.value:
                conflict_cnt += 1
            elif val_rec.quality_state_str == DataQualityState.QUARANTINED.value:
                quarantine_cnt += 1

        # Complete Ingestion Run
        self.run_manager.record_metrics(
            run_id=run_id,
            total=len(raw_items),
            valid=valid_cnt,
            partial=partial_cnt,
            invalid=invalid_cnt,
            quarantined=quarantine_cnt,
            conflict=conflict_cnt
        )
        self.run_manager.complete_run(run_id=run_id, status="SUCCESS")

        # Update SourceRegistry retrieval status
        try:
            self.source_registry.update_retrieval_status(source_id=source_id, success=True, timestamp=now_utc)
        except ValueError:
            pass

        # Build Coverage Summaries per scheme
        coverage_summaries = self.build_coverage_summaries(validated_list)

        # Layer E: Versioned Dataset Snapshot Construction
        snapshot_id = f"snap_{dataset_version.replace('.', '_')}_{uuid.uuid4().hex[:8]}"
        is_eligible = (valid_cnt > 0) and (invalid_cnt == 0) and (quarantine_cnt == 0)

        snapshot = VersionedDatasetSnapshot(
            snapshot_id=snapshot_id,
            dataset_version=dataset_version,
            created_at_utc=now_utc,
            ingestion_run_ids=[run_id],
            source_ids=[source_id],
            methodology_version_refs={
                "pipeline_version": "F9.1.0",
                "quality_state_model": "F8.1.0",
                "entity_resolution_model": "F2.0.0"
            },
            total_schemes_count=len(coverage_summaries),
            valid_schemes_count=valid_cnt,
            quarantined_schemes_count=quarantine_cnt,
            records=validated_list,
            coverage_summaries=coverage_summaries,
            is_production_eligible=is_eligible,
            notes=f"Processed {len(raw_items)} records from {source_id} via 5-layer pipeline."
        )

        return snapshot

    def build_coverage_summaries(self, records: List[ValidatedRecord]) -> List[SchemeCoverageSnapshot]:
        """Group records by canonical scheme ID and compute historical NAV coverage summaries."""
        scheme_map: Dict[str, List[ValidatedRecord]] = {}
        for r in records:
            scheme_map.setdefault(r.canonical_scheme_id, []).append(r)

        summaries: List[SchemeCoverageSnapshot] = []
        for canonical_id, recs in scheme_map.items():
            valid_dates = [r.observation_date for r in recs if r.observation_date and r.nav_value is not None]
            valid_dates.sort()

            earliest = valid_dates[0] if valid_dates else None
            latest = valid_dates[-1] if valid_dates else None

            count = len(valid_dates)
            status = CoverageStatus.SUFFICIENT if count >= 36 else (CoverageStatus.PARTIAL if count > 0 else CoverageStatus.INSUFFICIENT)

            summaries.append(SchemeCoverageSnapshot(
                canonical_scheme_id=canonical_id,
                amfi_code=recs[0].amfi_code,
                scheme_name=recs[0].scheme_name,
                earliest_nav_date=earliest,
                latest_nav_date=latest,
                total_observation_count=count,
                requested_start_date=earliest,
                requested_end_date=latest,
                coverage_status=status
            ))

        return summaries

    def convert_to_fund_quality_dataset_input(
        self,
        val_record: ValidatedRecord,
        nav_history: List[Dict[str, Any]],
        source_document_url: str = "https://www.amfiindia.com/net-asset-value"
    ) -> FundQualityDatasetInput:
        """
        Converts a validated record (Layer D/E) into a FundQualityDatasetInput object
        via FundQualityDatasetBuilder without modifying scoring logic.
        """
        return self.builder.build_dataset_input_for_scheme(
            amfi_code=val_record.amfi_code,
            scheme_name=val_record.scheme_name,
            observation_date=val_record.observation_date,
            nav_history=nav_history,
            isin_growth=val_record.isin,
            source_id="AMFI_OFFICIAL",
            source_document_url=source_document_url,
            custom_ter_data={"ter_value": val_record.ter_value, "observation_date": val_record.ter_observation_date} if val_record.ter_value is not None else None,
            custom_category_data={"category": val_record.category_str, "subcategory": val_record.subcategory_str},
            override_canonical_id=val_record.canonical_scheme_id
        )
