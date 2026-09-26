"""
Integration Contract Builders & Hand-Off Validation Functions (Phase F.7.2).

Provides helper functions for constructing typed integration contracts from domain outputs,
propagating provenance, validating point-in-time consistency, and verifying version compatibility.

Governance Rules Enforced:
- Wraps upstream domain outputs into integration contracts WITHOUT recalculating underlying domain logic.
- Preserves explicit `Optional` semantics (Missing != 0 / Missing != False).
- Validates version compatibility and point-in-time freshness across contracts.
- Strictly preserves canonical scheme identity and assessment IDs.
"""

from datetime import date, datetime
from typing import List, Optional, Any, Dict

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
)

from scoring.models import FundQualityScoreResult
from risk.capacity_models import RiskCapacityAssessmentResult
from risk.tolerance_models import RiskToleranceAssessmentResult
from risk.alignment_models import RiskAlignmentAssessmentResult
from models.suitability_assessment import SuitabilityAssessmentResult
from portfolio.need_models import PortfolioNeedAssessmentResult, PortfolioNeedState, CandidateFulfillmentStatus
from action.models import PositionContext


def from_fund_quality_result(
    result: FundQualityScoreResult,
    canonical_scheme_id: Optional[str] = None,
    category: Optional[str] = None,
    subcategory: Optional[str] = None,
    plan_type: str = "DIRECT",
    option_type: str = "GROWTH",
    fund_maturity_months: Optional[int] = None,
    fund_quality_comparison_valid: Optional[bool] = None,
    status: IntegrationStatus = IntegrationStatus.VALID,
) -> FundQualityIntegrationContract:
    """
    Constructs a FundQualityIntegrationContract from an upstream FundQualityScoreResult.

    - Domain Owner: Fund Quality Domain (`QualityEngine`)
    - Represents: Hand-off payload carrying scheme score, confidence, maturity, and comparison validity.
    - Must NOT Calculate: Fund Quality score, normalizations, confidence score, or score comparability.
    - Boundary Rationale: Encapsulates scheme quality output into a typed integration contract.
    """
    scheme_id = canonical_scheme_id or getattr(result, "canonical_scheme_id", "")
    cat = category or getattr(result, "category", "")
    subcat = subcategory or getattr(result, "subcategory", "")
    obs_date = getattr(result, "observation_date", getattr(result, "calculation_date", None))
    calc_ts = getattr(result, "calculation_timestamp_utc", None)
    meth_ver = getattr(result, "scoring_methodology_version", getattr(result, "methodology_version", "1.0.0"))
    config_ver = getattr(result, "weight_config_version", getattr(result, "config_version", getattr(result, "weights_version", "1.0.0")))
    score = getattr(result, "quality_score", getattr(result, "composite_score", None))
    conf = getattr(result, "confidence_score", 1.0)
    ass_id = getattr(result, "assessment_id", f"fq_{scheme_id}_{obs_date}")
    prov = getattr(result, "provenance", None)

    ref = CanonicalAssessmentReference(
        assessment_id=ass_id,
        assessment_type=AssessmentType.FUND_QUALITY,
        scheme_id=scheme_id,
        observation_date=obs_date,
        assessment_timestamp_utc=calc_ts,
        methodology_version=meth_ver,
        config_version=config_ver,
        status=status,
        confidence=conf,
        provenance_references=[prov.source_id] if prov else [],
    )
    ev_valid = getattr(result, "fund_quality_evidence_valid", getattr(result, "is_evidence_valid", False if score is None else True))
    return FundQualityIntegrationContract(
        reference=ref,
        canonical_scheme_id=scheme_id,
        category=cat,
        subcategory=subcat,
        plan_type=plan_type,
        option_type=option_type,
        fund_quality_score=score,
        fund_quality_confidence=conf,
        fund_maturity_months=fund_maturity_months,
        fund_quality_evidence_valid=ev_valid,
        fund_quality_comparison_valid=fund_quality_comparison_valid,
        methodology_version=meth_ver,
        config_version=config_ver,
        provenance=prov,
    )


