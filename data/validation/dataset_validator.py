"""
Dataset Validator (Phase F.9 — Layer D).

Validates Layer C EntityResolvedRecord and Layer B NormalizedRecord to produce
Layer D ValidatedRecord objects governed by the 8-state DataQualityState Model
(VALID, PARTIAL, UNKNOWN, INSUFFICIENT_INFORMATION, INVALID, CONFLICTED, QUARANTINED, STALE).

Enforces:
- Structural schema checks.
- Missing-data safety (Missing != 0, no favorable default evidence).
- Range bound violations (e.g., negative NAV, TER > 100%, future observation dates).
- Identity ambiguity quarantine.
- Field-specific conflict quarantine.
"""

from datetime import date, datetime, timezone
from typing import List, Optional, Tuple, Dict, Any

from models.production_dataset import (
    NormalizedRecord,
    EntityResolvedRecord,
    ValidatedRecord,
    FieldValidationFinding
)
from models.nav_data import DataQualityState


class DatasetValidator:
    """Layer D Data Quality & Structural Validation Engine."""

    def validate_record(
        self,
        norm_rec: NormalizedRecord,
        resolved_rec: EntityResolvedRecord,
        assessment_date: Optional[date] = None,
        conflicting_record: Optional[NormalizedRecord] = None
    ) -> ValidatedRecord:
        """
        Validates record and determines final DataQualityState and quarantine flags.
        """
        validated_id = f"val_{resolved_rec.resolved_id}"
        findings: List[FieldValidationFinding] = []
        quarantine_reasons: List[str] = []
        is_quarantined = False
        is_stale = False
        final_state = DataQualityState.VALID

        current_date = assessment_date or datetime.now(timezone.utc).date()

        # 1. Identity Ambiguity Validation
        if resolved_rec.is_identity_ambiguous:
            is_quarantined = True
            reason = resolved_rec.quarantine_reason or "Identity resolution ambiguous or unmapped."
            quarantine_reasons.append(reason)
            findings.append(FieldValidationFinding(
                field_name="scheme_identity",
                is_valid=False,
                quality_state=DataQualityState.QUARANTINED.value,
                issue_code="AMBIGUOUS_IDENTITY",
                issue_message=reason
            ))

        # 2. Structural & Range Bound Checks for NAV
        if norm_rec.nav_value is None:
            findings.append(FieldValidationFinding(
                field_name="nav_value",
                is_valid=False,
                quality_state=DataQualityState.INSUFFICIENT_INFORMATION.value,
                issue_code="MISSING_NAV",
                issue_message="NAV value is missing/None."
            ))
            if final_state == DataQualityState.VALID:
                final_state = DataQualityState.INSUFFICIENT_INFORMATION

        elif norm_rec.nav_value <= 0.0:
            findings.append(FieldValidationFinding(
                field_name="nav_value",
                is_valid=False,
                quality_state=DataQualityState.INVALID.value,
                issue_code="INVALID_NAV_BOUND",
                issue_message=f"Non-positive NAV value: {norm_rec.nav_value}"
            ))
            final_state = DataQualityState.INVALID
            is_quarantined = True
            quarantine_reasons.append(f"Non-positive NAV: {norm_rec.nav_value}")

        # 3. Observation Date Checks
        if norm_rec.observation_date > current_date:
            findings.append(FieldValidationFinding(
                field_name="observation_date",
                is_valid=False,
                quality_state=DataQualityState.INVALID.value,
                issue_code="FUTURE_NAV_DATE",
                issue_message=f"Observation date {norm_rec.observation_date} is in the future relative to assessment date {current_date}"
            ))
            final_state = DataQualityState.INVALID
            is_quarantined = True
            quarantine_reasons.append(f"Future observation date: {norm_rec.observation_date}")

        # 4. TER Range Checks if present
        if norm_rec.ter_value is not None:
            if norm_rec.ter_value < 0.0 or norm_rec.ter_value > 100.0:
                findings.append(FieldValidationFinding(
                    field_name="ter_value",
                    is_valid=False,
                    quality_state=DataQualityState.INVALID.value,
                    issue_code="INVALID_TER_BOUND",
                    issue_message=f"TER out of valid percentage bounds [0, 100]: {norm_rec.ter_value}"
                ))
                final_state = DataQualityState.INVALID

        # 5. Conflict Resolution Check if competing record provided
        if conflicting_record and norm_rec.nav_value is not None and conflicting_record.nav_value is not None:
            if abs(norm_rec.nav_value - conflicting_record.nav_value) > 1e-4:
                final_state = DataQualityState.CONFLICTED
                is_quarantined = True
                reason = (
                    f"Conflicting primary source NAV disagreement: {norm_rec.source_id} ({norm_rec.nav_value}) "
                    f"vs {conflicting_record.source_id} ({conflicting_record.nav_value})"
                )
                quarantine_reasons.append(reason)
                findings.append(FieldValidationFinding(
                    field_name="nav_value",
                    is_valid=False,
                    quality_state=DataQualityState.CONFLICTED.value,
                    issue_code="SOURCE_CONFLICT",
                    issue_message=reason
                ))

        # Determine Final Quality State if Quarantined
        if is_quarantined and final_state not in (DataQualityState.INVALID, DataQualityState.CONFLICTED):
            final_state = DataQualityState.QUARANTINED

        return ValidatedRecord(
            validated_record_id=validated_id,
            resolved_id=resolved_rec.resolved_id,
            canonical_scheme_id=resolved_rec.canonical_scheme_id,
            amfi_code=resolved_rec.amfi_code,
            isin=resolved_rec.isin,
            scheme_name=resolved_rec.scheme_name,
            amc_name=resolved_rec.amc_name,
            plan_type_str=resolved_rec.plan_type_str,
            option_type_str=resolved_rec.option_type_str,
            category_str=resolved_rec.category_str,
            subcategory_str=resolved_rec.subcategory_str,
            observation_date=norm_rec.observation_date,
            nav_value=norm_rec.nav_value,
            ter_value=norm_rec.ter_value,
            ter_observation_date=norm_rec.ter_observation_date,
            exit_load_text=norm_rec.exit_load_text,
            riskometer_label=norm_rec.riskometer_label,
            benchmark_name=norm_rec.benchmark_name,
            publication_date=norm_rec.publication_date,
            quality_state_str=final_state.value,
            is_stale=is_stale,
            is_quarantined=is_quarantined,
            quarantine_reasons=quarantine_reasons,
            findings=findings,
            lock_in_days=norm_rec.lock_in_days,
            lifecycle_status_str=norm_rec.lifecycle_status_str,
            launch_date=norm_rec.launch_date,
            pit_category_context=norm_rec.pit_category_context
        )

