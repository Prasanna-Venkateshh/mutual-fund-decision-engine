"""
Lifecycle Ingestion Pipeline — Phase D: Controlled Seed Data Ingestion.

Implements the production-grade, 6-stage lifecycle ingestion foundation required
to populate auditable historical lifecycle events.

Pipeline Architecture:
1. Document Retrieval & Raw Metadata Capture
2. Text Extraction & Candidate Event Parsing
3. Normalization (Effective Date Precision MD-1, Event Types)
4. Identity Resolution (Canonical Scheme ID mapping)
5. AMFI Empirical Corroboration (NAV boundaries & consistency check)
6. Confidence Evaluation, Quarantine & Provenance Persistence

Governing Documents:
- ARCHITECTURE.md §4 (data/ingestion/ boundary), §11 (Audit Provenance)
- PRODUCT_SPEC.md §24 (Evidence Layer), §25 (Data Architecture)
- DECISION_RULES.md §12.18.2 (Bias Prevention Safeguards)
- config/lifecycle/lifecycle_config.yaml
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import List, Optional, Dict, Any, Tuple

from models.scheme_lifecycle import (
    LifecycleEvent,
    LifecycleEventType,
    LifecycleConfidence,
    EffectiveDatePrecision,
    ExistenceStatus,
)
from data.repositories.lifecycle_repository import LifecycleRepository
from db.database import DatabaseConnection


# ---------------------------------------------------------------------------
# Data Containers
# ---------------------------------------------------------------------------

@dataclass
class RawLifecycleDocument:
    """
    Stage 1 Container: Authoritative source document and metadata.
    Preserves exact provenance attributes before extraction.
    """
    document_id: str
    source_id: str
    source_document_url: Optional[str]
    retrieval_timestamp_utc: datetime
    raw_content: str
    document_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CandidateLifecycleEvent:
    """
    Stage 2 Container: Candidate event extracted from raw document text.
    Captures raw unstructured facts before normalization.
    """
    source_document_id: str
    raw_scheme_name: Optional[str] = None
    raw_predecessor_name: Optional[str] = None
    raw_successor_name: Optional[str] = None
    raw_amfi_code: Optional[str] = None
    raw_isin: Optional[str] = None
    event_type_str: str = ""
    effective_date_str: str = ""
    effective_date_precision_str: str = "DAY"  # DAY, MONTH, YEAR
    source_document_fact: str = ""  # Exact claim from document
    notes: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None


@dataclass
class AmfiCorroborationResult:
    """
    Stage 5 Container: Results of empirical AMFI NAV history boundary check.
    """
    first_observed_nav_date: Optional[date] = None
    last_observed_nav_date: Optional[date] = None
    boundary_consistent: bool = True
    discrepancy_detected: bool = False
    empirical_observation_summary: str = "No empirical NAV discrepancy detected."
    discrepancy_notes: Optional[str] = None


# ---------------------------------------------------------------------------
# AMFI Empirical Corroborator Helper
# ---------------------------------------------------------------------------

class AmfiCorroborator:
    """
    Queries AMFI empirical NAV observations to corroborate lifecycle event boundaries.
    Does NOT modify legal lifecycle event types or force Day precision on Month/Year events.
    """

    def __init__(self, db: DatabaseConnection):
        self.db = db

    def corroborate_event(
        self,
        amfi_code: Optional[str],
        event_type: LifecycleEventType,
        effective_date: date,
        effective_date_precision: EffectiveDatePrecision,
    ) -> AmfiCorroborationResult:
        """
        Check raw_nav_observations for scheme boundary dates.
        """
        if not amfi_code:
            return AmfiCorroborationResult(
                boundary_consistent=True,
                empirical_observation_summary="AMFI Code unavailable for empirical NAV check.",
            )

        with self.db.get_conn() as conn:
            cursor = conn.execute(
                """
                SELECT MIN(raw_date), MAX(raw_date)
                FROM raw_nav_observations
                WHERE raw_scheme_code = ?
                """,
                (amfi_code,),
            )
            row = cursor.fetchone()

        if not row or not row[0] or not row[1]:
            return AmfiCorroborationResult(
                boundary_consistent=True,
                empirical_observation_summary=f"No raw NAV observations in database for AMFI Code {amfi_code}; corroboration deferred.",
            )

        min_date = date.fromisoformat(row[0])
        max_date = date.fromisoformat(row[1])

        summary = f"Observed NAV bounds for AMFI {amfi_code}: First = {min_date}, Last = {max_date}."

        # Event boundary consistency checks
        if event_type == LifecycleEventType.SCHEME_MERGED_INTO or event_type == LifecycleEventType.SCHEME_CLOSED:
            # Last observed NAV should be on or shortly before effective_date
            if effective_date_precision == EffectiveDatePrecision.DAY:
                days_diff = (max_date - effective_date).days
                if days_diff > 30:
                    return AmfiCorroborationResult(
                        first_observed_nav_date=min_date,
                        last_observed_nav_date=max_date,
                        boundary_consistent=False,
                        discrepancy_detected=True,
                        empirical_observation_summary=summary,
                        discrepancy_notes=f"Last NAV date {max_date} is {days_diff} days after effective date {effective_date}.",
                    )

        return AmfiCorroborationResult(
            first_observed_nav_date=min_date,
            last_observed_nav_date=max_date,
            boundary_consistent=True,
            empirical_observation_summary=summary,
        )


# ---------------------------------------------------------------------------
# Pipeline Engine
# ---------------------------------------------------------------------------

class LifecycleIngestionPipeline:
    """
    6-Stage Ingestion Pipeline for Scheme Lifecycle Events.
    """

    def __init__(
        self,
        repository: LifecycleRepository,
        corroborator: Optional[AmfiCorroborator] = None,
        methodology_version: str = "1.0.0",
    ):
        self.repository = repository
        self.corroborator = corroborator
        self.methodology_version = methodology_version

    def process_document(
        self,
        doc: RawLifecycleDocument,
        candidates: List[CandidateLifecycleEvent],
    ) -> List[LifecycleEvent]:
        """
        Process a raw document and candidate events through the 6 pipeline stages.
        """
        ingested_events: List[LifecycleEvent] = []

        for candidate in candidates:
            # Stage 3: Normalization
            event_type, eff_date, precision = self._normalize_candidate(candidate)

            # Stage 4: Identity Resolution
            canonical_id, pred_ids, succ_ids = self._resolve_identities(candidate)

            # Stage 5: AMFI Empirical Corroboration
            corroboration = AmfiCorroborationResult()
            if self.corroborator and candidate.raw_amfi_code:
                corroboration = self.corroborator.corroborate_event(
                    amfi_code=candidate.raw_amfi_code,
                    event_type=event_type,
                    effective_date=eff_date,
                    effective_date_precision=precision,
                )

            # Stage 6: Confidence & Quarantine Evaluation
            confidence, status, quarantine_reason = self._evaluate_confidence_and_quarantine(
                doc=doc,
                candidate=candidate,
                canonical_scheme_id=canonical_id,
                event_type=event_type,
                effective_date=eff_date,
                corroboration=corroboration,
            )

            # Build Strict Semantics Notes
            formatted_notes = self._format_strict_semantics_notes(
                source_fact=candidate.source_document_fact,
                amfi_summary=corroboration.empirical_observation_summary,
                event_type=event_type,
                candidate_notes=candidate.notes,
            )

            # Generate Deterministic Event ID
            target_id = canonical_id or "unresolved_scheme"
            event_id = f"evt_{uuid.uuid5(uuid.NAMESPACE_DNS, f'{doc.source_id}:{target_id}:{event_type.value}:{eff_date.isoformat()}').hex[:16]}"

            event = LifecycleEvent(
                event_id=event_id,
                canonical_scheme_id=target_id,
                event_type=event_type,
                effective_date=eff_date,
                effective_date_precision=precision,
                source_id=doc.source_id,
                source_document_url=doc.source_document_url,
                retrieval_timestamp_utc=doc.retrieval_timestamp_utc,
                predecessor_scheme_ids=pred_ids,
                successor_scheme_ids=succ_ids,
                old_value=candidate.old_value,
                new_value=candidate.new_value,
                confidence=confidence,
                status=status,
                quarantine_reason=quarantine_reason,
                methodology_version=self.methodology_version,
                notes=formatted_notes,
            )

            # Ensure canonical_schemes entry exists to satisfy FK constraint
            self._ensure_canonical_scheme_exists(target_id, candidate.raw_scheme_name)
            for p_id in pred_ids:
                self._ensure_canonical_scheme_exists(p_id, candidate.raw_predecessor_name)
            for s_id in succ_ids:
                self._ensure_canonical_scheme_exists(s_id, candidate.raw_successor_name)

            # Persist to Repository (Idempotent)
            self.repository.save_lifecycle_event(event)
            ingested_events.append(event)

        return ingested_events

    # ------------------------------------------------------------------
    # Stage Normalization & Resolution Helpers
    # ------------------------------------------------------------------

    def _normalize_candidate(
        self, candidate: CandidateLifecycleEvent
    ) -> Tuple[LifecycleEventType, date, EffectiveDatePrecision]:
        """
        Stage 3: Normalize event type string, effective date, and date precision (MD-1).
        """
        # Event type mapping
        try:
            event_type = LifecycleEventType(candidate.event_type_str)
        except ValueError:
            event_type = LifecycleEventType.SCHEME_RENAMED  # Fallback to prevent crash

        # Effective date precision mapping (MD-1)
        precision_str = candidate.effective_date_precision_str.upper()
        if precision_str == "MONTH":
            precision = EffectiveDatePrecision.MONTH
            # Ensure YYYY-MM-01 storage representation
            dt = date.fromisoformat(candidate.effective_date_str)
            eff_date = date(dt.year, dt.month, 1)
        elif precision_str == "YEAR":
            precision = EffectiveDatePrecision.YEAR
            # Ensure YYYY-01-01 storage representation
            dt = date.fromisoformat(candidate.effective_date_str)
            eff_date = date(dt.year, 1, 1)
        else:
            precision = EffectiveDatePrecision.DAY
            eff_date = date.fromisoformat(candidate.effective_date_str)

        return event_type, eff_date, precision

    def _resolve_identities(
        self, candidate: CandidateLifecycleEvent
    ) -> Tuple[Optional[str], List[str], List[str]]:
        """
        Stage 4: Map raw scheme names/codes to canonical scheme IDs.
        """
        canonical_id: Optional[str] = None
        if candidate.raw_amfi_code:
            canonical_id = f"sch_{candidate.raw_amfi_code}"
        elif candidate.raw_scheme_name:
            # Deterministic hash ID from normalized scheme name if AMFI code missing
            name_clean = candidate.raw_scheme_name.lower().strip()
            canonical_id = f"sch_name_{uuid.uuid5(uuid.NAMESPACE_DNS, name_clean).hex[:12]}"

        predecessor_ids: List[str] = []
        if candidate.raw_predecessor_name:
            p_clean = candidate.raw_predecessor_name.lower().strip()
            predecessor_ids.append(f"sch_name_{uuid.uuid5(uuid.NAMESPACE_DNS, p_clean).hex[:12]}")

        successor_ids: List[str] = []
        if candidate.raw_successor_name:
            s_clean = candidate.raw_successor_name.lower().strip()
            successor_ids.append(f"sch_name_{uuid.uuid5(uuid.NAMESPACE_DNS, s_clean).hex[:12]}")

        return canonical_id, predecessor_ids, successor_ids

    def _evaluate_confidence_and_quarantine(
        self,
        doc: RawLifecycleDocument,
        candidate: CandidateLifecycleEvent,
        canonical_scheme_id: Optional[str],
        event_type: LifecycleEventType,
        effective_date: date,
        corroboration: AmfiCorroborationResult,
    ) -> Tuple[LifecycleConfidence, str, Optional[str]]:
        """
        Stage 6: Evaluate event confidence and quarantine rules.
        """
        # Quarantine Rule 1: Identity unresolved or missing scheme identifier
        if not canonical_scheme_id or "unresolved" in canonical_scheme_id:
            return (
                LifecycleConfidence.AMBIGUOUS,
                "QUARANTINED",
                "Quarantined: Canonical scheme identity could not be resolved from raw scheme name or AMFI code.",
            )

        # Quarantine Rule 2: Missing direct source URL for non-AMFI primary disclosures
        if not doc.source_document_url and doc.source_id != "AMFI_OFFICIAL":
            return (
                LifecycleConfidence.AMBIGUOUS,
                "QUARANTINED",
                "Quarantined: Mandatory source_document_url is missing for primary statutory document.",
            )

        # Quarantine Rule 3: Empirical discrepancy detected by AMFI corroborator
        if corroboration.discrepancy_detected:
            return (
                LifecycleConfidence.AMBIGUOUS,
                "QUARANTINED",
                f"Quarantined due to empirical AMFI NAV discrepancy: {corroboration.discrepancy_notes}",
            )

        # Quarantine Rule 4: ISIN change with conflicting evidence (MD-3)
        if event_type == LifecycleEventType.ISIN_CHANGED and "conflict" in (candidate.notes or "").lower():
            return (
                LifecycleConfidence.AMBIGUOUS,
                "QUARANTINED",
                "Quarantined (MD-3): ISIN change carries conflicting continuity evidence requiring manual investigation.",
            )

        # Quarantine Rule 5: AMFI code reuse without verified legal reassignment notice (MD-2)
        if event_type == LifecycleEventType.AMFI_CODE_REASSIGNED and "unverified" in (candidate.notes or "").lower():
            return (
                LifecycleConfidence.AMBIGUOUS,
                "QUARANTINED",
                "Quarantined (MD-2): AMFI code reuse lacks statutory reassignment evidence.",
            )

        # Quarantine Rule 6: Conflicting or ambiguous evidence in candidate notes
        if "conflict" in (candidate.notes or "").lower() or "discrepancy" in (candidate.notes or "").lower():
            return (
                LifecycleConfidence.AMBIGUOUS,
                "QUARANTINED",
                f"Quarantined due to conflicting candidate evidence: {candidate.notes}",
            )

        # Confidence Grading
        if doc.source_document_url and corroboration.boundary_consistent and doc.source_id in ("SEBI_OFFICIAL", "AMC_STATUTORY_DISCLOSURE", "AMFI_OFFICIAL"):
            confidence = LifecycleConfidence.HIGH
        elif doc.source_id in ("SEBI_OFFICIAL", "AMC_STATUTORY_DISCLOSURE", "AMFI_OFFICIAL"):
            confidence = LifecycleConfidence.MEDIUM
        else:
            confidence = LifecycleConfidence.LOW

        return confidence, "ACTIVE", None

    def _format_strict_semantics_notes(
        self,
        source_fact: str,
        amfi_summary: str,
        event_type: LifecycleEventType,
        candidate_notes: Optional[str],
    ) -> str:
        """
        Step 5 Enforcement: Format notes distinguishing Document Fact, AMFI Observation, and Platform Inference.
        """
        inference_map = {
            LifecycleEventType.SCHEME_MERGED_INTO: "Scheme identity evaluates to MERGED_PREDECESSOR after effective date boundary.",
            LifecycleEventType.SCHEME_RECEIVED_MERGER: "Scheme identity remains ACTIVE; absorbs predecessor scheme relationships.",
            LifecycleEventType.SCHEME_CLOSED: "Scheme identity evaluates to CLOSED after effective date boundary.",
            LifecycleEventType.SCHEME_RENAMED: "Scheme identity remains ACTIVE; name metadata updated.",
            LifecycleEventType.SCHEME_CREATION: "Scheme identity evaluates to PRE_LAUNCH prior to effective date, ACTIVE on/after effective date.",
            LifecycleEventType.PLAN_TYPE_CHANGED: "Scheme identity remains ACTIVE; plan_type metadata updated.",
            LifecycleEventType.OPTION_TYPE_CHANGED: "Scheme identity remains ACTIVE; option_type metadata updated.",
        }
        platform_inference = inference_map.get(event_type, "Scheme identity updated per event rules.")

        parts = [
            f"SOURCE-DOCUMENT FACT: {source_fact}",
            f"EMPIRICAL AMFI OBSERVATION: {amfi_summary}",
            f"PLATFORM INFERENCE: {platform_inference}",
        ]
        if candidate_notes:
            parts.append(f"NOTES: {candidate_notes}")

        return "\n\n".join(parts)

    def _ensure_canonical_scheme_exists(self, canonical_scheme_id: str, raw_scheme_name: Optional[str]) -> None:
        """
        Ensure canonical_schemes contains a row for canonical_scheme_id to satisfy FK constraints.
        """
        if not canonical_scheme_id:
            return

        scheme_name = raw_scheme_name or canonical_scheme_id
        clean_name = scheme_name.lower().strip()
        created_at = datetime.now(timezone.utc).isoformat()

        with self.repository.db.get_conn() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO canonical_schemes (
                    canonical_scheme_id, amc_name, scheme_name, clean_scheme_name,
                    plan_type, option_type, category, sub_category, is_active, created_at, lifecycle_status
                ) VALUES (?, 'UNKNOWN', ?, ?, 'REGULAR', 'GROWTH', 'UNKNOWN', 'UNKNOWN', 1, ?, 'UNKNOWN')
                """,
                (canonical_scheme_id, scheme_name, clean_name, created_at),
            )
