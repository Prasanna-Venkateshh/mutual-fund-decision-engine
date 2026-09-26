"""
Integration Data Contracts & Typed Assessment References (Phase F.7.2).

Defines frozen, versioned, provenance-preserving data contracts and enums for hand-offs
between governed decision domains:
DATA -> METRIC ENGINE -> FUND QUALITY -> RISK CAPACITY -> RISK TOLERANCE -> RISK ALIGNMENT -> SUITABILITY -> PORTFOLIO NEED -> ECONOMIC BENEFIT -> ACTION

Governance Rules Enforced:
- Cross-domain contracts carry upstream outputs ONLY; they MUST NOT calculate or recreate financial methodology.
- Dataclasses are immutable (frozen=True).
- Preserves full auditability, versioning, confidence, and provenance.
- Enforces canonical F.5 Economic Benefit states (rejects non-canonical state strings).
- Strictly preserves canonical scheme identity and upstream assessment IDs.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import List, Optional, Dict, Any

from models.fund_quality_dataset import ProvenanceMetadata
from models.investor_profile import RiskCapacityLevel, RiskToleranceLevel
from risk.capacity_models import AssessmentStatus
from risk.tolerance_models import BehavioralConsistencyLevel
from risk.alignment_models import AlignmentStatus, LimitingConstraint, AlignedRiskLevel
from models.suitability_assessment import SuitabilityStatus
from portfolio.need_models import (
    PortfolioNeedState,
    CandidateFulfillmentStatus,
    AffordabilityStatus,
    FundingStatus,
    ExposureGapDirection,
)
from action.models import PositionContext, ActionState


class AssessmentType(Enum):
    """Enumeration of governed decision domain assessment types."""
    FUND_QUALITY = "FUND_QUALITY"
    RISK_CAPACITY = "RISK_CAPACITY"
    RISK_TOLERANCE = "RISK_TOLERANCE"
    RISK_ALIGNMENT = "RISK_ALIGNMENT"
    SUITABILITY = "SUITABILITY"
    PORTFOLIO_NEED = "PORTFOLIO_NEED"
    ECONOMIC_BENEFIT = "ECONOMIC_BENEFIT"
    ACTION = "ACTION"


class IntegrationStatus(Enum):
    """
    Integration-level contract validity and evidence sufficiency status.

    - VALID: Complete evidence lineage; mandatory upstream assessments pass validation and are compatible.
    - PARTIAL: Non-fatal optional inputs missing (e.g. optional goal/exposure context); downstream evaluation permitted with warnings.
    - UNKNOWN: Evidence sufficiency cannot be established.
    - INVALID: Mandatory input missing, version mismatch, corrupted assessment, or prohibited state.
    """
    VALID = "VALID"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"
    INVALID = "INVALID"


class EconomicBenefitState(Enum):
    """
    Canonical Economic Benefit vocabulary established in Phase F.5.

    The Economic Benefit domain owns economic comparison, switching math, tax liability rules,
    exit load schedules, and expected return improvement.
    Integration contracts MUST ONLY consume these canonical states.
    Parallel taxonomies (HIGH_BENEFIT, ACTION_BENEFICIAL, etc.) are strictly prohibited.
    """
    ECONOMICALLY_BENEFICIAL = "ECONOMICALLY_BENEFICIAL"
    ECONOMICALLY_NOT_BENEFICIAL = "ECONOMICALLY_NOT_BENEFICIAL"
    ECONOMICALLY_NEUTRAL = "ECONOMICALLY_NEUTRAL"
    NO_EVALUABLE_CHANGE = "NO_EVALUABLE_CHANGE"
    BENEFIT_UNCERTAIN = "BENEFIT_UNCERTAIN"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"
    INVALID_ASSESSMENT = "INVALID_ASSESSMENT"


@dataclass(frozen=True)
class CanonicalAssessmentReference:
    """
    Common immutable reference structure for tracking upstream assessment lineage.

    - Domain Owner: Governance & Data Infrastructure
    - Represents: Historical lineage reference for an individual domain assessment output.
    - Must NOT Calculate: Any financial score, tier, or decision rule.
    - Boundary Rationale: Decouples upstream assessment identity and point-in-time metadata from downstream consumption logic.
    """
    assessment_id: str
    assessment_type: AssessmentType
    investor_id: Optional[str] = None
    profile_version: Optional[str] = None
    goal_id: Optional[str] = None
    portfolio_id: Optional[str] = None
    scheme_id: Optional[str] = None
    observation_date: Optional[date] = None
    assessment_timestamp_utc: Optional[datetime] = None
    methodology_version: str = "1.0.0"
    rule_version: str = "1.0.0"
    config_version: Optional[str] = None
    status: IntegrationStatus = IntegrationStatus.VALID
    confidence: Optional[float] = None
    provenance_references: List[str] = field(default_factory=list)
    source_references: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.assessment_id or not self.assessment_id.strip():
            raise ValueError("assessment_id cannot be empty")
        if not isinstance(self.assessment_type, AssessmentType):
            raise ValueError(f"assessment_type must be an AssessmentType enum, got {type(self.assessment_type)}")
        if self.confidence is not None and (self.confidence < 0.0 or self.confidence > 1.0):
            raise ValueError(f"confidence must be between 0.0 and 1.0, got {self.confidence}")


@dataclass(frozen=True)
class FundQualityIntegrationContract:
    """
    Typed hand-off contract for Fund Quality assessment outputs.

    - Domain Owner: Fund Quality Domain (`QualityEngine`)
    - Represents: Upstream scheme quality score, confidence, maturity, and score comparability flags.
    - Must NOT Calculate: Fund Quality score, peer normalizations, confidence score, or score comparability.
    - Boundary Rationale: Ensures Action and Suitability consume governed quality outputs without recalculating scheme metrics.
    """
    reference: CanonicalAssessmentReference
    canonical_scheme_id: str
    category: str
    subcategory: str
    plan_type: str
    option_type: str
    fund_quality_score: Optional[float] = None
    fund_quality_confidence: Optional[float] = None
    fund_maturity_months: Optional[int] = None
    fund_quality_evidence_valid: Optional[bool] = None
    fund_quality_comparison_valid: Optional[bool] = None
    methodology_version: str = "1.0.0"
    config_version: Optional[str] = None
    provenance: Optional[ProvenanceMetadata] = None

    def __post_init__(self):
        if not self.canonical_scheme_id or not self.canonical_scheme_id.strip():
            raise ValueError("canonical_scheme_id cannot be empty")
        if self.fund_quality_confidence is not None and (self.fund_quality_confidence < 0.0 or self.fund_quality_confidence > 1.0):
            raise ValueError(f"fund_quality_confidence must be between 0.0 and 1.0, got {self.fund_quality_confidence}")


@dataclass(frozen=True)
class RiskCapacityIntegrationContract:
    """
    Typed hand-off contract for Risk Capacity assessment outputs.

    - Domain Owner: Risk Capacity Domain (`RiskCapacityEngine`)
    - Represents: Financial risk capacity tier, binding financial constraints, and assessment status.
    - Must NOT Calculate: Debt ratios, emergency reserve ratios, cash surplus ratios, or capacity tiers.
    - Boundary Rationale: Isolate financial capacity logic from psychological risk tolerance and fund quality.
    """
    reference: CanonicalAssessmentReference
    investor_id: str
    risk_capacity_level: Optional[RiskCapacityLevel] = None
    binding_constraint_name: Optional[str] = None
    status: AssessmentStatus = AssessmentStatus.COMPLETE
    confidence_score: float = 1.0
    provenance: Optional[ProvenanceMetadata] = None
    methodology_version: str = "1.0.0"
    rule_version: str = "1.0.0"

    def __post_init__(self):
        if not self.investor_id or not self.investor_id.strip():
            raise ValueError("investor_id cannot be empty")


@dataclass(frozen=True)
class RiskToleranceIntegrationContract:
    """
    Typed hand-off contract for Risk Tolerance assessment outputs.

    - Domain Owner: Risk Tolerance Domain (`RiskToleranceEngine`)
    - Represents: Psychometric risk tolerance tier, behavioral consistency level, and assessment status.
    - Must NOT Calculate: Questionnaire scoring, loss acceptance math, or behavioral consistency scores.
    - Boundary Rationale: Keep psychological tolerance completely independent of financial capacity and fund performance.
    """
    reference: CanonicalAssessmentReference
    investor_id: str
    risk_tolerance_level: Optional[RiskToleranceLevel] = None
    consistency_level: BehavioralConsistencyLevel = BehavioralConsistencyLevel.UNKNOWN
    status: AssessmentStatus = AssessmentStatus.COMPLETE
    confidence_score: float = 1.0
    provenance: Optional[ProvenanceMetadata] = None
    methodology_version: str = "1.0.0"
    rule_version: str = "1.0.0"

    def __post_init__(self):
        if not self.investor_id or not self.investor_id.strip():
            raise ValueError("investor_id cannot be empty")


@dataclass(frozen=True)
class RiskAlignmentIntegrationContract:
    """
    Typed hand-off contract for Risk Alignment assessment outputs.

    - Domain Owner: Risk Alignment Domain (`RiskAlignmentEngine`)
    - Represents: Governed lower-of-two aligned risk tier, alignment status, and limiting constraint.
    - Must NOT Calculate: Min(Capacity, Tolerance) logic, capacity evaluation, or tolerance evaluation.
    - Boundary Rationale: Provide a single unified aligned risk contract to Suitability while preserving constituent lineage.
    """
    reference: CanonicalAssessmentReference
    investor_id: str
    alignment_status: AlignmentStatus = AlignmentStatus.FULLY_ALIGNED
    limiting_constraint: LimitingConstraint = LimitingConstraint.NONE
    aligned_risk_level: Optional[AlignedRiskLevel] = None
    capacity_assessment_id: Optional[str] = None
    tolerance_assessment_id: Optional[str] = None
    alignment_confidence_score: float = 1.0
    is_stale_input: bool = False
    provenance: Optional[ProvenanceMetadata] = None
    methodology_version: str = "1.0.0"
    rule_version: str = "1.0.0"

    def __post_init__(self):
        if not self.investor_id or not self.investor_id.strip():
            raise ValueError("investor_id cannot be empty")


@dataclass(frozen=True)
class SuitabilityIntegrationContract:
    """
    Typed hand-off contract for Suitability assessment outputs.

    - Domain Owner: Suitability Domain (`SuitabilityEngine`)
    - Represents: Governed Suitability Status (SUITABLE, NOT_SUITABLE, etc.), constraints, and rejection reasons.
    - Must NOT Calculate: Risk alignment checking, horizon compatibility math, or suitability decision rules.
    - Boundary Rationale: Encapsulates investor/fund/goal compatibility without leaking suitability logic into Portfolio Need or Action.
    """
    reference: CanonicalAssessmentReference
    investor_id: str
    canonical_scheme_id: str
    goal_id: Optional[str] = None
    suitability_status: SuitabilityStatus = SuitabilityStatus.SUITABLE
    constraints_applied: List[str] = field(default_factory=list)
    rejection_reasons: List[str] = field(default_factory=list)
    suitability_confidence_score: float = 1.0
    effective_horizon_years: Optional[float] = None
    is_horizon_compatible: Optional[bool] = None
    is_liquidity_compatible: Optional[bool] = None
    provenance: Optional[ProvenanceMetadata] = None
    methodology_version: str = "1.0.0"
    rule_version: str = "1.0.0"

    def __post_init__(self):
        if not self.investor_id or not self.investor_id.strip():
            raise ValueError("investor_id cannot be empty")
        if not self.canonical_scheme_id or not self.canonical_scheme_id.strip():
            raise ValueError("canonical_scheme_id cannot be empty")


@dataclass(frozen=True)
class PortfolioNeedIntegrationContract:
    """
    Typed hand-off contract for Portfolio Need assessment outputs.

    - Domain Owner: Portfolio Need Domain (`PortfolioNeedEngine`)
    - Represents: Portfolio Need state, candidate fulfillment status, affordability status, and exposure gaps.
    - Must NOT Calculate: Target allocation gaps, funding gap ratios, candidate fulfillment checks, or affordability rules.
    - Boundary Rationale: Decouples goal-centric portfolio gaps from individual scheme suitability and economic benefit math.
    """
    reference: CanonicalAssessmentReference
    investor_id: str
    goal_id: Optional[str] = None
    portfolio_snapshot_id: Optional[str] = None
    candidate_scheme_id: Optional[str] = None
    need_state: PortfolioNeedState = PortfolioNeedState.NEED_IDENTIFIED
    candidate_fulfillment: CandidateFulfillmentStatus = CandidateFulfillmentStatus.CANDIDATE_CAN_FULFILL_NEED
    affordability_status: AffordabilityStatus = AffordabilityStatus.AFFORDABLE
    funding_status: FundingStatus = FundingStatus.ADEQUATELY_FUNDED
    exposure_gap_direction: Optional[ExposureGapDirection] = None
    exposure_gap_pct: Optional[float] = None
    provenance: Optional[ProvenanceMetadata] = None
    methodology_version: str = "1.0.0"
    rule_version: str = "1.0.0"

    def __post_init__(self):
        if not self.investor_id or not self.investor_id.strip():
            raise ValueError("investor_id cannot be empty")


@dataclass(frozen=True)
class EconomicBenefitIntegrationContract:
    """
    Typed hand-off contract for Economic Benefit assessment outputs.

    - Domain Owner: Economic Benefit Domain (`EconomicBenefitEngine`)
    - Represents: Canonical F.5 Economic Benefit state, actionability, evidence sufficiency, and cost/tax evidence status.
    - Must NOT Calculate: Statutory tax liability, exit load schedules, transaction cost math, or return improvement deltas.
    - Boundary Rationale: Centralizes switching economics and cost/tax verification in Economic Benefit domain, keeping Action clean.
    """
    reference: CanonicalAssessmentReference
    investor_id: str
    position_context: str = "NEW_POSITION"
    current_holding_scheme_id: Optional[str] = None
    candidate_scheme_id: Optional[str] = None
    economic_benefit_state: EconomicBenefitState = EconomicBenefitState.BENEFIT_UNCERTAIN
    economic_benefit_actionable: Optional[bool] = None
    evidence_sufficiency_valid: Optional[bool] = None
    expected_improvement_status: Optional[str] = None
    cost_tax_evidence_status: Optional[str] = None
    provenance: Optional[ProvenanceMetadata] = None
    methodology_version: str = "F.5.0"
    rule_version: str = "1.0.0"
    config_version: Optional[str] = None

    def __post_init__(self):
        if not self.investor_id or not self.investor_id.strip():
            raise ValueError("investor_id cannot be empty")
        if not isinstance(self.economic_benefit_state, EconomicBenefitState):
            raise ValueError(
                f"economic_benefit_state must be a canonical EconomicBenefitState enum, got {type(self.economic_benefit_state)}"
            )


@dataclass(frozen=True)
class ActionInputIntegrationContract:
    """
    Formal typed input payload consumed by the Action Decision orchestrator.

    - Domain Owner: Action Decision Domain (`ActionEngine`) / Integration Layer
    - Represents: Composition of all upstream domain integration contracts into a single validated decision payload.
    - Must NOT Calculate: Upstream scoring, suitability rules, portfolio need math, tax rates, or economic benefit states.
    - Boundary Rationale: Provides a structured, immutable, provenance-preserving contract for final decision orchestration.
    """
    assessment_reference: CanonicalAssessmentReference
    investor_id: str
    scheme_id: str
    position_context: PositionContext
    goal_id: Optional[str] = None
    portfolio_id: Optional[str] = None
    fund_quality_contract: Optional[FundQualityIntegrationContract] = None
    risk_alignment_contract: Optional[RiskAlignmentIntegrationContract] = None
    suitability_contract: Optional[SuitabilityIntegrationContract] = None
    portfolio_need_contract: Optional[PortfolioNeedIntegrationContract] = None
    economic_benefit_contract: Optional[EconomicBenefitIntegrationContract] = None
    deterioration_signal: Optional[str] = None
    deterioration_validated: Optional[bool] = None
    has_suitable_replacement: Optional[bool] = None
    fund_quality_comparison_valid: Optional[bool] = None
    macro_stress_flag: bool = False
    integration_status: IntegrationStatus = IntegrationStatus.VALID
    actionability_status: str = "HIGH_ACTIONABILITY"
    validation_messages: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.investor_id or not self.investor_id.strip():
            raise ValueError("investor_id cannot be empty")
        if not self.scheme_id or not self.scheme_id.strip():
            raise ValueError("scheme_id cannot be empty")


@dataclass(frozen=True)
class EndToEndDecisionResult:
    """
    Immutable data contract representing the final end-to-end decision result generated by DecisionOrchestrator.

    - Domain Owner: End-to-End Decision Integration Domain (`DecisionOrchestrator`)
    - Represents: Governed composition of all upstream domain assessment outputs into a final Fund + Portfolio Decision.
    - Must NOT Calculate: Upstream scoring, risk ratios, suitability rules, gap math, tax rates, or economic return logic.
    - Boundary Rationale: Encapsulates final decision outcome, blocking reasons, explanation, version metadata, and full provenance.
    """
    assessment_id: str
    investor_id: str
    scheme_id: str
    final_action_state: ActionState
    final_decision_status: IntegrationStatus
    goal_id: Optional[str] = None
    portfolio_id: Optional[str] = None
    upstream_assessment_ids: Dict[str, str] = field(default_factory=dict)
    final_explanation: str = ""
    blocking_reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    provenance: Optional[ProvenanceMetadata] = None
    observation_timestamp: Optional[datetime] = None
    decision_timestamp_utc: Optional[datetime] = None
    methodology_versions: Dict[str, str] = field(default_factory=dict)
    rule_versions: Dict[str, str] = field(default_factory=dict)
    config_versions: Dict[str, str] = field(default_factory=dict)
    orchestrator_version: str = "F.7.3"

    def __post_init__(self):
        if not self.assessment_id or not self.assessment_id.strip():
            raise ValueError("assessment_id cannot be empty")
        if not self.investor_id or not self.investor_id.strip():
            raise ValueError("investor_id cannot be empty")
        if not self.scheme_id or not self.scheme_id.strip():
            raise ValueError("scheme_id cannot be empty")