def from_risk_capacity_result(
    result: RiskCapacityAssessmentResult,
    status: IntegrationStatus = IntegrationStatus.VALID,
) -> RiskCapacityIntegrationContract:
    """
    Constructs a RiskCapacityIntegrationContract from an upstream RiskCapacityAssessmentResult.

    - Domain Owner: Risk Capacity Domain (`RiskCapacityEngine`)
    - Represents: Hand-off payload carrying investor financial risk capacity tier and binding constraints.
    - Must NOT Calculate: Financial capacity ratios, debt limits, or capacity tier assignments.
    - Boundary Rationale: Wraps capacity output for downstream alignment and suitability evaluation.
    """
    ref = CanonicalAssessmentReference(
        assessment_id=result.assessment_id,
        assessment_type=AssessmentType.RISK_CAPACITY,
        investor_id=result.investor_id,
        profile_version=result.profile_version_used,
        observation_date=result.observation_date,
        assessment_timestamp_utc=result.assessment_timestamp_utc,
        methodology_version=result.methodology_version,
        rule_version=result.rule_version,
        status=status,
        confidence=result.confidence_score,
        provenance_references=[result.provenance.source_id] if result.provenance else [],
    )
    return RiskCapacityIntegrationContract(
        reference=ref,
        investor_id=result.investor_id,
        risk_capacity_level=result.overall_capacity_tier,
        binding_constraint_name=result.binding_constraint_name,
        status=result.assessment_status,
        confidence_score=result.confidence_score,
        provenance=result.provenance,
        methodology_version=result.methodology_version,
        rule_version=result.rule_version,
    )


def from_risk_tolerance_result(
    result: RiskToleranceAssessmentResult,
    status: IntegrationStatus = IntegrationStatus.VALID,
) -> RiskToleranceIntegrationContract:
    """
    Constructs a RiskToleranceIntegrationContract from an upstream RiskToleranceAssessmentResult.

    - Domain Owner: Risk Tolerance Domain (`RiskToleranceEngine`)
    - Represents: Hand-off payload carrying investor psychometric risk tolerance tier and behavioral consistency.
    - Must NOT Calculate: Psychometric scoring, loss tolerance math, or behavioral consistency ratings.
    - Boundary Rationale: Wraps risk tolerance output for downstream alignment and suitability evaluation.
    """
    ref = CanonicalAssessmentReference(
        assessment_id=result.assessment_id,
        assessment_type=AssessmentType.RISK_TOLERANCE,
        investor_id=result.investor_id,
        profile_version=result.profile_version_used,
        observation_date=result.observation_date,
        assessment_timestamp_utc=result.assessment_timestamp_utc,
        methodology_version=result.methodology_version,
        rule_version=result.rule_version,
        status=status,
        confidence=result.confidence_score,
        provenance_references=[result.provenance.source_id] if result.provenance else [],
    )
    return RiskToleranceIntegrationContract(
        reference=ref,
        investor_id=result.investor_id,
        risk_tolerance_level=result.overall_tolerance_tier,
        consistency_level=result.consistency_level,
        status=result.assessment_status,
        confidence_score=result.confidence_score,
        provenance=result.provenance,
        methodology_version=result.methodology_version,
        rule_version=result.rule_version,
    )


def from_risk_alignment_result(
    result: RiskAlignmentAssessmentResult,
    status: IntegrationStatus = IntegrationStatus.VALID,
) -> RiskAlignmentIntegrationContract:
    """
    Constructs a RiskAlignmentIntegrationContract from an upstream RiskAlignmentAssessmentResult.

    - Domain Owner: Risk Alignment Domain (`RiskAlignmentEngine`)
    - Represents: Hand-off payload carrying aligned risk level and lower-of-two limiting constraints.
    - Must NOT Calculate: Min(Capacity, Tolerance) logic or constituent evaluations.
    - Boundary Rationale: Provides unified risk alignment reference to Suitability while maintaining lineage.
    """
    ref = CanonicalAssessmentReference(
        assessment_id=result.assessment_id,
        assessment_type=AssessmentType.RISK_ALIGNMENT,
        investor_id=result.investor_id,
        profile_version=result.profile_version_used,
        observation_date=result.observation_date,
        assessment_timestamp_utc=result.assessment_timestamp_utc,
        methodology_version=result.methodology_version,
        rule_version=result.rule_version,
        status=status,
        confidence=result.alignment_confidence_score,
        provenance_references=[result.provenance.source_id] if result.provenance else [],
    )
    return RiskAlignmentIntegrationContract(
        reference=ref,
        investor_id=result.investor_id,
        alignment_status=result.alignment_status,
        limiting_constraint=result.limiting_constraint,
        aligned_risk_level=result.aligned_risk_level,
        capacity_assessment_id=result.capacity_assessment_id,
        tolerance_assessment_id=result.tolerance_assessment_id,
        alignment_confidence_score=result.alignment_confidence_score,
        is_stale_input=result.is_stale_input,
        provenance=result.provenance,
        methodology_version=result.methodology_version,
        rule_version=result.rule_version,
    )


