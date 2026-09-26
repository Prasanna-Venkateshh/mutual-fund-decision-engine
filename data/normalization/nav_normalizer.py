"""
NAV Normalization Engine.

Transforms validated raw NAV observations into NormalizedNAVRecord instances linked
to Canonical Scheme IDs, preserving full source provenance metadata.
Quarantines records whose scheme mapping is AMBIGUOUS or UNMAPPED.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Tuple, Optional

from models.nav_data import RawNAVRecord, ValidationResult, NormalizedNAVRecord, DataQualityState, QuarantineRecord
from models.scheme import MappingConfidence
from data.mapping.scheme_master import SchemeMaster


class NAVNormalizer:
    """Normalizes validated raw NAV observations into canonical NAV records."""

    def __init__(self, scheme_master: SchemeMaster):
        self.scheme_master = scheme_master

    def normalize_record(
        self,
        raw_rec: RawNAVRecord,
        val_res: ValidationResult
    ) -> Tuple[Optional[NormalizedNAVRecord], Optional[QuarantineRecord]]:
        """
        Normalize a validated raw record.
        
        Guarantees:
        1. Raw observation is validated.
        2. Scheme identity resolves to a high/exact confidence Canonical Scheme.
        3. If mapping is AMBIGUOUS or UNMAPPED, record is quarantined.
        4. Preserves source_id, raw_record_id, and retrieval_timestamp.
        """
        if not val_res.is_valid or not val_res.parsed_date or val_res.parsed_nav is None:
            q_rec = QuarantineRecord(
                quarantine_id=f"quarantine_norm_{raw_rec.raw_record_id}",
                raw_record_id=raw_rec.raw_record_id,
                source_id=raw_rec.source_id,
                reason=val_res.error_message or "Normalization failed: invalid validation result.",
                quarantined_at=datetime.now(timezone.utc),
                raw_payload=f"scheme={raw_rec.raw_scheme_code}|nav={raw_rec.raw_nav_value}|date={raw_rec.raw_date}"
            )
            return None, q_rec

        # Extract ISIN if present in metadata
        isin_growth = None
        if raw_rec.additional_metadata:
            isin_growth = raw_rec.additional_metadata.get("isin_growth")

        canonical, mapping = self.scheme_master.resolve_or_create_canonical_scheme(
            source_id=raw_rec.source_id,
            source_scheme_code=val_res.parsed_scheme_code or raw_rec.raw_scheme_code,
            source_scheme_name=val_res.parsed_scheme_name or raw_rec.raw_scheme_name,
            isin_growth=isin_growth
        )

        # Enforce Quarantine for Ambiguous or Unmapped schemes
        if mapping.confidence in (MappingConfidence.AMBIGUOUS, MappingConfidence.UNMAPPED):
            q_rec = QuarantineRecord(
                quarantine_id=f"quarantine_map_{raw_rec.raw_record_id}",
                raw_record_id=raw_rec.raw_record_id,
                source_id=raw_rec.source_id,
                reason=f"Isolated during normalization: scheme mapping confidence is {mapping.confidence.value}. {mapping.notes}",
                quarantined_at=datetime.now(timezone.utc),
                raw_payload=f"scheme_name={raw_rec.raw_scheme_name}|code={raw_rec.raw_scheme_code}"
            )
            return None, q_rec

        nav_id = f"norm_{canonical.canonical_scheme_id}_{val_res.parsed_date.strftime('%Y%m%d')}_{raw_rec.source_id}"

        norm_rec = NormalizedNAVRecord(
            nav_id=nav_id,
            canonical_scheme_id=canonical.canonical_scheme_id,
            nav_date=val_res.parsed_date,
            nav_value=val_res.parsed_nav,
            source_id=raw_rec.source_id,
            raw_record_id=raw_rec.raw_record_id,
            retrieval_timestamp=raw_rec.retrieval_timestamp,
            quality_state=val_res.quality_state,
            observation_date=val_res.parsed_date
        )

        return norm_rec, None

    def normalize_batch(
        self,
        valid_tuples: List[Tuple[RawNAVRecord, ValidationResult]]
    ) -> Tuple[List[NormalizedNAVRecord], List[QuarantineRecord]]:
        """Normalize a batch of validated raw observations."""
        normalized_records: List[NormalizedNAVRecord] = []
        quarantine_records: List[QuarantineRecord] = []

        for raw_rec, val_res in valid_tuples:
            norm_rec, q_rec = self.normalize_record(raw_rec, val_res)
            if norm_rec:
                normalized_records.append(norm_rec)
            elif q_rec:
                quarantine_records.append(q_rec)

        return normalized_records, quarantine_records
