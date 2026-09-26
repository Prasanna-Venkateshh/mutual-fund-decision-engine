"""
Portfolio Need Models & Data Contracts Re-export (Phase F.4.4)

Re-exports data contracts from portfolio.need_models for backwards compatibility.
"""

from portfolio.need_models import (
    PortfolioNeedState,
    CandidateFulfillmentStatus,
    AffordabilityStatus,
    FundingStatus,
    ExposureGapDirection,
    GoalFundingSnapshot,
    PortfolioExposureSnapshot,
    ExposureGap,
    AllocationContext,
    FundingGap,
    AffordabilityContext,
    PortfolioLookThroughContext,
    FundCandidateContext,
    MultiGoalContext,
    GeneralWealthContext,
    PortfolioNeedAssessmentResult,
)

__all__ = [
    "PortfolioNeedState",
    "CandidateFulfillmentStatus",
    "AffordabilityStatus",
    "FundingStatus",
    "ExposureGapDirection",
    "GoalFundingSnapshot",
    "PortfolioExposureSnapshot",
    "ExposureGap",
    "AllocationContext",
    "FundingGap",
    "AffordabilityContext",
    "PortfolioLookThroughContext",
    "FundCandidateContext",
    "MultiGoalContext",
    "GeneralWealthContext",
    "PortfolioNeedAssessmentResult",
]