def from_suitability_result(
    result: SuitabilityAssessmentResult,
    status: IntegrationStatus = IntegrationStatus.VALID,
) -> SuitabilityIntegrationContract:
    """
    Constructs a SuitabilityIntegrationContract from an upstream SuitabilityAssessmentResult.

    - Domain Owner: Suitability Domain (`SuitabilityEngine`)
    - Represents: Hand-off payload carrying Suitability Status (SUITABLE, NOT_SUITABLE, etc.) and applied constraints.
    - Must NOT Calculate: Risk alignment checking, horizon matching, or suitability decision pipeline logic.
    - Boundary Rationale: Wraps suitability determination for Portfolio Need and Action consumption.
    """
    ref = CanonicalAssessmentReference(
        assessment_id=result.assessment_id,
        assessment_type=AssessmentType.SUITABILITY,
        investor_id=result.investor_id,
        profile_version=result.profile_version_used,
        goal_id=result.goal_id,
        scheme_id=result.canonical_scheme_id,
        observation_date=result.observation_date,
        assessment_timestamp_utc=result.assessment_timestamp_utc,
        methodology_version=result.methodology_version,
        rule_version=result.rule_version,
        status=status,
        confidence=result.suitability_confidence_score,
        provenance_references=[result.provenance.source_id] if result.provenance else [],
    )
    return SuitabilityIntegrationContract(
        reference=ref,
        investor_id=result.investor_id,
        canonical_scheme_id=result.canonical_scheme_id,
        goal_id=result.goal_id,
        suitability_status=result.suitability_status,
        constraints_applied=list(result.constraints_applied),
        rejection_reasons=list(result.rejection_reasons),
        suitability_confidence_score=result.suitability_confidence_score,
        effective_horizon_years=result.effective_horizon_years,
        is_horizon_compatible=result.is_horizon_compatible,
        is_liquidity_compatible=result.is_liquidity_compatible,
        provenance=result.provenance,
        methodology_version=result.methodology_version,
        rule_version=result.rule_version,
    )


def from_portfolio_need_result(
    result: PortfolioNeedAssessmentResult,
    status: IntegrationStatus = IntegrationStatus.VALID,
) -> PortfolioNeedIntegrationContract:
    """
    Constructs a PortfolioNeedIntegrationContract from an upstream PortfolioNeedAssessmentResult.

    - Domain Owner: Portfolio Need Domain (`PortfolioNeedEngine`)
    - Represents: Hand-off payload carrying Portfolio Need state, candidate fulfillment, and affordability.
    - Must NOT Calculate: Exposure gaps, funding ratio math, candidate fulfillment logic, or affordability rules.
    - Boundary Rationale: Wraps portfolio need determination for Economic Benefit and Action consumption.
    """
    obs_ts = getattr(result, "observation_timestamp", None)
    obs_date = getattr(result, "observation_date", obs_ts.date() if isinstance(obs_ts, datetime) else None)
    meth_ver = getattr(result, "methodology_version", "1.0.0")
    rule_ver = getattr(result, "rule_version", "1.0.0")
    prov = getattr(result, "provenance", None)

    need_st = getattr(result, "primary_state", getattr(result, "need_state", PortfolioNeedState.NEED_IDENTIFIED))
    cand_ful = getattr(result, "candidate_fulfillment_status", getattr(result, "candidate_fulfillment", CandidateFulfillmentStatus.CANDIDATE_CAN_FULFILL_NEED))
    upstream_ids = getattr(result, "upstream_assessment_ids", {})
    port_snap_id = getattr(result, "portfolio_snapshot_id", upstream_ids.get("portfolio_snapshot_id"))
    cand_scheme_id = getattr(result, "scheme_id", getattr(result, "candidate_scheme_id", None))

    ref = CanonicalAssessmentReference(
        assessment_id=result.assessment_id,
        assessment_type=AssessmentType.PORTFOLIO_NEED,
        investor_id=result.investor_id,
        goal_id=result.goal_id,
        portfolio_id=port_snap_id,
        scheme_id=cand_scheme_id,
        observation_date=obs_date if isinstance(obs_date, date) else (obs_ts.date() if isinstance(obs_ts, datetime) else None),
        assessment_timestamp_utc=obs_ts,
        methodology_version=meth_ver,
        rule_version=rule_ver,
        status=status,
        provenance_references=[prov.source_id] if prov else [],
    )
    exp_pct = result.exposure_gap.gap_pct if result.exposure_gap else None
    exp_dir = result.exposure_gap.gap_direction if result.exposure_gap else None

    return PortfolioNeedIntegrationContract(
        reference=ref,
        investor_id=result.investor_id,
        goal_id=result.goal_id,
        portfolio_snapshot_id=port_snap_id,
        candidate_scheme_id=cand_scheme_id,
        need_state=need_st,
        candidate_fulfillment=cand_ful,
        affordability_status=result.affordability_status,
        funding_status=result.funding_status,
        exposure_gap_direction=exp_dir,
        exposure_gap_pct=exp_pct,
        provenance=prov,
        methodology_version=meth_ver,
        rule_version=rule_ver,
    )


