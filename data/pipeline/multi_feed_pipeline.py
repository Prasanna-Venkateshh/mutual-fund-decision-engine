"""
Multi-Feed Production Dataset Pipeline & Orchestrator (Phase F.10).

Orchestrates multi-source Mutual Fund data ingestion, canonical identity resolution,
field-specific normalization, validation, deterministic multi-feed merging,
conflict resolution, and immutable versioned snapshot generation.
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
    VersionedDatasetSnapshot,
    SchemeCoverageSnapshot,
    CoverageStatus,
    IngestionRunRecord
)
from models.nav_data import DataQualityState
from data.ingestion.source_registry import SourceRegistry
from data.ingestion.ingestion_run_manager import IngestionRunManager
from data.ingestion.ter_feed_adapter import TERFeedAdapter
from data.ingestion.riskometer_feed_adapter import RiskometerFeedAdapter
from data.ingestion.benchmark_feed_adapter import BenchmarkFeedAdapter
from data.ingestion.scheme_master_adapter import SchemeMasterFeedAdapter
from data.normalization.dataset_normalizer import DatasetNormalizer
from data.mapping.entity_resolver import EntityResolver
from data.validation.dataset_validator import DatasetValidator


class MultiFeedDatasetPipeline:
    """
    Multi-Feed Dataset Pipeline & Orchestrator for Phase F.10.
    Incoorporates multi-feed merging for NAV, Scheme Master, TER, Riskometer, and Benchmark feeds.
    """

    DEFAULT_DATASET_VERSION = "F10.0.0"

    def __init__(
        self,
        source_registry: Optional[SourceRegistry] = None,
        run_manager: Optional[IngestionRunManager] = None,
        normalizer: Optional[DatasetNormalizer] = None,
        resolver: Optional[EntityResolver] = None,
        validator: Optional[DatasetValidator] = None
    ):
        self.source_registry = source_registry or SourceRegistry()
        self.run_manager = run_manager or IngestionRunManager()
        self.normalizer = normalizer or DatasetNormalizer()
        self.resolver = resolver or EntityResolver()
        self.validator = validator or DatasetValidator()

        self.ter_adapter = TERFeedAdapter()
        self.riskometer_adapter = RiskometerFeedAdapter()
        self.benchmark_adapter = BenchmarkFeedAdapter()
        self.scheme_master_adapter = SchemeMasterFeedAdapter()

    def process_multi_feed_batch(
        self,
        nav_raw_items: List[Dict[str, Any]],
        ter_raw_items: Optional[List[Dict[str, Any]]] = None,
        riskometer_raw_items: Optional[List[Dict[str, Any]]] = None,
        benchmark_raw_items: Optional[List[Dict[str, Any]]] = None,
        scheme_master_raw_items: Optional[List[Dict[str, Any]]] = None,
        dataset_version: str = DEFAULT_DATASET_VERSION,
        assessment_date: Optional[date] = None
    ) -> Tuple[VersionedDatasetSnapshot, Dict[str, Any]]:
        """
        Executes multi-feed ingestion, deterministic field-level merging, validation,
        and snapshot construction.
        """
        now_utc = datetime.now(timezone.utc)
        run_id = self.run_manager.start_run(source_id="MULTI_FEED_ORCHESTRATOR")

        # 1. Parse Metadata Feeds into identity-indexed maps
        ter_map = self.ter_adapter.parse_ter_feed_items(ter_raw_items or [])
        risk_map = self.riskometer_adapter.parse_riskometer_feed_items(riskometer_raw_items or [])
        bm_map = self.benchmark_adapter.parse_benchmark_feed_items(benchmark_raw_items or [])
        master_map = self.scheme_master_adapter.parse_scheme_master_items(scheme_master_raw_items or [])

        active_source_ids = ["AMFI_OFFICIAL"]
        if ter_raw_items:
            active_source_ids.append("AMFI_TER_FEED")
        if riskometer_raw_items:
            active_source_ids.append("AMFI_RISKOMETER_FEED")
        if benchmark_raw_items:
            active_source_ids.append("AMFI_BENCHMARK_FEED")
        if scheme_master_raw_items:
            active_source_ids.append("AMFI_SCHEME_MASTER")

        raw_evidence_list: List[RawSourceEvidence] = []
        validated_list: List[ValidatedRecord] = []
        conflict_ledger: List[Dict[str, Any]] = []
        unmapped_metadata_count = 0

        valid_cnt = 0
        partial_cnt = 0
        invalid_cnt = 0
        quarantine_cnt = 0
        conflict_cnt = 0

        # Track merged AMFI scheme codes
        processed_scheme_codes = set()

        for idx, item in enumerate(nav_raw_items):
            scheme_code = str(item.get("scheme_code", "")).strip()
            processed_scheme_codes.add(scheme_code)

            payload_str = str(item)
            payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()
            evidence_id = f"ev_nav_{idx}_{payload_hash[:8]}"

            # Layer A: Raw Evidence for NAV line
            evidence = RawSourceEvidence(
                evidence_id=evidence_id,
                source_id="AMFI_OFFICIAL",
                ingestion_run_id=run_id,
                retrieval_timestamp_utc=now_utc,
                source_endpoint_url=item.get("source_url", "https://www.amfiindia.com/spages/NAVAll.txt"),
                raw_payload_text=payload_str,
                raw_payload_hash=payload_hash,
                publication_date=item.get("publication_date"),
                line_number=idx + 1
            )
            raw_evidence_list.append(evidence)

            # Determine merged TER, Riskometer, Benchmark, Category from Multi-Feeds
            master_info = master_map.get(scheme_code, {})
            ter_info = ter_map.get(scheme_code, {})
            risk_info = risk_map.get(scheme_code, {})
            bm_info = bm_map.get(scheme_code, {})

            # TER Merge with Conflict Resolution
            merged_ter = item.get("ter")
            merged_ter_date = item.get("ter_date")
            if merged_ter is None:
                if ter_info.get("ter_value") is not None:
                    merged_ter = ter_info.get("ter_value")
                    merged_ter_date = ter_info.get("ter_observation_date")
                elif master_info.get("ter_value") is not None:
                    merged_ter = master_info.get("ter_value")

            # Riskometer Merge
            merged_risk = item.get("riskometer")
            if merged_risk is None:
                if risk_info.get("riskometer_label") is not None:
                    merged_risk = risk_info.get("riskometer_label")
                elif master_info.get("riskometer_label") is not None:
                    merged_risk = master_info.get("riskometer_label")

            # Benchmark Merge
            merged_bm = item.get("benchmark")
            if merged_bm is None:
                if bm_info.get("benchmark_name") is not None:
                    merged_bm = bm_info.get("benchmark_name")
                elif master_info.get("benchmark_name") is not None:
                    merged_bm = master_info.get("benchmark_name")

            # Category Merge
            merged_cat = item.get("category") or master_info.get("category")
            merged_subcat = item.get("subcategory") or master_info.get("subcategory")
            merged_amc = item.get("amc_name") or master_info.get("amc_name")

            # Layer B: Normalization
            norm_rec = self.normalizer.normalize_raw_evidence(
                evidence=evidence,
                raw_scheme_code=scheme_code,
                raw_scheme_name=str(item.get("scheme_name", "")),
                raw_nav_str=str(item.get("nav", "")) if item.get("nav") is not None else "",
                raw_date_str=str(item.get("nav_date", "")) if item.get("nav_date") is not None else "",
                raw_category_str=merged_cat,
                raw_subcategory_str=merged_subcat,
                raw_amc_name_str=merged_amc,
                raw_ter_str=str(merged_ter) if merged_ter is not None else None,
                raw_ter_date_str=str(merged_ter_date) if merged_ter_date is not None else None,
                raw_exit_load_str=item.get("exit_load"),
                raw_riskometer_str=merged_risk,
                raw_benchmark_str=merged_bm,
                raw_isin_str=item.get("isin") or master_info.get("isin_growth"),
                raw_plan_str=item.get("plan"),
                raw_option_str=item.get("option")
            )

            # Layer C: Canonical Identity Resolution
            resolved_rec = self.resolver.resolve_entity(norm_rec)

            # Layer D: Validation
            val_rec = self.validator.validate_record(
                norm_rec=norm_rec,
                resolved_rec=resolved_rec,
                assessment_date=assessment_date
            )
            validated_list.append(val_rec)

            # Primary Quality State Count
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

        # Count unmapped metadata feed items (records in metadata feeds lacking matching scheme code in NAV feed)
        metadata_scheme_codes = set(ter_map.keys()) | set(risk_map.keys()) | set(bm_map.keys()) | set(master_map.keys())
        unmapped_scheme_codes = metadata_scheme_codes - processed_scheme_codes
        unmapped_metadata_count = len(unmapped_scheme_codes)

        # Complete Ingestion Run
        self.run_manager.record_metrics(
            run_id=run_id,
            total=len(nav_raw_items),
            valid=valid_cnt,
            partial=partial_cnt,
            invalid=invalid_cnt,
            quarantined=quarantine_cnt,
            conflict=conflict_cnt
        )
        self.run_manager.complete_run(run_id=run_id, status="SUCCESS")

        # Layer E: Versioned Dataset Snapshot Construction
        snapshot_id = f"snap_mf_{dataset_version.replace('.', '_')}_{uuid.uuid4().hex[:8]}"
        is_eligible = (valid_cnt > 0) and (invalid_cnt == 0) and (quarantine_cnt == 0)

        snapshot = VersionedDatasetSnapshot(
            snapshot_id=snapshot_id,
            dataset_version=dataset_version,
            created_at_utc=now_utc,
            ingestion_run_ids=[run_id],
            source_ids=active_source_ids,
            methodology_version_refs={
                "pipeline_version": "F10.0.0",
                "quality_state_model": "F8.1.0",
                "entity_resolution_model": "F2.0.0"
            },
            total_schemes_count=len(validated_list),
            valid_schemes_count=valid_cnt,
            quarantined_schemes_count=quarantine_cnt,
            records=validated_list,
            coverage_summaries=[],
            is_production_eligible=is_eligible,
            notes=f"Processed multi-feed batch ({len(active_source_ids)} active feeds). Unmapped metadata count: {unmapped_metadata_count}."
        )

        quality_report = self.generate_quality_report(snapshot, unmapped_metadata_count, conflict_ledger)
        return snapshot, quality_report

    def generate_quality_report(
        self,
        snapshot: VersionedDatasetSnapshot,
        unmapped_metadata_count: int,
        conflict_ledger: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generates machine-readable multi-feed dataset quality report."""
        total = snapshot.total_schemes_count
        ter_populated = sum(1 for r in snapshot.records if r.ter_value is not None)
        risk_populated = sum(1 for r in snapshot.records if r.riskometer_label is not None)
        bm_populated = sum(1 for r in snapshot.records if r.benchmark_name is not None)

        valid_recs = [r for r in snapshot.records if r.quality_state_str == DataQualityState.VALID.value]
        valid_cnt = len(valid_recs)

        ter_valid_pop = sum(1 for r in valid_recs if r.ter_value is not None)
        risk_valid_pop = sum(1 for r in valid_recs if r.riskometer_label is not None)
        bm_valid_pop = sum(1 for r in valid_recs if r.benchmark_name is not None)

        return {
            "snapshot_id": snapshot.snapshot_id,
            "dataset_version": snapshot.dataset_version,
            "created_at_utc": snapshot.created_at_utc.isoformat(),
            "source_ids": snapshot.source_ids,
            "total_records": total,
            "valid_records": valid_cnt,
            "quarantined_records": snapshot.quarantined_schemes_count,
            "invalid_records": total - valid_cnt - snapshot.quarantined_schemes_count,
            "ter_populated_total": ter_populated,
            "ter_coverage_total_pct": round(ter_populated / max(1, total) * 100, 2),
            "ter_coverage_valid_pct": round(ter_valid_pop / max(1, valid_cnt) * 100, 2),
            "riskometer_populated_total": risk_populated,
            "riskometer_coverage_total_pct": round(risk_populated / max(1, total) * 100, 2),
            "riskometer_coverage_valid_pct": round(risk_valid_pop / max(1, valid_cnt) * 100, 2),
            "benchmark_populated_total": bm_populated,
            "benchmark_coverage_total_pct": round(bm_populated / max(1, total) * 100, 2),
            "benchmark_coverage_valid_pct": round(bm_valid_pop / max(1, valid_cnt) * 100, 2),
            "unmapped_metadata_count": unmapped_metadata_count,
            "conflict_count": len(conflict_ledger)
        }
