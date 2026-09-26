"""
Action Decision Engine Models & Data Contracts (Phase F.6 / F.6.1 / F.6.2)

Defines data contracts, enums, evaluation context, and assessment outputs for the Action Decision Engine.

Architecture:
DATA -> METRIC ENGINE -> FUND QUALITY -> SUITABILITY -> PORTFOLIO NEED -> ECONOMIC BENEFIT -> ACTION

Governance Rules Enforced:
- Action orchestrates upstream evidence (Fund Quality, Suitability, Portfolio Need, Economic Benefit).
- Action does NOT recalculate any upstream financial engine outputs.
- Action does NOT own statutory tax rules or exit-load schedules.
- Action is a read-only analytical recommendation layer; it does NOT execute broker transactions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any

from models.suitability_assessment import SuitabilityAssessmentResult, SuitabilityStatus
from portfolio.need_models import (
    PortfolioNeedAssessmentResult,
    PortfolioNeedState,
    CandidateFulfillmentStatus,
    AffordabilityStatus,
)


class ActionState(Enum):
    BUY = "BUY"
    ACCUMULATE = "ACCUMULATE"
    HOLD = "HOLD"
    MONITOR = "MONITOR"
    REVIEW = "REVIEW"
    SELL = "SELL"
    NO_ACTION = "NO_ACTION"
    INVALID_ASSESSMENT = "INVALID_ASSESSMENT"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"


class PositionContext(Enum):
    NEW_POSITION = "NEW_POSITION"
    EXISTING_POSITION = "EXISTING_POSITION"


class InformationSufficiency(Enum):
    SUFFICIENT = "SUFFICIENT"
    PARTIAL = "PARTIAL"
    INSUFFICIENT = "INSUFFICIENT"


class ReasonCode(Enum):
    NO_PORTFOLIO_NEED = "NO_PORTFOLIO_NEED"
    NEED_IDENTIFIED = "NEED_IDENTIFIED"
    CANDIDATE_NOT_SUITABLE = "CANDIDATE_NOT_SUITABLE"
    CANDIDATE_CANNOT_FULFILL_NEED = "CANDIDATE_CANNOT_FULFILL_NEED"
    CANDIDATE_FULFILLMENT_UNKNOWN = "CANDIDATE_FULFILLMENT_UNKNOWN"
    ECONOMIC_BENEFIT_UNKNOWN = "ECONOMIC_BENEFIT_UNKNOWN"
    TAX_COST_INFORMATION_MISSING = "TAX_COST_INFORMATION_MISSING"
    EXIT_LOAD_INFORMATION_MISSING = "EXIT_LOAD_INFORMATION_MISSING"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    MATERIAL_REVIEW_SIGNAL = "MATERIAL_REVIEW_SIGNAL"
    LOW_ACTIONABILITY = "LOW_ACTIONABILITY"
    HOLD_DEFAULT = "HOLD_DEFAULT"
    SWITCH_NOT_JUSTIFIED = "SWITCH_NOT_JUSTIFIED"
    POSITIVE_PORTFOLIO_NEED = "POSITIVE_PORTFOLIO_NEED"
    AFFORDABILITY_CONSTRAINED = "AFFORDABILITY_CONSTRAINED"
    INVALID_INPUT = "INVALID_INPUT"
    INSUFFICIENT_INPUT = "INSUFFICIENT_INPUT"
    STALE_INPUT = "STALE_INPUT"
    CATEGORY_CONCENTRATION_EXCEEDED = "CATEGORY_CONCENTRATION_EXCEEDED"
    HIGH_SECURITY_OVERLAP = "HIGH_SECURITY_OVERLAP"
    NO_SUITABLE_REPLACEMENT = "NO_SUITABLE_REPLACEMENT"
    TEMPORARY_UNDERPERFORMANCE = "TEMPORARY_UNDERPERFORMANCE"
    MACRO_STRESS_CONTEXT = "MACRO_STRESS_CONTEXT"
    UNVALIDATED_DETERIORATION = "UNVALIDATED_DETERIORATION"


@dataclass
class ActionEvaluationContext:
    """
    Mutable evaluation context containing upstream assessment results and context nodes
    supplied to the Action Decision Engine.
    """
    investor_id: str
    scheme_id: str
    position_context: PositionContext
    goal_id: Optional[str] = None
    portfolio_id: Optional[str] = None
    fund_quality_assessment_id: Optional[str] = None
    fund_quality_score: Optional[float] = None
    fund_quality_confidence: Optional[float] = None
    fund_quality_evidence_valid: Optional[bool] = None
    suitability_result: Optional[SuitabilityAssessmentResult] = None
    portfolio_need_result: Optional[PortfolioNeedAssessmentResult] = None
    economic_benefit_state: Optional[str] = "BENEFIT_UNCERTAIN"  # Canonical F.5 states: ECONOMICALLY_BENEFICIAL, ECONOMICALLY_NOT_BENEFICIAL, ECONOMICALLY_NEUTRAL, NO_EVALUABLE_CHANGE, BENEFIT_UNCERTAIN, INSUFFICIENT_INFORMATION, INVALID_ASSESSMENT
    tax_liability_known: Optional[bool] = None
    exit_load_known: Optional[bool] = None
    transaction_costs_known: Optional[bool] = None
    is_stale_input: bool = False
    deterioration_signal: Optional[str] = None  # MATERIAL_DETERIORATION, MILD_DETERIORATION, TEMPORARY_UNDERPERFORMANCE, NONE
    deterioration_validated: Optional[bool] = None  # True if deterioration methodology is governed/validated
    has_suitable_replacement: Optional[bool] = None
    fund_quality_comparison_valid: Optional[bool] = None  # True if candidate and holding Fund Quality scores are validly comparable
    macro_stress_flag: bool = False
    observation_timestamp: Optional[datetime] = None


@dataclass(frozen=True)
class ActionAssessmentResult:
    """
    Immutable data contract representing the reproducible Action Decision Result.

    Note on action_confidence:
    `action_confidence` represents an evidence-sufficiency and structural actionability indicator
    reflecting the completeness of decision inputs (1.0 = fully sufficient, 0.5-0.8 = constrained/partial, 0.0 = insufficient).
    It is NOT a statistical probability of financial correctness, does NOT claim empirical calibration,
    does NOT override upstream Fund Quality or Suitability confidence, and is NOT used as a numerical cutoff to filter actions.
    """
    assessment_id: str
    investor_id: str
    scheme_id: str
    position_context: PositionContext
    action_state: ActionState
    information_sufficiency: InformationSufficiency
    actionability_status: str
    action_confidence: float
    primary_reason_code: str
    reason_codes: List[str] = field(default_factory=list)
    explanation: str = ""
    warnings: List[str] = field(default_factory=list)
    goal_id: Optional[str] = None
    portfolio_id: Optional[str] = None
    upstream_assessment_ids: Dict[str, str] = field(default_factory=dict)
    observation_timestamp: Optional[datetime] = None
    methodology_version: str = "F.6.2"
    rule_version: str = "1.0.0"

    def __post_init__(self):
        if not self.assessment_id or not self.assessment_id.strip():
            raise ValueError("assessment_id cannot be empty")
        if not self.investor_id or not self.investor_id.strip():
            raise ValueError("investor_id cannot be empty")
        if not self.scheme_id or not self.scheme_id.strip():
            raise ValueError("scheme_id cannot be empty")
        if self.action_confidence < 0.0 or self.action_confidence > 1.0:
            raise ValueError(f"action_confidence must be between 0.0 and 1.0, got {self.action_confidence}")
