"""
Production Dataset Models (Phase F.9).

Defines data models across the 5-layer ingestion pipeline:
- Layer A: RawSourceEvidence
- Layer B: NormalizedRecord
- Layer C: EntityResolvedRecord
- Layer D: ValidatedRecord & FieldValidationFinding
- Layer E: VersionedDatasetSnapshot, IngestionRunRecord, SchemeCoverageSnapshot

Governance Rules Enforced:
- Raw evidence is preserved immutably with raw string hash and retrieval timestamp.
- Normalization is deterministic and does not compute downstream financial metrics.
- Identity resolution maps to canonical scheme ID or flags ambiguity for quarantine.
- Data quality uses the formal 8-state model (VALID, PARTIAL, UNKNOWN, INSUFFICIENT_INFORMATION, INVALID, CONFLICTED, QUARANTINED, STALE).
- Dataset snapshots are immutable with dataset version ID, creation timestamp, run references, and constituent data versions.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional, Any


class CoverageStatus(Enum):
    """Historical coverage status for a canonical scheme."""
    SUFFICIENT = "SUFFICIENT"
    PARTIAL = "PARTIAL"
    INSUFFICIENT = "INSUFFICIENT"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class RawSourceEvidence:
    """
    Layer A: Immutably preserved raw source payload record.
    Preserves exact raw string, source ID, retrieval timestamp, endpoint, run ID, and raw hash.
    """
    evidence_id: str
    source_id: str
    ingestion_run_id: str
    retrieval_timestamp_utc: datetime
    source_endpoint_url: str
    raw_payload_text: str
    raw_payload_hash: str
    publication_date: Optional[date] = None
    source_version_ref: Optional[str] = None
    line_number: Optional[int] = None
    additional_headers: Optional[Dict[str, str]] = None


@dataclass(frozen=True)
class NormalizedRecord:
    """
    Layer B: Canonical internal representation of normalized data fields.
    Source linkage preserved; no financial score calculations.
    """
    record_id: str
    raw_evidence_id: str
    source_id: str
    ingestion_run_id: str
    retrieval_timestamp_utc: datetime
    raw_scheme_code: str
    raw_scheme_name: str
    normalized_scheme_name: str
    plan_type_str: str           # "DIRECT" | "REGULAR" | "UNKNOWN"
    option_type_str: str         # "GROWTH" | "IDCW_REINVESTMENT" | "IDCW_PAYOUT" | "UNKNOWN"
    amc_name_str: str
    category_str: str
    subcategory_str: str
    observation_date: date
    nav_value: Optional[float]
    ter_value: Optional[float] = None
    ter_observation_date: Optional[date] = None
    exit_load_text: Optional[str] = None
    riskometer_label: Optional[str] = None
    benchmark_name: Optional[str] = None
    benchmark_isin: Optional[str] = None
    isin_code: Optional[str] = None
    publication_date: Optional[date] = None
    lock_in_days: Optional[int] = None
    lifecycle_status_str: Optional[str] = "ACTIVE"
    launch_date: Optional[date] = None
    pit_category_context: Optional[str] = None


@dataclass(frozen=True)
class EntityResolvedRecord:
    """
    Layer C: Entity-resolved record linked to canonical scheme identity.
    Includes resolution method, identity confidence score, and quarantine flag if ambiguous.
    """
    resolved_id: str
    normalized_record_id: str
    canonical_scheme_id: str
    amfi_code: str
    isin: Optional[str]
    scheme_name: str
    amc_name: str
    plan_type_str: str
    option_type_str: str
    category_str: str
    subcategory_str: str
    resolution_method: str       # "AMFI_EXACT" | "ISIN_EXACT" | "ALIAS_MAP" | "UNRESOLVED_AMBIGUOUS"
    identity_confidence: float   # [0.0, 1.0]
    is_identity_ambiguous: bool
    quarantine_reason: Optional[str] = None


@dataclass(frozen=True)
class FieldValidationFinding:
    """Detailed validation finding for a specific data field."""
    field_name: str
    is_valid: bool
    quality_state: str           # DataQualityState value
    issue_code: Optional[str] = None
    issue_message: Optional[str] = None


@dataclass(frozen=True)
class ValidatedRecord:
    """
    Layer D: Structural and data-quality validated record.
    Carries final DataQualityState (VALID, PARTIAL, STALE, CONFLICTED, QUARANTINED, INVALID, etc.).
    """
    validated_record_id: str
    resolved_id: str
    canonical_scheme_id: str
    amfi_code: str
    isin: Optional[str]
    scheme_name: str
    amc_name: str
    plan_type_str: str
    option_type_str: str
    category_str: str
    subcategory_str: str
    observation_date: date
    nav_value: Optional[float]
    ter_value: Optional[float]
    ter_observation_date: Optional[date]
    exit_load_text: Optional[str]
    riskometer_label: Optional[str]
    benchmark_name: Optional[str]
    publication_date: Optional[date]
    quality_state_str: str       # "VALID" | "PARTIAL" | "STALE" | "CONFLICTED" | "QUARANTINED" | "INVALID" | "UNKNOWN" | "INSUFFICIENT_INFORMATION"
    is_stale: bool
    is_quarantined: bool
    quarantine_reasons: List[str] = field(default_factory=list)
    findings: List[FieldValidationFinding] = field(default_factory=list)
    lock_in_days: Optional[int] = None
    lifecycle_status_str: Optional[str] = "ACTIVE"
    launch_date: Optional[date] = None
    pit_category_context: Optional[str] = None



@dataclass(frozen=True)
class SchemeCoverageSnapshot:
    """
    Historical coverage summary for a specific canonical scheme within a dataset version.
    """
    canonical_scheme_id: str
    amfi_code: str
    scheme_name: str
    earliest_nav_date: Optional[date]
    latest_nav_date: Optional[date]
    total_observation_count: int
    requested_start_date: Optional[date]
    requested_end_date: Optional[date]
    coverage_status: CoverageStatus
    detectable_gap_count: int = 0
    max_gap_days: int = 0


@dataclass(frozen=True)
class IngestionRunRecord:
    """
    Audit record of an ingestion run execution.
    """
    run_id: str
    source_id: str
    start_time_utc: datetime
    end_time_utc: datetime
    requested_date_range: Optional[str]
    retrieval_status: str       # "SUCCESS" | "PARTIAL" | "FAILED" | "RETRY_REQUIRED"
    total_records_processed: int
    valid_record_count: int
    partial_record_count: int
    invalid_record_count: int
    quarantined_record_count: int
    conflict_record_count: int
    error_log: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class VersionedDatasetSnapshot:
    """
    Layer E: Immutable, versioned snapshot container of validated real-world mutual fund data.
    Captures constituent records, run metadata, coverage summaries, and reproducibility parameters.
    """
    snapshot_id: str
    dataset_version: str
    created_at_utc: datetime
    ingestion_run_ids: List[str]
    source_ids: List[str]
    methodology_version_refs: Dict[str, str]
    total_schemes_count: int
    valid_schemes_count: int
    quarantined_schemes_count: int
    records: List[ValidatedRecord] = field(default_factory=list)
    coverage_summaries: List[SchemeCoverageSnapshot] = field(default_factory=list)
    is_production_eligible: bool = False  # False until fully validated
    notes: Optional[str] = None
