"""
Risk Alignment Engine Implementation (Phase F.3.3.2).

Implements the production Risk Alignment Engine combining independent Risk Capacity
and Risk Tolerance assessments according to the F.3.3 specification and F.3.3.1 audit.

Governance Rules Enforced:
- Risk Capacity != Risk Tolerance.
- Aligned Risk Level = min(Risk Capacity Level, Risk Tolerance Level) when both are valid.
- High Risk Tolerance CANNOT override inadequate Risk Capacity.
- High Risk Capacity CANNOT force a higher Risk Tolerance.
- Ordinal comparisons are integer value comparisons (VERY_LOW=1 ... VERY_HIGH=5).
- Confidence scores NEVER alter ordinal risk levels.
- Missing or insufficient inputs produce clear status tags (INSUFFICIENT_INFORMATION, INVALID_ASSESSMENT).
- Preserves full auditability, versioning, confidence, staleness flags, and provenance.
"""

import uuid
from datetime import date, datetime, timezone
from typing import List, Optional, Tuple, Any

from config.risk.alignment_config import RiskAlignmentConfig
from config.risk.capacity_config import StartupMode
from models.fund_quality_dataset import ProvenanceMetadata
from models.investor_profile import (
    InvestorProfileSnapshot,
    RiskCapacityLevel,
    RiskToleranceLevel,
)
from risk.alignment_models import (
    AlignedRiskLevel,
    AlignmentStatus,
    LimitingConstraint,
    RiskAlignmentAssessmentResult,
)
from risk.capacity_models import AssessmentStatus, RiskCapacityAssessmentResult
from risk.tolerance_models import RiskToleranceAssessmentResult


