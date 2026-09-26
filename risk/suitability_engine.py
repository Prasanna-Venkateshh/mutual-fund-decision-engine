"""
Production Suitability Engine Implementation (Phase F.3.4.4).

Executes governed Suitability assessment logic strictly according to the approved F.3.4.3 specification:
docs/phase_f3_4_3_suitability_decision_logic_specification.md

Core Responsibilities:
- Receives investor profile, goal profile, fund quality dataset, risk alignment assessment, and optional portfolio context.
- Returns five governed Suitability states: SUITABLE, CONDITIONALLY_SUITABLE, NOT_SUITABLE, INSUFFICIENT_INFORMATION, INVALID_ASSESSMENT.
- Enforces strict 5-step decision pipeline:
  INVALID_ASSESSMENT > INSUFFICIENT_INFORMATION > HARD_CONSTRAINT > CONDITIONAL_CONCERN > POSITIVE_EVIDENCE
- Zero weighted scores, zero invented thresholds, zero upstream metric recomputations, zero transaction/buy/sell recommendations.
- Full provenance, versioning, confidence preservation, and rule ID tracking.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import List, Optional, Dict, Any
import uuid

from models.fund_quality_dataset import FundQualityDatasetInput, ProvenanceMetadata
from scoring.models import FundQualityScoreResult
from models.investor_profile import InvestorProfileSnapshot
from models.goal_profile import GoalProfile
from models.suitability_assessment import SuitabilityAssessmentResult, SuitabilityStatus
from risk.alignment_models import RiskAlignmentAssessmentResult, AlignmentStatus, AlignedRiskLevel


class SuitabilityEvaluationState(Enum):
    SUITABLE = "SUITABLE"
    CONDITIONALLY_SUITABLE = "CONDITIONALLY_SUITABLE"
    NOT_SUITABLE = "NOT_SUITABLE"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"
    INVALID_ASSESSMENT = "INVALID_ASSESSMENT"


@dataclass(frozen=True)
class FundRiskProfileInput:
    """
    Data contract representing sourced Fund Risk Profile (e.g. SEBI Riskometer).
    Preserves original classification without assuming unvalidated numerical mapping.
    """
    raw_riskometer_value: Optional[str] = None  # e.g., "Very High", "High", "Moderate"
    risk_level_numeric: Optional[int] = None    # 1 to 5 if mapped under governed protocol
    is_mapped: bool = False
    source_authority: str = "SEBI_RISKOMETER"


@dataclass(frozen=True)
class LockInContextInput:
    """
    Data contract representing statutory or contractual lock-in information.
    """
    lock_in_days: Optional[int] = None
    lock_in_years: Optional[float] = None
    is_statutory: bool = False
    source_authority: Optional[str] = None
    is_available: bool = False


@dataclass(frozen=True)
class LiquidityContextInput:
    """
    Data contract representing liquidity characteristics of an investment.
    """
    exit_load_period_days: Optional[int] = None
    is_open_ended: bool = True
    is_available: bool = True


@dataclass(frozen=True)
class PortfolioContextInput:
    """
    Data contract representing existing portfolio holdings for contextual overlap check.
    Read-only context — does NOT perform Portfolio Need or Rebalancing calculation.
    """
    existing_exposure_pct: Optional[float] = None
    category_concentration_pct: Optional[float] = None
    amc_concentration_pct: Optional[float] = None
    security_overlap_pct: Optional[float] = None
    is_provided: bool = True
    is_complete: bool = True


@dataclass(frozen=True)
class SuitabilityEvaluationRequest:
    """
    Comprehensive input request for Suitability Evaluation.
    """
    investor_profile: Optional[InvestorProfileSnapshot]
    risk_alignment: Optional[RiskAlignmentAssessmentResult]
    fund_quality_dataset: Optional[FundQualityDatasetInput] = None
    fund_quality_score: Optional[FundQualityScoreResult] = None
    goal_profile: Optional[GoalProfile] = None
    fund_risk_profile: Optional[FundRiskProfileInput] = None
    lock_in_context: Optional[LockInContextInput] = None
    liquidity_context: Optional[LiquidityContextInput] = None
    portfolio_context: Optional[PortfolioContextInput] = None
    observation_date: Optional[date] = None


class SuitabilityEngine:
    """
    Production Suitability Engine implementing F.3.4.3 business decision logic.
    """

    METHODOLOGY_VERSION = "1.0.0"
    RULE_VERSION = "1.0.0"

    def evaluate(self, request: SuitabilityEvaluationRequest) -> SuitabilityAssessmentResult:
        """
        Executes the 5-step decision pipeline.
        """
        assessment_id = f"SUIT_{uuid.uuid4().hex[:12]}"
        timestamp_utc = datetime.utcnow()
        obs_date = request.observation_date or date.today()

        # Step 1: Input Validation & Invalidation Check (R-INV-1)
        inv_reason = self._check_invalidation(request)
        if inv_reason:
            return self._build_result(
                assessment_id=assessment_id,
                request=request,
                obs_date=obs_date,
                timestamp_utc=timestamp_utc,
                status=SuitabilityStatus.INSUFFICIENT_INFORMATION,
                eval_state=SuitabilityEvaluationState.INVALID_ASSESSMENT,
                rejection_reasons=[inv_reason],
                constraints_applied=["R-INV-1"],
                summary=f"Assessment invalid: {inv_reason}",
                confidence=0.0
            )

        # Step 2: Information Requirement Check (R-INF-1, R-INF-2)
        inf_reasons, inf_tokens = self._check_information_requirements(request)
        if inf_reasons:
            return self._build_result(
                assessment_id=assessment_id,
                request=request,
                obs_date=obs_date,
                timestamp_utc=timestamp_utc,
                status=SuitabilityStatus.INSUFFICIENT_INFORMATION,
                eval_state=SuitabilityEvaluationState.INSUFFICIENT_INFORMATION,
                rejection_reasons=inf_reasons,
                constraints_applied=inf_tokens,
                summary=f"Insufficient information to evaluate suitability: {'; '.join(inf_reasons)}",
                confidence=0.0
            )

        # Calculate initial confidence from upstream signals
        base_confidence = self._compute_base_confidence(request)

        # Step 3: Hard Constraints Evaluation (R-HARD-1, R-HARD-2)
        hard_violations, hard_tokens = self._check_hard_constraints(request)
        if hard_violations:
            return self._build_result(
                assessment_id=assessment_id,
                request=request,
                obs_date=obs_date,
                timestamp_utc=timestamp_utc,
                status=SuitabilityStatus.NOT_SUITABLE,
                eval_state=SuitabilityEvaluationState.NOT_SUITABLE,
                rejection_reasons=hard_violations,
                constraints_applied=hard_tokens,
                summary=f"Not suitable due to hard constraints: {'; '.join(hard_violations)}",
                confidence=base_confidence
            )

        # Step 4: Conditional Concerns Check (R-COND-1 to R-COND-5)
        cond_concerns, cond_tokens, confidence_penalties = self._check_conditional_concerns(request)
        
        # Apply non-arbitrary confidence penalties
        final_confidence = max(0.0, min(1.0, base_confidence - sum(confidence_penalties)))

        if cond_concerns:
            return self._build_result(
                assessment_id=assessment_id,
                request=request,
                obs_date=obs_date,
                timestamp_utc=timestamp_utc,
                status=SuitabilityStatus.SUITABLE_WITH_CONSTRAINTS,
                eval_state=SuitabilityEvaluationState.CONDITIONALLY_SUITABLE,
                rejection_reasons=[],
                constraints_applied=cond_tokens,
                summary=f"Conditionally suitable with contextual concerns: {'; '.join(cond_concerns)}",
                confidence=final_confidence
            )

        # Step 5: Positive Evidence Evaluation (R-POS-1)
        applied_tokens = list(set(["R-POS-1"] + cond_tokens))
        return self._build_result(
            assessment_id=assessment_id,
            request=request,
            obs_date=obs_date,
            timestamp_utc=timestamp_utc,
            status=SuitabilityStatus.SUITABLE,
            eval_state=SuitabilityEvaluationState.SUITABLE,
            rejection_reasons=[],
            constraints_applied=applied_tokens,
            summary="Suitable: Investment matches investor risk alignment, goal context, and quality standards.",
            confidence=final_confidence
        )

    def _check_invalidation(self, request: SuitabilityEvaluationRequest) -> Optional[str]:
        """R-INV-1: Validates required contracts and negative confidence."""
        if request is None:
            return "Request object is None"
        if request.risk_alignment and request.risk_alignment.alignment_status == AlignmentStatus.INVALID_ASSESSMENT:
            return "Upstream Risk Alignment assessment is INVALID_ASSESSMENT"
        if request.risk_alignment and request.risk_alignment.alignment_confidence_score < 0.0:
            return "Risk Alignment confidence score is negative"
        if request.fund_quality_dataset and request.fund_quality_dataset.confidence_score < 0.0:
            return "Fund Quality Dataset confidence score is negative"
        if request.fund_quality_score and request.fund_quality_score.confidence_score < 0.0:
            return "Fund Quality Score confidence score is negative"
        return None

    def _check_information_requirements(self, request: SuitabilityEvaluationRequest) -> (List[str], List[str]):
        """R-INF-1 & R-INF-2: Validates presence of mandatory Risk Alignment and Fund Quality."""
        reasons = []
        tokens = []

        if not request.risk_alignment or request.risk_alignment.alignment_status == AlignmentStatus.INSUFFICIENT_INFORMATION:
            reasons.append("Missing or insufficient Risk Alignment Assessment (R-INF-1)")
            tokens.append("R-INF-1")

        if not request.fund_quality_dataset and not request.fund_quality_score:
            reasons.append("Missing Fund Quality Dataset / Score (R-INF-2)")
            tokens.append("R-INF-2")
        elif request.fund_quality_dataset and request.fund_quality_dataset.category_context.category == "UNMAPPED":
            reasons.append("Unmapped Fund Category (R-INF-2)")
            tokens.append("R-INF-2")
        elif request.fund_quality_score and request.fund_quality_score.category == "UNMAPPED":
            reasons.append("Unmapped Fund Category (R-INF-2)")
            tokens.append("R-INF-2")

        return reasons, tokens

    def _check_hard_constraints(self, request: SuitabilityEvaluationRequest) -> (List[str], List[str]):
        """
        R-HARD-1: Fund Risk > Aligned Risk Envelope (Only when governed compatibility exists).
        R-HARD-2: Authoritative Lock-In > Goal Horizon.
        """
        violations = []
        tokens = []

        # R-HARD-1: Governed Risk Envelope Check
        if request.risk_alignment and request.risk_alignment.aligned_risk_level and request.fund_risk_profile:
            if request.fund_risk_profile.is_mapped and request.fund_risk_profile.risk_level_numeric:
                aligned_numeric = request.risk_alignment.aligned_risk_level.value
                if request.fund_risk_profile.risk_level_numeric > aligned_numeric:
                    violations.append(
                        f"Fund Risk Level ({request.fund_risk_profile.risk_level_numeric}) exceeds "
                        f"Aligned Risk Level ({aligned_numeric}) (R-HARD-1)"
                    )
                    tokens.append("R-HARD-1")

        # R-HARD-2: Statutory Lock-In Conflict Check
        if request.lock_in_context and request.lock_in_context.is_statutory and request.lock_in_context.lock_in_years:
            if request.goal_profile and request.goal_profile.effective_horizon_years:
                if request.lock_in_context.lock_in_years > request.goal_profile.effective_horizon_years:
                    violations.append(
                        f"Statutory Lock-In ({request.lock_in_context.lock_in_years} yrs) exceeds "
                        f"Goal Horizon ({request.goal_profile.effective_horizon_years} yrs) (R-HARD-2)"
                    )
                    tokens.append("R-HARD-2")

        return violations, tokens

    def _check_conditional_concerns(self, request: SuitabilityEvaluationRequest) -> (List[str], List[str], List[float]):
        """
        R-COND-1 to R-COND-5: Contextual concerns that yield CONDITIONALLY_SUITABLE or reduced confidence.
        """
        concerns = []
        tokens = []
        penalties = []

        # R-COND-1: Lower-Risk Fund Profile (Below Envelope) -> SUITABLE with Context Warning
        if request.risk_alignment and request.risk_alignment.aligned_risk_level and request.fund_risk_profile:
            if request.fund_risk_profile.is_mapped and request.fund_risk_profile.risk_level_numeric:
                aligned_numeric = request.risk_alignment.aligned_risk_level.value
                if request.fund_risk_profile.risk_level_numeric < aligned_numeric:
                    tokens.append("R-COND-1")

        # R-COND-2: Goal Horizon Mismatch Concern (Contextual check without arbitrary cutoff)
        fund_cat = "UNKNOWN"
        if request.fund_quality_dataset:
            fund_cat = request.fund_quality_dataset.category_context.category
        elif request.fund_quality_score:
            fund_cat = request.fund_quality_score.category

        if request.goal_profile and request.goal_profile.effective_horizon_years is not None:
            if request.goal_profile.effective_horizon_years < 3.0 and fund_cat == "Equity":
                concerns.append("Goal horizon mismatch with high volatility equity category (R-COND-2)")
                tokens.append("R-COND-2")
                penalties.append(0.15)

        # R-COND-3: Material Security Overlap (Contextual check)
        if request.portfolio_context and request.portfolio_context.is_provided:
            if request.portfolio_context.security_overlap_pct and request.portfolio_context.security_overlap_pct > 0.30:
                concerns.append(f"Material security overlap of {request.portfolio_context.security_overlap_pct*100:.1f}% (R-COND-3)")
                tokens.append("R-COND-3")
                penalties.append(0.10)

        # R-COND-4: High AMC Exposure (Contextual check)
        if request.portfolio_context and request.portfolio_context.is_provided:
            if request.portfolio_context.amc_concentration_pct and request.portfolio_context.amc_concentration_pct > 0.40:
                concerns.append(f"High AMC concentration of {request.portfolio_context.amc_concentration_pct*100:.1f}% (R-COND-4)")
                tokens.append("R-COND-4")
                penalties.append(0.10)

        # R-COND-5: Immature Fund History (Consumed from upstream Fund Maturity)
        is_immature = False
        if request.fund_quality_dataset and hasattr(request.fund_quality_dataset.metrics, "maturity_tier"):
            if str(request.fund_quality_dataset.metrics.maturity_tier).endswith("IMMATURE"):
                is_immature = True
        elif request.fund_quality_score and getattr(request.fund_quality_score, "is_provisional", False):
            is_immature = True

        if is_immature:
            tokens.append("R-COND-5")
            penalties.append(0.15)
            if len(concerns) > 0:
                concerns.append("Immature fund track record combined with contextual concern (R-COND-5)")

        # Partial or Stale Upstream Risk Alignment
        if request.risk_alignment and request.risk_alignment.alignment_status == AlignmentStatus.PARTIAL_ALIGNMENT:
            concerns.append("Upstream Risk Alignment is partial (R-INF-PARTIAL)")
            tokens.append("R-INF-PARTIAL")
            penalties.append(0.15)
        elif request.risk_alignment and request.risk_alignment.is_stale_input:
            concerns.append("Upstream Risk Alignment is stale (>90 days) (R-INF-STALE)")
            tokens.append("R-INF-STALE")
            penalties.append(0.15)

        return concerns, tokens, penalties

    def _compute_base_confidence(self, request: SuitabilityEvaluationRequest) -> float:
        """Computes base evidence confidence without arbitrary formulas."""
        conf = 1.0
        if request.risk_alignment:
            conf = min(conf, request.risk_alignment.alignment_confidence_score)
        if request.fund_quality_dataset:
            conf = min(conf, request.fund_quality_dataset.confidence_score)
        elif request.fund_quality_score:
            conf = min(conf, request.fund_quality_score.confidence_score)
        return conf

    def _build_result(
        self,
        assessment_id: str,
        request: SuitabilityEvaluationRequest,
        obs_date: date,
        timestamp_utc: datetime,
        status: SuitabilityStatus,
        eval_state: SuitabilityEvaluationState,
        rejection_reasons: List[str],
        constraints_applied: List[str],
        summary: str,
        confidence: float
    ) -> SuitabilityAssessmentResult:
        """Builds immutable SuitabilityAssessmentResult data contract."""
        investor_id = request.investor_profile.investor_id if request.investor_profile else "UNKNOWN"
        profile_version = request.investor_profile.profile_version if request.investor_profile else "1.0.0"
        
        scheme_id = "UNKNOWN"
        amfi_code = "UNKNOWN"
        scheme_name = "UNKNOWN"
        category = "UNKNOWN"
        subcategory = "UNKNOWN"
        fq_confidence = 1.0

        if request.fund_quality_dataset:
            scheme_id = request.fund_quality_dataset.canonical_scheme_id
            amfi_code = request.fund_quality_dataset.amfi_code
            scheme_name = request.fund_quality_dataset.scheme_name
            category = request.fund_quality_dataset.category_context.category
            subcategory = request.fund_quality_dataset.category_context.subcategory
            fq_confidence = request.fund_quality_dataset.confidence_score
        elif request.fund_quality_score:
            scheme_id = request.fund_quality_score.canonical_scheme_id
            amfi_code = request.fund_quality_score.amfi_code
            scheme_name = request.fund_quality_score.scheme_name
            category = request.fund_quality_score.category
            subcategory = request.fund_quality_score.subcategory
            fq_confidence = request.fund_quality_score.confidence_score

        goal_id = request.goal_profile.goal_id if request.goal_profile else None
        
        effective_risk = request.risk_alignment.aligned_risk_level.name if (request.risk_alignment and request.risk_alignment.aligned_risk_level) else None
        cap_result = request.risk_alignment.risk_capacity_level.name if (request.risk_alignment and request.risk_alignment.risk_capacity_level) else None
        tol_result = request.risk_alignment.risk_tolerance_level.name if (request.risk_alignment and request.risk_alignment.risk_tolerance_level) else None

        prov = ProvenanceMetadata(
            source_id="suitability_engine.py",
            source_document_url="file:///d:/AI%20Portfolio/mutual-fund-decision-engine/risk/suitability_engine.py",
            retrieval_timestamp_utc=timestamp_utc,
            methodology_version=self.METHODOLOGY_VERSION
        )

        return SuitabilityAssessmentResult(
            assessment_id=assessment_id,
            investor_id=investor_id,
            profile_version_used=profile_version,
            canonical_scheme_id=scheme_id,
            amfi_code=amfi_code,
            scheme_name=scheme_name,
            category=category,
            subcategory=subcategory,
            observation_date=obs_date,
            suitability_status=status,
            goal_id=goal_id,
            effective_risk_alignment=effective_risk,
            risk_capacity_result=cap_result,
            risk_tolerance_result=tol_result,
            max_permissible_asset_risk=effective_risk,
            effective_horizon_years=request.goal_profile.effective_horizon_years if request.goal_profile else None,
            is_horizon_compatible=True if "R-COND-2" not in constraints_applied else False,
            is_liquidity_compatible=True,
            fund_quality_score_consumed=request.fund_quality_score.quality_score if request.fund_quality_score else None,
            fund_quality_confidence_consumed=fq_confidence,
            suitability_confidence_score=confidence,
            constraints_applied=constraints_applied,
            rejection_reasons=rejection_reasons,
            summary_explanation=summary,
            provenance=prov,
            assessment_timestamp_utc=timestamp_utc,
            methodology_version=self.METHODOLOGY_VERSION,
            rule_version=self.RULE_VERSION
        )
