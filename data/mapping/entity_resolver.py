"""
Entity Resolver (Phase F.9 — Layer C).

Maps Layer B NormalizedRecord objects into Layer C EntityResolvedRecord objects.
Prioritizes AMFI code and ISIN code identity matching.
Routes ambiguous or unmapped identity matches to quarantine.
"""

from typing import Optional, Tuple
from models.production_dataset import NormalizedRecord, EntityResolvedRecord
from data.mapping.scheme_master import SchemeMaster
from models.scheme import MappingConfidence


class EntityResolver:
    """Layer C Entity Resolution Engine."""

    def __init__(self, scheme_master: Optional[SchemeMaster] = None):
        self.scheme_master = scheme_master or SchemeMaster()

    def resolve_entity(self, norm_rec: NormalizedRecord) -> EntityResolvedRecord:
        """
        Resolves normalized record to a Layer C EntityResolvedRecord.
        """
        resolved_id = f"ent_{norm_rec.record_id}"

        # 1. Primary Resolution via SchemeMaster
        canonical, mapping = self.scheme_master.resolve_or_create_canonical_scheme(
            source_id=norm_rec.source_id,
            source_scheme_code=norm_rec.raw_scheme_code,
            source_scheme_name=norm_rec.raw_scheme_name,
            isin_growth=norm_rec.isin_code
        )

        # 2. Check for Identity Ambiguity / Quarantine
        is_ambiguous = False
        quarantine_reason = None
        resolution_method = "AMFI_EXACT" if norm_rec.raw_scheme_code.isdigit() else "ALIAS_MAP"

        if norm_rec.isin_code:
            resolution_method = "ISIN_EXACT"

        if mapping.confidence in (MappingConfidence.AMBIGUOUS, MappingConfidence.UNMAPPED):
            is_ambiguous = True
            resolution_method = "UNRESOLVED_AMBIGUOUS"
            quarantine_reason = f"Identity resolution ambiguous or unmapped: {mapping.notes}"

        # Confidence Score calculation
        confidence_score = 1.0
        if mapping.confidence == MappingConfidence.HIGH_CONFIDENCE:
            confidence_score = 0.85
        elif mapping.confidence == MappingConfidence.AMBIGUOUS:
            confidence_score = 0.40
        elif mapping.confidence == MappingConfidence.UNMAPPED:
            confidence_score = 0.0

        canonical_id = canonical.canonical_scheme_id

        return EntityResolvedRecord(
            resolved_id=resolved_id,
            normalized_record_id=norm_rec.record_id,
            canonical_scheme_id=canonical_id,
            amfi_code=norm_rec.raw_scheme_code,
            isin=norm_rec.isin_code,
            scheme_name=canonical.scheme_name or norm_rec.normalized_scheme_name,
            amc_name=canonical.amc_name or norm_rec.amc_name_str,
            plan_type_str=canonical.plan_type.value if canonical.plan_type.value != "UNKNOWN" else norm_rec.plan_type_str,
            option_type_str=canonical.option_type.value if canonical.option_type.value != "UNKNOWN" else norm_rec.option_type_str,
            category_str=norm_rec.category_str,
            subcategory_str=norm_rec.subcategory_str,
            resolution_method=resolution_method,
            identity_confidence=confidence_score,
            is_identity_ambiguous=is_ambiguous,
            quarantine_reason=quarantine_reason
        )