class RiskAlignmentEngine:
    """
    Production Risk Alignment Engine enforcing lower-of-two risk envelope constraint.
    """

    def __init__(self, config: Optional[RiskAlignmentConfig] = None):
        if config is None:
            self.config = RiskAlignmentConfig()
        else:
            self.config = config

    # -------------------------------------------------------------------------
    # A. INPUT VALIDATION
    # -------------------------------------------------------------------------
    def validate_inputs(
        self,
        capacity_assessment: Optional[RiskCapacityAssessmentResult],
        tolerance_assessment: Optional[RiskToleranceAssessmentResult],
    ) -> List[str]:
        """
        Validates structural integrity of input assessment objects.
        Returns a list of error strings. If empty, inputs are valid.
        """
        errors = []
        if capacity_assessment is None:
            errors.append("capacity_assessment cannot be None")
        else:
            if not capacity_assessment.assessment_id or not capacity_assessment.assessment_id.strip():
                errors.append("capacity_assessment.assessment_id cannot be empty")
            if capacity_assessment.confidence_score < 0.0 or capacity_assessment.confidence_score > 1.0:
                errors.append(
                    f"capacity_assessment.confidence_score out of bounds [0.0, 1.0]: {capacity_assessment.confidence_score}"
                )

        if tolerance_assessment is None:
            errors.append("tolerance_assessment cannot be None")
        else:
            if not tolerance_assessment.assessment_id or not tolerance_assessment.assessment_id.strip():
                errors.append("tolerance_assessment.assessment_id cannot be empty")
            if tolerance_assessment.confidence_score < 0.0 or tolerance_assessment.confidence_score > 1.0:
                errors.append(
                    f"tolerance_assessment.confidence_score out of bounds [0.0, 1.0]: {tolerance_assessment.confidence_score}"
                )

        return errors

    # -------------------------------------------------------------------------
    # B. STALENESS ASSESSMENT
    # -------------------------------------------------------------------------
    def check_input_staleness(
        self,
        capacity_date: date,
        tolerance_date: date,
    ) -> Tuple[bool, int]:
        """
        Calculates gap in days between Capacity observation date and Tolerance observation date.
        Returns (is_stale, gap_days).
        """
        gap_days = abs((capacity_date - tolerance_date).days)
        max_gap = self.config.max_assessment_age_gap_days if self.config.max_assessment_age_gap_days is not None else 90
        is_stale = gap_days > max_gap
        return is_stale, gap_days

    # -------------------------------------------------------------------------
    # C. PROVENANCE MERGING
    # -------------------------------------------------------------------------
    def _merge_provenance(
        self,
        capacity_prov: Optional[ProvenanceMetadata],
        tolerance_prov: Optional[ProvenanceMetadata],
    ) -> Optional[ProvenanceMetadata]:
        """
        Merges provenance metadata from capacity and tolerance assessments.
        """
        if not capacity_prov and not tolerance_prov:
            return None
        if capacity_prov and not tolerance_prov:
            return capacity_prov
        if tolerance_prov and not capacity_prov:
            return tolerance_prov

        combined_url = f"{capacity_prov.source_document_url};{tolerance_prov.source_document_url}"
        combined_source_id = f"{capacity_prov.source_id}+{tolerance_prov.source_id}"
        return ProvenanceMetadata(
            source_id=combined_source_id,
            source_document_url=combined_url,
            retrieval_timestamp_utc=capacity_prov.retrieval_timestamp_utc,
            methodology_version=self.config.methodology_version,
            is_platform_calculated=True,
        )

    # -------------------------------------------------------------------------
    # MAIN ENGINE ASSESSMENT PIPELINE
    # -------------------------------------------------------------------------
    def assess_alignment(
        self,
        capacity_assessment: Optional[RiskCapacityAssessmentResult],
        tolerance_assessment: Optional[RiskToleranceAssessmentResult],
        investor_id: Optional[str] = None,
        profile_version: Optional[str] = None,
        observation_date: Optional[date] = None,
    ) -> RiskAlignmentAssessmentResult:
        """
        Executes the complete end-to-end Risk Alignment assessment pipeline.
        Enforces lower-of-two constraint and returns immutable RiskAlignmentAssessmentResult.
        """
        assessment_id = f"RA-{uuid.uuid4().hex[:12].upper()}"
        ts_utc = datetime.now(timezone.utc)

        # Determine investor_id and profile_version
        inv_id = investor_id
        if not inv_id:
            if capacity_assessment and capacity_assessment.investor_id:
                inv_id = capacity_assessment.investor_id
            elif tolerance_assessment and tolerance_assessment.investor_id:
                inv_id = tolerance_assessment.investor_id
            else:
                inv_id = "UNKNOWN_INVESTOR"

        prof_ver = profile_version
        if not prof_ver:
            if capacity_assessment and capacity_assessment.profile_version_used:
                prof_ver = capacity_assessment.profile_version_used
            elif tolerance_assessment and tolerance_assessment.profile_version_used:
                prof_ver = tolerance_assessment.profile_version_used
            else:
                prof_ver = "1.0.0"

        obs_date = observation_date
        if not obs_date:
            if capacity_assessment and capacity_assessment.observation_date:
                obs_date = capacity_assessment.observation_date
            elif tolerance_assessment and tolerance_assessment.observation_date:
                obs_date = tolerance_assessment.observation_date
            else:
                obs_date = date.today()

        # 1. Configuration Validation
        config_errors = self.config.validate()
        if config_errors:
            return RiskAlignmentAssessmentResult(
                assessment_id=assessment_id,
                investor_id=inv_id,
                profile_version_used=prof_ver,
                observation_date=obs_date,
                assessment_timestamp_utc=ts_utc,
                startup_mode=self.config.startup_mode,
                alignment_status=AlignmentStatus.INVALID_ASSESSMENT,
                limiting_constraint=LimitingConstraint.UNCLASSIFIED,
                aligned_risk_level=None,
                alignment_confidence_score=0.0,
                explanation_tokens=["MISSING_PRODUCTION_CALIBRATION_PARAMETERS"],
                missing_information_tokens=config_errors,
                output_tag=self.config.output_tag,
                methodology_version=self.config.methodology_version,
                rule_version=self.config.rule_version,
            )

        # 2. Input Null / Structural Validation
        input_errors = self.validate_inputs(capacity_assessment, tolerance_assessment)
        if input_errors:
            missing_tokens = []
            if capacity_assessment is None:
                missing_tokens.append("MISSING_CAPACITY_ASSESSMENT")
            if tolerance_assessment is None:
                missing_tokens.append("MISSING_TOLERANCE_ASSESSMENT")

            # Determine constraint classification for null input
            if capacity_assessment is None and tolerance_assessment is None:
                lim_constraint = LimitingConstraint.BOTH_INSUFFICIENT
            else:
                lim_constraint = LimitingConstraint.UNCLASSIFIED

            return RiskAlignmentAssessmentResult(
                assessment_id=assessment_id,
                investor_id=inv_id,
                profile_version_used=prof_ver,
                observation_date=obs_date,
                assessment_timestamp_utc=ts_utc,
                startup_mode=self.config.startup_mode,
                alignment_status=AlignmentStatus.INSUFFICIENT_INFORMATION,
                limiting_constraint=lim_constraint,
                aligned_risk_level=None,
                capacity_assessment_id=capacity_assessment.assessment_id if capacity_assessment else None,
                tolerance_assessment_id=tolerance_assessment.assessment_id if tolerance_assessment else None,
                capacity_confidence_score=capacity_assessment.confidence_score if capacity_assessment else 0.0,
                tolerance_confidence_score=tolerance_assessment.confidence_score if tolerance_assessment else 0.0,
                alignment_confidence_score=0.0,
                explanation_tokens=["INSUFFICIENT_INPUT_ASSESSMENTS"],
                missing_information_tokens=missing_tokens + input_errors,
                output_tag=self.config.output_tag,
                methodology_version=self.config.methodology_version,
                rule_version=self.config.rule_version,
            )

        # 3. Check for Input Configuration Errors or Invalid Statuses
        if (
            capacity_assessment.assessment_status == AssessmentStatus.CONFIGURATION_ERROR
            or tolerance_assessment.assessment_status == AssessmentStatus.CONFIGURATION_ERROR
        ):
            return RiskAlignmentAssessmentResult(
                assessment_id=assessment_id,
                investor_id=inv_id,
                profile_version_used=prof_ver,
                observation_date=obs_date,
                assessment_timestamp_utc=ts_utc,
                startup_mode=self.config.startup_mode,
                alignment_status=AlignmentStatus.INVALID_ASSESSMENT,
                limiting_constraint=LimitingConstraint.UNCLASSIFIED,
                aligned_risk_level=None,
                capacity_assessment_id=capacity_assessment.assessment_id,
                tolerance_assessment_id=tolerance_assessment.assessment_id,
                capacity_confidence_score=capacity_assessment.confidence_score,
                tolerance_confidence_score=tolerance_assessment.confidence_score,
                alignment_confidence_score=0.0,
                explanation_tokens=["INPUT_ASSESSMENT_CONFIGURATION_ERROR"],
                missing_information_tokens=["UNDERLYING_ASSESSMENT_CONFIG_ERROR"],
                provenance=self._merge_provenance(capacity_assessment.provenance, tolerance_assessment.provenance),
                output_tag=self.config.output_tag,
                methodology_version=self.config.methodology_version,
                rule_version=self.config.rule_version,
            )

        # 4. Check for Insufficient Data in Underlying Assessments
        cap_tier = capacity_assessment.overall_capacity_tier
        tol_tier = tolerance_assessment.overall_tolerance_tier
        cap_status = capacity_assessment.assessment_status
        tol_status = tolerance_assessment.assessment_status

        if (
            cap_status == AssessmentStatus.INSUFFICIENT_INFORMATION
            or tol_status == AssessmentStatus.INSUFFICIENT_INFORMATION
            or cap_tier is None
            or tol_tier is None
        ):
            missing_tokens = []
            if cap_tier is None or cap_status == AssessmentStatus.INSUFFICIENT_INFORMATION:
                missing_tokens.append("INSUFFICIENT_DATA_CAPACITY_MISSING")
            if tol_tier is None or tol_status == AssessmentStatus.INSUFFICIENT_INFORMATION:
                missing_tokens.append("INSUFFICIENT_DATA_TOLERANCE_MISSING")

            if cap_tier is None and tol_tier is None:
                lim_constraint = LimitingConstraint.BOTH_INSUFFICIENT
            else:
                lim_constraint = LimitingConstraint.UNCLASSIFIED

            base_conf = min(capacity_assessment.confidence_score, tolerance_assessment.confidence_score)

            return RiskAlignmentAssessmentResult(
                assessment_id=assessment_id,
                investor_id=inv_id,
                profile_version_used=prof_ver,
                observation_date=obs_date,
                assessment_timestamp_utc=ts_utc,
                startup_mode=self.config.startup_mode,
                alignment_status=AlignmentStatus.INSUFFICIENT_INFORMATION,
                limiting_constraint=lim_constraint,
                aligned_risk_level=None,
                risk_capacity_level=cap_tier,
                risk_tolerance_level=tol_tier,
                capacity_assessment_id=capacity_assessment.assessment_id,
                tolerance_assessment_id=tolerance_assessment.assessment_id,
                capacity_confidence_score=capacity_assessment.confidence_score,
                tolerance_confidence_score=tolerance_assessment.confidence_score,
                alignment_confidence_score=base_conf,
                explanation_tokens=["INSUFFICIENT_INFORMATION_FOR_ALIGNMENT"],
                missing_information_tokens=missing_tokens,
                provenance=self._merge_provenance(capacity_assessment.provenance, tolerance_assessment.provenance),
                output_tag=self.config.output_tag,
                methodology_version=self.config.methodology_version,
                rule_version=self.config.rule_version,
            )

        # 5. Core Lower-of-Two Ordinal Calculation
        cap_val = cap_tier.value
        tol_val = tol_tier.value
        min_val = min(cap_val, tol_val)
        aligned_risk_level = AlignedRiskLevel(min_val)

        # 6. Alignment Status and Limiting Constraint Determination
        explanation_tokens = []
        missing_information_tokens = []

        is_both_complete = (
            cap_status == AssessmentStatus.COMPLETE and tol_status == AssessmentStatus.COMPLETE
        )

        if is_both_complete:
            if cap_val == tol_val:
                alignment_status = AlignmentStatus.FULLY_ALIGNED
                limiting_constraint = LimitingConstraint.NONE
                explanation_tokens.append("FULLY_ALIGNED_CAPACITY_AND_TOLERANCE")
            elif cap_val < tol_val:
                alignment_status = AlignmentStatus.CAPACITY_CONSTRAINED
                limiting_constraint = LimitingConstraint.RISK_CAPACITY
                explanation_tokens.append("CONSTRAINED_BY_RISK_CAPACITY")
            else:
                alignment_status = AlignmentStatus.TOLERANCE_CONSTRAINED
                limiting_constraint = LimitingConstraint.RISK_TOLERANCE
                explanation_tokens.append("CONSTRAINED_BY_RISK_TOLERANCE")
        else:
            # One or both assessments are PARTIAL
            alignment_status = AlignmentStatus.PARTIAL_ALIGNMENT
            if cap_val < tol_val:
                limiting_constraint = LimitingConstraint.RISK_CAPACITY
            elif tol_val < cap_val:
                limiting_constraint = LimitingConstraint.RISK_TOLERANCE
            else:
                limiting_constraint = LimitingConstraint.NONE

            explanation_tokens.append("PROVISIONAL_ALIGNMENT_PARTIAL_INPUTS")

            if cap_status == AssessmentStatus.PARTIAL:
                missing_information_tokens.append("PARTIAL_ALIGNMENT_CAPACITY_PARTIAL")
            if tol_status == AssessmentStatus.PARTIAL:
                missing_information_tokens.append("PARTIAL_ALIGNMENT_TOLERANCE_PARTIAL")

        # 7. Confidence Calculation & Penalty Ordering (F.3.3.2 §12)
        # Step 1: Base Confidence = min(Capacity Confidence, Tolerance Confidence)
        base_confidence = min(capacity_assessment.confidence_score, tolerance_assessment.confidence_score)

        # Step 2: Apply Partial Alignment Confidence Cap if applicable
        partial_cap = self.config.partial_alignment_confidence_cap or 0.70
        if alignment_status == AlignmentStatus.PARTIAL_ALIGNMENT:
            conf_after_cap = min(base_confidence, partial_cap)
        else:
            conf_after_cap = base_confidence

        # Step 3: Check Input Staleness & Apply Penalty if gap > threshold
        is_stale, gap_days = self.check_input_staleness(
            capacity_assessment.observation_date,
            tolerance_assessment.observation_date,
        )

        stale_penalty = self.config.stale_input_confidence_penalty or 0.85
        if is_stale:
            explanation_tokens.append("STALE_ASSESSMENT_INPUT_GAP_EXCEEDED")
            final_confidence = conf_after_cap * stale_penalty
        else:
            final_confidence = conf_after_cap

        # Step 4: Clamp final confidence to [0.0, 1.0]
        final_confidence = max(0.0, min(1.0, final_confidence))

        # 8. Merge Provenance Metadata
        merged_provenance = self._merge_provenance(
            capacity_assessment.provenance,
            tolerance_assessment.provenance,
        )

        # 9. Return Reproducible Alignment Assessment Result Data Contract
        return RiskAlignmentAssessmentResult(
            assessment_id=assessment_id,
            investor_id=inv_id,
            profile_version_used=prof_ver,
            observation_date=obs_date,
            assessment_timestamp_utc=ts_utc,
            startup_mode=self.config.startup_mode,
            alignment_status=alignment_status,
            limiting_constraint=limiting_constraint,
            aligned_risk_level=aligned_risk_level,
            risk_capacity_level=cap_tier,
            risk_tolerance_level=tol_tier,
            capacity_assessment_id=capacity_assessment.assessment_id,
            tolerance_assessment_id=tolerance_assessment.assessment_id,
            capacity_confidence_score=capacity_assessment.confidence_score,
            tolerance_confidence_score=tolerance_assessment.confidence_score,
            alignment_confidence_score=final_confidence,
            explanation_tokens=explanation_tokens,
            missing_information_tokens=missing_information_tokens,
            provenance=merged_provenance,
            output_tag=self.config.output_tag,
            is_stale_input=is_stale,
            methodology_version=self.config.methodology_version,
            rule_version=self.config.rule_version,
        )