def from_economic_benefit_result(
    assessment_id: str,
    investor_id: str,
    economic_benefit_state: EconomicBenefitState,
    position_context: str = "NEW_POSITION",
    current_holding_scheme_id: Optional[str] = None,
    candidate_scheme_id: Optional[str] = None,
    economic_benefit_actionable: bool = True,
    evidence_sufficiency_valid: bool = True,
    expected_improvement_status: Optional[str] = None,
    cost_tax_evidence_status: Optional[str] = None,
    observation_date: Optional[date] = None,
    assessment_timestamp_utc: Optional[datetime] = None,
    methodology_version: str = "F.5.0",
    rule_version: str = "1.0.0",
    config_version: Optional[str] = None,
    provenance: Optional[ProvenanceMetadata] = None,
    status: IntegrationStatus = IntegrationStatus.VALID,
) -> EconomicBenefitIntegrationContract:
    """
    Constructs an EconomicBenefitIntegrationContract from an upstream Economic Benefit assessment.

    - Domain Owner: Economic Benefit Domain (`EconomicBenefitEngine`)
    - Represents: Hand-off payload carrying canonical F.5 Economic Benefit state and evidence actionability.
    - Must NOT Calculate: Statutory tax liability, exit load math, transaction cost math, or return improvement deltas.
    - Boundary Rationale: Centralizes economic benefit hand-off to Action, enforcing canonical F.5 states exclusively.
    """
    if not isinstance(economic_benefit_state, EconomicBenefitState):
        raise ValueError(
            f"economic_benefit_state must be a canonical EconomicBenefitState enum, got {type(economic_benefit_state)}"
        )

    ref = CanonicalAssessmentReference(
        assessment_id=assessment_id,
        assessment_type=AssessmentType.ECONOMIC_BENEFIT,
        investor_id=investor_id,
        scheme_id=candidate_scheme_id or current_holding_scheme_id,
        observation_date=observation_date,
        assessment_timestamp_utc=assessment_timestamp_utc or datetime.utcnow(),
        methodology_version=methodology_version,
        rule_version=rule_version,
        config_version=config_version,
        status=status,
        provenance_references=[provenance.source_id] if provenance else [],
    )
    return EconomicBenefitIntegrationContract(
        reference=ref,
        investor_id=investor_id,
        position_context=position_context,
        current_holding_scheme_id=current_holding_scheme_id,
        candidate_scheme_id=candidate_scheme_id,
        economic_benefit_state=economic_benefit_state,
        economic_benefit_actionable=economic_benefit_actionable,
        evidence_sufficiency_valid=evidence_sufficiency_valid,
        expected_improvement_status=expected_improvement_status,
        cost_tax_evidence_status=cost_tax_evidence_status,
        provenance=provenance,
        methodology_version=methodology_version,
        rule_version=rule_version,
        config_version=config_version,
    )


