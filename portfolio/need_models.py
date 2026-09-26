"""
Portfolio Need Models & Data Contracts (Phase F.4.2 / F.4.2.1 / F.4.3.2 / F.4.4)

Defines data contracts, snapshots, and assessment outputs for the Portfolio Need / Goal Need subsystem.

Architecture:
DATA -> METRIC ENGINE -> FUND QUALITY -> SUITABILITY -> PORTFOLIO NEED -> ECONOMIC BENEFIT -> ACTION

Governance Rules Enforced:
- Portfolio Need consumes upstream Risk Capacity, Risk Tolerance, Risk Alignment, Fund Quality, and Suitability results.
- Portfolio Need does NOT recalculate any upstream financial engine outputs.
- Portfolio Need does NOT create transaction recommendations (BUY, SELL, REBALANCE, SWITCH).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any

from models.suitability_assessment import SuitabilityAssessmentResult


class PortfolioNeedState(Enum):
    NEED_IDENTIFIED = "NEED_IDENTIFIED"
    NO_MATERIAL_NEED = "NO_MATERIAL_NEED"
    EXCESS_EXPOSURE = "EXCESS_EXPOSURE"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"
    INVALID_ASSESSMENT = "INVALID_ASSESSMENT"


class CandidateFulfillmentStatus(Enum):
    CANDIDATE_CAN_FULFILL_NEED = "CANDIDATE_CAN_FULFILL_NEED"
    CANDIDATE_CANNOT_FULFILL_NEED = "CANDIDATE_CANNOT_FULFILL_NEED"
    CANDIDATE_FULFILLMENT_UNKNOWN = "CANDIDATE_FULFILLMENT_UNKNOWN"


class AffordabilityStatus(Enum):
    AFFORDABLE = "AFFORDABLE"
    AFFORDABILITY_CONSTRAINED = "AFFORDABILITY_CONSTRAINED"
    AFFORDABILITY_STATUS_UNKNOWN = "AFFORDABILITY_STATUS_UNKNOWN"


class FundingStatus(Enum):
    ADEQUATELY_FUNDED = "ADEQUATELY_FUNDED"
    PARTIALLY_FUNDED = "PARTIALLY_FUNDED"
    UNDERFUNDED = "UNDERFUNDED"
    OVERFUNDED = "OVERFUNDED"
    UNKNOWN_FUNDING = "UNKNOWN_FUNDING"


class ExposureGapDirection(Enum):
    POSITIVE_GAP = "POSITIVE_GAP"
    BALANCED_EXPOSURE = "BALANCED_EXPOSURE"
    NEGATIVE_GAP = "NEGATIVE_GAP"
    UNKNOWN_ALLOCATION = "UNKNOWN_ALLOCATION"


@dataclass(frozen=True)
class GoalFundingSnapshot:
    goal_id: str
    investor_id: str
    target_amount: Optional[float] = None
    target_date: Optional[datetime] = None
    current_corpus: Optional[float] = None
    funding_status: FundingStatus = FundingStatus.UNKNOWN_FUNDING
    horizon_years: Optional[float] = None
    observation_date: Optional[datetime] = None


@dataclass(frozen=True)
class PortfolioHoldingRecord:
    """
    Granular portfolio holding record representing an ingested portfolio position.
    
    Serves as the detailed record underlying PortfolioExposureSnapshot without duplicating
    downstream portfolio exposure contracts.
    """
    holding_id: str
    portfolio_snapshot_id: str
    investor_id: str
    canonical_scheme_id: str
    units: float
    source_provenance: Dict[str, Any] = field(default_factory=dict)
    amfi_code: Optional[str] = None
    isin: Optional[str] = None
    scheme_name_raw: Optional[str] = None
    cost_basis_amount: Optional[float] = None
    current_nav: Optional[float] = None
    current_value: Optional[float] = None
    acquisition_date: Optional[datetime] = None
    plan_type: Optional[str] = None
    option_type: Optional[str] = None
    goal_id: Optional[str] = None


@dataclass(frozen=True)
class PortfolioExposureSnapshot:
    portfolio_snapshot_id: str
    investor_id: str
    holding_ids: List[str] = field(default_factory=list)
    canonical_scheme_ids: List[str] = field(default_factory=list)
    total_valuation: Optional[float] = None
    is_valuation_available: bool = True
    observation_date: Optional[datetime] = None


@dataclass(frozen=True)
class ExposureGap:
    current_exposure_pct: Optional[float] = None
    reference_exposure_pct: Optional[float] = None
    gap_pct: Optional[float] = None
    gap_direction: ExposureGapDirection = ExposureGapDirection.UNKNOWN_ALLOCATION
    observation_date: Optional[datetime] = None


@dataclass(frozen=True)
class AllocationContext:
    target_allocation_pct: Optional[float] = None
    current_allocation_pct: Optional[float] = None
    exposure_gap: Optional[ExposureGap] = None
    observation_date: Optional[datetime] = None


@dataclass(frozen=True)
class FundingGap:
    target_amount: Optional[float] = None
    current_corpus: Optional[float] = None
    funding_gap_amount: Optional[float] = None
    funding_status: FundingStatus = FundingStatus.UNKNOWN_FUNDING
    observation_date: Optional[datetime] = None


@dataclass(frozen=True)
class AffordabilityContext:
    affordability_status: AffordabilityStatus = AffordabilityStatus.AFFORDABILITY_STATUS_UNKNOWN
    comfortable_monthly_capacity: Optional[float] = None
    required_monthly_contribution: Optional[float] = None
    upstream_assessment_id: Optional[str] = None
    observation_date: Optional[datetime] = None


@dataclass(frozen=True)
class PortfolioLookThroughContext:
    is_category_overexposed: bool = False
    has_high_security_overlap: bool = False
    look_through_confidence: float = 1.0
    observation_date: Optional[datetime] = None


@dataclass(frozen=True)
class FundCandidateContext:
    canonical_scheme_id: str
    asset_class: Optional[str] = None
    category: Optional[str] = None
    suitability_result: Optional[SuitabilityAssessmentResult] = None
    suitability_assessment_id: Optional[str] = None
    fund_quality_assessment_id: Optional[str] = None
    risk_alignment_assessment_id: Optional[str] = None
    is_capable_of_fulfilling_need: Optional[bool] = None
    observation_date: Optional[datetime] = None


@dataclass(frozen=True)
class MultiGoalContext:
    goal_snapshots: List[GoalFundingSnapshot] = field(default_factory=list)
    shared_capital_amount: Optional[float] = None
    observation_date: Optional[datetime] = None


@dataclass(frozen=True)
class GeneralWealthContext:
    is_general_wealth: bool = True
    allocation_context: Optional[AllocationContext] = None
    observation_date: Optional[datetime] = None


@dataclass(frozen=True)
class PortfolioNeedAssessmentResult:
    assessment_id: str
    investor_id: str
    goal_id: Optional[str]
    scheme_id: Optional[str]
    primary_state: PortfolioNeedState
    candidate_fulfillment_status: CandidateFulfillmentStatus
    affordability_status: AffordabilityStatus
    contextual_flags: List[str] = field(default_factory=list)
    funding_status: FundingStatus = FundingStatus.UNKNOWN_FUNDING
    allocation_status: ExposureGapDirection = ExposureGapDirection.UNKNOWN_ALLOCATION
    exposure_gap: Optional[ExposureGap] = None
    funding_gap: Optional[FundingGap] = None
    confidence_score: float = 1.0
    triggered_rule_ids: List[str] = field(default_factory=list)
    explanation: str = ""
    upstream_assessment_ids: Dict[str, str] = field(default_factory=dict)
    observation_timestamp: Optional[datetime] = None
    methodology_version: str = "F.4.4-PROVISIONAL"
    rule_version: str = "1.0.0"
