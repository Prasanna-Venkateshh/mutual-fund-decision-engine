"""
Integration Contracts Package (Phase F.7.2).

Provides typed, explicit, immutable, provenance-preserving hand-off contracts
connecting all governed decision domains:
DATA -> METRIC ENGINE -> FUND QUALITY -> RISK CAPACITY -> RISK TOLERANCE -> RISK ALIGNMENT -> SUITABILITY -> PORTFOLIO NEED -> ECONOMIC BENEFIT -> ACTION

Governance Invariants:
- Integration contracts carry governed upstream outputs; they MUST NOT manufacture, calculate, or recreate financial methodology.
- Dataclasses are immutable (frozen=True).
- Canonical scheme IDs and upstream assessment IDs are strictly preserved.
"""

from integration.models import (
    AssessmentType,
    IntegrationStatus,
    EconomicBenefitState,
    CanonicalAssessmentReference,
    FundQualityIntegrationContract,
    RiskCapacityIntegrationContract,
    RiskToleranceIntegrationContract,
    RiskAlignmentIntegrationContract,
    SuitabilityIntegrationContract,
    PortfolioNeedIntegrationContract,
    EconomicBenefitIntegrationContract,
    ActionInputIntegrationContract,
    EndToEndDecisionResult,
)

from integration.contracts import (
    from_fund_quality_result,
    from_risk_capacity_result,
    from_risk_tolerance_result,
    from_risk_alignment_result,
    from_suitability_result,
    from_portfolio_need_result,
    from_economic_benefit_result,
    build_action_input_contract,
    validate_version_compatibility,
    validate_point_in_time_consistency,
)

from integration.orchestrator import DecisionOrchestrator

__all__ = [
    "AssessmentType",
    "IntegrationStatus",
    "EconomicBenefitState",
    "CanonicalAssessmentReference",
    "FundQualityIntegrationContract",
    "RiskCapacityIntegrationContract",
    "RiskToleranceIntegrationContract",
    "RiskAlignmentIntegrationContract",
    "SuitabilityIntegrationContract",
    "PortfolioNeedIntegrationContract",
    "EconomicBenefitIntegrationContract",
    "ActionInputIntegrationContract",
    "EndToEndDecisionResult",
    "DecisionOrchestrator",
    "from_fund_quality_result",
    "from_risk_capacity_result",
    "from_risk_tolerance_result",
    "from_risk_alignment_result",
    "from_suitability_result",
    "from_portfolio_need_result",
    "from_economic_benefit_result",
    "build_action_input_contract",
    "validate_version_compatibility",
    "validate_point_in_time_consistency",
]