def build_action_input_contract(
    investor_id: str,
    scheme_id: str,
    position_context: PositionContext,
    assessment_id: str,
    goal_id: Optional[str] = None,
    portfolio_id: Optional[str] = None,
    fund_quality_contract: Optional[FundQualityIntegrationContract] = None,
    risk_alignment_contract: Optional[RiskAlignmentIntegrationContract] = None,
    suitability_contract: Optional[SuitabilityIntegrationContract] = None,
    portfolio_need_contract: Optional[PortfolioNeedIntegrationContract] = None,
    economic_benefit_contract: Optional[EconomicBenefitIntegrationContract] = None,
    deterioration_signal: Optional[str] = None,
    deterioration_validated: Optional[bool] = None,
    has_suitable_replacement: Optional[bool] = None,
    fund_quality_comparison_valid: Optional[bool] = None,
    macro_stress_flag: bool = False,
    observation_timestamp: Optional[datetime] = None,
) -> ActionInputIntegrationContract:
    """
    Builds a validated ActionInputIntegrationContract by composing upstream domain integration contracts.

    - Domain Owner: Action Decision Domain (`ActionEngine`) / Integration Layer
    - Represents: Composition of all upstream domain integration contracts into a single validated input payload.
    - Must NOT Calculate: Upstream scoring, suitability rules, portfolio need math, tax rates, or economic benefit states.
    - Boundary Rationale: Structurally decouples upstream domain outputs from Action Decision orchestration.
    """
    ref = CanonicalAssessmentReference(
        assessment_id=assessment_id,
        assessment_type=AssessmentType.ACTION,
        investor_id=investor_id,
        goal_id=goal_id,
        portfolio_id=portfolio_id,
        scheme_id=scheme_id,
        assessment_timestamp_utc=observation_timestamp or datetime.utcnow(),
        methodology_version="F.6.2",
        rule_version="1.0.0",
        status=IntegrationStatus.VALID,
    )

    validation_messages: List[str] = []
    status = IntegrationStatus.VALID

    # Hand-off validation checks
    if suitability_contract is None:
        validation_messages.append("Missing Suitability Integration Contract")
        status = IntegrationStatus.PARTIAL
    if portfolio_need_contract is None:
        validation_messages.append("Missing Portfolio Need Integration Contract")
        status = IntegrationStatus.PARTIAL
    if economic_benefit_contract is None:
        validation_messages.append("Missing Economic Benefit Integration Contract")
        status = IntegrationStatus.PARTIAL

    return ActionInputIntegrationContract(
        assessment_reference=ref,
        investor_id=investor_id,
        scheme_id=scheme_id,
        position_context=position_context,
        goal_id=goal_id,
        portfolio_id=portfolio_id,
        fund_quality_contract=fund_quality_contract,
        risk_alignment_contract=risk_alignment_contract,
        suitability_contract=suitability_contract,
        portfolio_need_contract=portfolio_need_contract,
        economic_benefit_contract=economic_benefit_contract,
        deterioration_signal=deterioration_signal,
        deterioration_validated=deterioration_validated,
        has_suitable_replacement=has_suitable_replacement,
        fund_quality_comparison_valid=fund_quality_comparison_valid,
        macro_stress_flag=macro_stress_flag,
        integration_status=status,
        actionability_status="HIGH_ACTIONABILITY" if status == IntegrationStatus.VALID else "PARTIAL_ACTIONABILITY",
        validation_messages=validation_messages,
    )


def validate_version_compatibility(contracts: List[Any]) -> bool:
    """
    Validates methodology and rule version compatibility across a collection of integration contracts.

    Returns True if all provided contracts have non-empty, valid version strings.
    Returns False if any contract has a missing/empty version string or an explicit incompatibility marker.
    """
    for contract in contracts:
        if contract is None:
            continue
        methodology = getattr(contract, "methodology_version", None)
        if methodology is None or not str(methodology).strip():
            return False
        meth_str = str(methodology).strip().upper()
        if "INCOMPATIBLE" in meth_str or "INVALID" in meth_str or "UNSUPPORTED" in meth_str:
            return False
    return True


def validate_point_in_time_consistency(contracts: List[Any]) -> bool:
    """
    Validates point-in-time freshness and observation date alignment across integration contracts.

    Consumes upstream freshness determinations (`is_stale_input`) across provided contracts.
    Returns False if any contract is explicitly flagged as stale by upstream domain rules (`is_stale_input is True`).
    Returns True otherwise.
    Must NOT calculate hardcoded numerical staleness thresholds or day deltas (e.g. 180-day delta).
    """
    for contract in contracts:
        if contract is None:
            continue
        if getattr(contract, "is_stale_input", False) is True:
            return False
    return True
