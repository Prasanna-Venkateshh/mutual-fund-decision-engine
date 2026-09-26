"""
End-to-End Decision Orchestrator Implementation (Phase F.7.3).

Implements the central decision orchestrator that composes already-established and independently QA-accepted
domain assessments into one governed Fund Decision + Portfolio Decision outcome.

Canonical Architecture Pipeline:
DATA -> METRIC ENGINE -> FUND QUALITY -> RISK CAPACITY -> RISK TOLERANCE -> RISK ALIGNMENT -> SUITABILITY -> PORTFOLIO NEED -> ECONOMIC BENEFIT -> ACTION

Governance Invariants Enforced:
1. Low-turnover principle: DEFAULT ACTION = HOLD / DO NOTHING UNLESS EVIDENCE JUSTIFIES CHANGE.
2. 7-Tier Precedence Hierarchy:
   TIER 1 — DATA INTEGRITY
   TIER 2 — INFORMATION SUFFICIENCY & FRESHNESS
   TIER 3 — SUITABILITY / HARD RISK CONSTRAINTS
   TIER 4 — PORTFOLIO NEED & CANDIDATE FULFILLMENT
   TIER 5 — ECONOMIC BENEFIT & SWITCHING ECONOMICS
   TIER 6 — ACTIONABILITY & AFFORDABILITY / ACCUMULATE
   TIER 7 — OPERATIONAL ACTION / DEFAULT BASELINE
3. Zero Upstream Methodology Duplication: The orchestrator ONLY composes governed upstream outputs.
   It does NOT calculate scores, risk ratios, suitability rules, gap math, tax rates, or return forecasts.
4. Preserves explicit unknown/missing/false semantics (None != False, None != 0, Missing != Favorable Evidence).
5. Canonical state preservation (F.5 Economic Benefit states, F.3.4 Suitability states, F.4.4 Portfolio Need states).
6. Complete provenance and version metadata aggregation across all constituent domain contracts.
7. Read-only analytical recommendation layer; zero execution of broker transactions.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from models.fund_quality_dataset import ProvenanceMetadata
from models.suitability_assessment import SuitabilityAssessmentResult, SuitabilityStatus
from portfolio.need_models import (
    PortfolioNeedAssessmentResult,
    PortfolioNeedState,
    CandidateFulfillmentStatus,
    AffordabilityStatus,
    FundingStatus,
)
from action.models import (
    ActionState,
    PositionContext,
    ActionEvaluationContext,
    ActionAssessmentResult,
    ReasonCode,
)
from action.engine import assess_action

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
    validate_version_compatibility,
    validate_point_in_time_consistency,
    build_action_input_contract,
)


class DecisionOrchestrator:
    """
    End-to-End Decision Orchestrator (Phase F.7.3).

    Composes governed upstream integration contracts into a final EndToEndDecisionResult.
    """

    ORCHESTRATOR_VERSION = "F.7.3"

    def evaluate_decision(
        self,
        input_contract: ActionInputIntegrationContract,
    ) -> EndToEndDecisionResult:
        """
        Executes the end-to-end decision orchestration pipeline over an ActionInputIntegrationContract payload.
        """
        now_utc = datetime.now(timezone.utc)
        assessment_id = f"e2e_{uuid.uuid4().hex[:12]}"
        
        blocking_reasons: List[str] = []
        warnings: List[str] = list(input_contract.validation_messages)
        
        # Extract contract references
        fq = input_contract.fund_quality_contract
        rc = input_contract.risk_alignment_contract.capacity_assessment_id if input_contract.risk_alignment_contract else None
        rt = input_contract.risk_alignment_contract.tolerance_assessment_id if input_contract.risk_alignment_contract else None
        ra = input_contract.risk_alignment_contract
        suit = input_contract.suitability_contract
        pneed = input_contract.portfolio_need_contract
        eb = input_contract.economic_benefit_contract

        # Aggregate upstream assessment IDs
        upstream_ids: Dict[str, str] = {}
        if fq and fq.reference:
            upstream_ids["fund_quality_assessment_id"] = fq.reference.assessment_id
        if ra and ra.capacity_assessment_id:
            upstream_ids["risk_capacity_assessment_id"] = ra.capacity_assessment_id
        if ra and ra.tolerance_assessment_id:
            upstream_ids["risk_tolerance_assessment_id"] = ra.tolerance_assessment_id
        if ra and ra.reference:
            upstream_ids["risk_alignment_assessment_id"] = ra.reference.assessment_id
        if suit and suit.reference:
            upstream_ids["suitability_assessment_id"] = suit.reference.assessment_id
        if pneed and pneed.reference:
            upstream_ids["portfolio_need_assessment_id"] = pneed.reference.assessment_id
        if eb and eb.reference:
            upstream_ids["economic_benefit_assessment_id"] = eb.reference.assessment_id

        # Aggregate methodology, rule, and config versions
        meth_versions: Dict[str, str] = {"orchestrator": self.ORCHESTRATOR_VERSION}
        rule_versions: Dict[str, str] = {"orchestrator": "1.0.0"}
        config_versions: Dict[str, str] = {}

        if fq:
            meth_versions["fund_quality"] = fq.methodology_version
            if fq.config_version:
                config_versions["fund_quality"] = fq.config_version
        if ra:
            meth_versions["risk_alignment"] = ra.methodology_version
            rule_versions["risk_alignment"] = ra.rule_version
        if suit:
            meth_versions["suitability"] = suit.methodology_version
            rule_versions["suitability"] = suit.rule_version
        if pneed:
            meth_versions["portfolio_need"] = pneed.methodology_version
            rule_versions["portfolio_need"] = pneed.rule_version
        if eb:
            meth_versions["economic_benefit"] = eb.methodology_version
            rule_versions["economic_benefit"] = eb.rule_version

        # ---------------------------------------------------------------------
        # TIER 1: DATA INTEGRITY & STRUCTURAL SOUNDNESS CHECK
        # ---------------------------------------------------------------------
        if not input_contract.investor_id or not input_contract.scheme_id or not input_contract.position_context:
            blocking_reasons.append("Structural non-nullness violation in ActionInputIntegrationContract.")
            return EndToEndDecisionResult(
                assessment_id=assessment_id,
                investor_id=input_contract.investor_id or "UNKNOWN",
                scheme_id=input_contract.scheme_id or "UNKNOWN",
                position_context=input_contract.position_context if input_contract else PositionContext.NEW_POSITION,
                final_action_state=ActionState.INVALID_ASSESSMENT,
                final_decision_status=IntegrationStatus.INVALID,
                goal_id=input_contract.goal_id,
                portfolio_id=input_contract.portfolio_id,
                upstream_assessment_ids=upstream_ids,
                final_explanation="Invalid context: investor_id, scheme_id, or position_context is empty/missing.",
                blocking_reasons=blocking_reasons,
                warnings=warnings,
                decision_timestamp_utc=now_utc,
                methodology_versions=meth_versions,
                rule_versions=rule_versions,
                config_versions=config_versions,
                orchestrator_version=self.ORCHESTRATOR_VERSION,
            )

        # Check for invalid assessment states in upstream contracts
        if ra and (ra.alignment_confidence_score < 0.0 or (ra.reference and ra.reference.status == IntegrationStatus.INVALID)):
            blocking_reasons.append("Upstream Risk Alignment reported invalid assessment or negative confidence score.")
            return EndToEndDecisionResult(
                assessment_id=assessment_id,
                investor_id=input_contract.investor_id,
                scheme_id=input_contract.scheme_id,
                final_action_state=ActionState.INVALID_ASSESSMENT,
                final_decision_status=IntegrationStatus.INVALID,
                goal_id=input_contract.goal_id,
                portfolio_id=input_contract.portfolio_id,
                upstream_assessment_ids=upstream_ids,
                final_explanation="Upstream Risk Alignment assessment is invalid.",
                blocking_reasons=blocking_reasons,
                warnings=warnings,
                decision_timestamp_utc=now_utc,
                methodology_versions=meth_versions,
                rule_versions=rule_versions,
                config_versions=config_versions,
                orchestrator_version=self.ORCHESTRATOR_VERSION,
            )

        if suit and (suit.suitability_confidence_score < 0.0 or suit.suitability_status == SuitabilityStatus.INVALID_ASSESSMENT or (suit.reference and suit.reference.status == IntegrationStatus.INVALID)):
            blocking_reasons.append("Upstream Suitability reported invalid assessment or negative confidence score.")
            return EndToEndDecisionResult(
                assessment_id=assessment_id,
                investor_id=input_contract.investor_id,
                scheme_id=input_contract.scheme_id,
                final_action_state=ActionState.INVALID_ASSESSMENT,
                final_decision_status=IntegrationStatus.INVALID,
                goal_id=input_contract.goal_id,
                portfolio_id=input_contract.portfolio_id,
                upstream_assessment_ids=upstream_ids,
                final_explanation="Upstream Suitability assessment is invalid.",
                blocking_reasons=blocking_reasons,
                warnings=warnings,
                decision_timestamp_utc=now_utc,
                methodology_versions=meth_versions,
                rule_versions=rule_versions,
                config_versions=config_versions,
                orchestrator_version=self.ORCHESTRATOR_VERSION,
            )

        if fq and (fq.fund_quality_confidence is not None and fq.fund_quality_confidence < 0.0 or (fq.reference and fq.reference.status == IntegrationStatus.INVALID)):
            blocking_reasons.append("Upstream Fund Quality reported invalid assessment or negative confidence score.")
            return EndToEndDecisionResult(
                assessment_id=assessment_id,
                investor_id=input_contract.investor_id,
                scheme_id=input_contract.scheme_id,
                final_action_state=ActionState.INVALID_ASSESSMENT,
                final_decision_status=IntegrationStatus.INVALID,
                goal_id=input_contract.goal_id,
                portfolio_id=input_contract.portfolio_id,
                upstream_assessment_ids=upstream_ids,
                final_explanation="Upstream Fund Quality assessment is invalid.",
                blocking_reasons=blocking_reasons,
                warnings=warnings,
                decision_timestamp_utc=now_utc,
                methodology_versions=meth_versions,
                rule_versions=rule_versions,
                config_versions=config_versions,
                orchestrator_version=self.ORCHESTRATOR_VERSION,
            )

        if pneed and pneed.need_state == PortfolioNeedState.INVALID_ASSESSMENT:
            blocking_reasons.append("Upstream Portfolio Need reported INVALID_ASSESSMENT.")
            return EndToEndDecisionResult(
                assessment_id=assessment_id,
                investor_id=input_contract.investor_id,
                scheme_id=input_contract.scheme_id,
                final_action_state=ActionState.INVALID_ASSESSMENT,
                final_decision_status=IntegrationStatus.INVALID,
                goal_id=input_contract.goal_id,
                portfolio_id=input_contract.portfolio_id,
                upstream_assessment_ids=upstream_ids,
                final_explanation="Upstream Portfolio Need assessment is invalid.",
                blocking_reasons=blocking_reasons,
                warnings=warnings,
                decision_timestamp_utc=now_utc,
                methodology_versions=meth_versions,
                rule_versions=rule_versions,
                config_versions=config_versions,
                orchestrator_version=self.ORCHESTRATOR_VERSION,
            )

        if eb and eb.economic_benefit_state == EconomicBenefitState.INVALID_ASSESSMENT:
            blocking_reasons.append("Upstream Economic Benefit reported INVALID_ASSESSMENT.")
            return EndToEndDecisionResult(
                assessment_id=assessment_id,
                investor_id=input_contract.investor_id,
                scheme_id=input_contract.scheme_id,
                final_action_state=ActionState.INVALID_ASSESSMENT,
                final_decision_status=IntegrationStatus.INVALID,
                goal_id=input_contract.goal_id,
                portfolio_id=input_contract.portfolio_id,
                upstream_assessment_ids=upstream_ids,
                final_explanation="Upstream Economic Benefit assessment is invalid.",
                blocking_reasons=blocking_reasons,
                warnings=warnings,
                decision_timestamp_utc=now_utc,
                methodology_versions=meth_versions,
                rule_versions=rule_versions,
                config_versions=config_versions,
                orchestrator_version=self.ORCHESTRATOR_VERSION,
            )

        # Propagate warnings for conditional suitability / constraints
        if suit and suit.suitability_status in [SuitabilityStatus.CONDITIONALLY_SUITABLE, SuitabilityStatus.SUITABLE_WITH_CONSTRAINTS]:
            warnings.append(f"Suitability status: {suit.suitability_status.value}")
            if suit.constraints_applied:
                for c in suit.constraints_applied:
                    if c not in warnings:
                        warnings.append(f"Suitability constraint: {c}")

        # ---------------------------------------------------------------------
        # TIER 2: VERSION COMPATIBILITY & POINT-IN-TIME FRESHNESS CHECK
        # ---------------------------------------------------------------------
        contracts_to_check = [fq, ra, suit, pneed, eb]
        if not validate_version_compatibility(contracts_to_check):
            blocking_reasons.append("Methodology or rule version incompatibility detected across domain contracts.")
            return EndToEndDecisionResult(
                assessment_id=assessment_id,
                investor_id=input_contract.investor_id,
                scheme_id=input_contract.scheme_id,
                final_action_state=ActionState.INVALID_ASSESSMENT,
                final_decision_status=IntegrationStatus.INVALID,
                goal_id=input_contract.goal_id,
                portfolio_id=input_contract.portfolio_id,
                upstream_assessment_ids=upstream_ids,
                final_explanation="Version compatibility validation failed across domain contracts.",
                blocking_reasons=blocking_reasons,
                warnings=warnings,
                decision_timestamp_utc=now_utc,
                methodology_versions=meth_versions,
                rule_versions=rule_versions,
                config_versions=config_versions,
                orchestrator_version=self.ORCHESTRATOR_VERSION,
            )

        if not validate_point_in_time_consistency(contracts_to_check):
            blocking_reasons.append("Upstream assessment input data is flagged as stale by governed freshness criteria.")
            if input_contract.position_context == PositionContext.EXISTING_POSITION:
                final_act = ActionState.REVIEW
            else:
                final_act = ActionState.INSUFFICIENT_INFORMATION
            return EndToEndDecisionResult(
                assessment_id=assessment_id,
                investor_id=input_contract.investor_id,
                scheme_id=input_contract.scheme_id,
                final_action_state=final_act,
                final_decision_status=IntegrationStatus.PARTIAL,
                goal_id=input_contract.goal_id,
                portfolio_id=input_contract.portfolio_id,
                upstream_assessment_ids=upstream_ids,
                final_explanation="Upstream assessment input data is flagged as stale by governed freshness criteria.",
                blocking_reasons=blocking_reasons,
                warnings=warnings,
                decision_timestamp_utc=now_utc,
                methodology_versions=meth_versions,
                rule_versions=rule_versions,
                config_versions=config_versions,
                orchestrator_version=self.ORCHESTRATOR_VERSION,
            )

        # Construct ActionEvaluationContext for delegation to ActionEngine
        suit_res_obj = self._build_suitability_assessment_result(suit)
        pneed_res_obj = self._build_portfolio_need_assessment_result(pneed)

        action_context = ActionEvaluationContext(
            investor_id=input_contract.investor_id,
            scheme_id=input_contract.scheme_id,
            position_context=input_contract.position_context,
            goal_id=input_contract.goal_id,
            portfolio_id=input_contract.portfolio_id,
            fund_quality_assessment_id=fq.reference.assessment_id if fq and fq.reference else None,
            fund_quality_score=fq.fund_quality_score if fq else None,
            fund_quality_confidence=fq.fund_quality_confidence if fq else None,
            fund_quality_evidence_valid=fq.fund_quality_evidence_valid if fq else None,
            suitability_result=suit_res_obj,
            portfolio_need_result=pneed_res_obj,
            economic_benefit_state=eb.economic_benefit_state.value if eb else "BENEFIT_UNCERTAIN",
            tax_liability_known=(eb.cost_tax_evidence_status != "MISSING_TAX_RATES" and eb.evidence_sufficiency_valid is True) if eb else False,
            exit_load_known=(eb.cost_tax_evidence_status != "MISSING_EXIT_LOAD" and eb.evidence_sufficiency_valid is True) if eb else False,
            transaction_costs_known=(eb.cost_tax_evidence_status != "MISSING_TRANSACTION_COSTS" and eb.evidence_sufficiency_valid is True) if eb else False,
            is_stale_input=any(getattr(c, "is_stale_input", False) for c in contracts_to_check if c is not None),
            deterioration_signal=input_contract.deterioration_signal,
            deterioration_validated=input_contract.deterioration_validated,
            has_suitable_replacement=input_contract.has_suitable_replacement,
            fund_quality_comparison_valid=input_contract.fund_quality_comparison_valid,
            macro_stress_flag=input_contract.macro_stress_flag,
            observation_timestamp=input_contract.assessment_reference.assessment_timestamp_utc,
        )

        # Delegate evaluation to governed Action Engine
        action_res: ActionAssessmentResult = assess_action(action_context)

        # Merge warnings and reason codes
        warnings.extend(action_res.warnings)
        if action_res.primary_reason_code in [
            ReasonCode.CANDIDATE_NOT_SUITABLE.value,
            ReasonCode.CANDIDATE_CANNOT_FULFILL_NEED.value,
            ReasonCode.UNVALIDATED_DETERIORATION.value,
            ReasonCode.NO_SUITABLE_REPLACEMENT.value,
            ReasonCode.TAX_COST_INFORMATION_MISSING.value,
            ReasonCode.EXIT_LOAD_INFORMATION_MISSING.value,
            ReasonCode.INSUFFICIENT_EVIDENCE.value,
        ]:
            blocking_reasons.append(action_res.explanation)

        # Determine final decision status
        if action_res.action_state == ActionState.INVALID_ASSESSMENT:
            dec_status = IntegrationStatus.INVALID
        elif action_res.action_state in [ActionState.INSUFFICIENT_INFORMATION, ActionState.REVIEW]:
            dec_status = IntegrationStatus.PARTIAL
        else:
            dec_status = IntegrationStatus.VALID

        # Build aggregated provenance
        combined_prov = self._aggregate_provenance(contracts_to_check, now_utc)

        return EndToEndDecisionResult(
            assessment_id=assessment_id,
            investor_id=input_contract.investor_id,
            scheme_id=input_contract.scheme_id,
            final_action_state=action_res.action_state,
            final_decision_status=dec_status,
            goal_id=input_contract.goal_id,
            portfolio_id=input_contract.portfolio_id,
            upstream_assessment_ids=upstream_ids,
            final_explanation=action_res.explanation,
            blocking_reasons=blocking_reasons,
            warnings=warnings,
            provenance=combined_prov,
            observation_timestamp=input_contract.assessment_reference.assessment_timestamp_utc,
            decision_timestamp_utc=now_utc,
            methodology_versions=meth_versions,
            rule_versions=rule_versions,
            config_versions=config_versions,
            orchestrator_version=self.ORCHESTRATOR_VERSION,
        )

    def _build_suitability_assessment_result(
        self,
        suit: Optional[SuitabilityIntegrationContract],
    ) -> Optional[SuitabilityAssessmentResult]:
        """Reconstructs SuitabilityAssessmentResult compatibility object from SuitabilityIntegrationContract."""
        if suit is None:
            return None

        status_val = suit.suitability_status
        if isinstance(status_val, str):
            try:
                status_val = SuitabilityStatus[status_val]
            except KeyError:
                status_val = SuitabilityStatus.SUITABLE

        return SuitabilityAssessmentResult(
            assessment_id=suit.reference.assessment_id,
            investor_id=suit.investor_id,
            profile_version_used=suit.reference.profile_version or "1.0.0",
            canonical_scheme_id=suit.canonical_scheme_id,
            amfi_code="UNKNOWN",
            scheme_name="UNKNOWN",
            category="UNKNOWN",
            subcategory="UNKNOWN",
            observation_date=suit.reference.observation_date or datetime.now(timezone.utc).date(),
            suitability_status=status_val,
            goal_id=suit.goal_id,
            effective_horizon_years=suit.effective_horizon_years,
            is_horizon_compatible=suit.is_horizon_compatible,
            is_liquidity_compatible=suit.is_liquidity_compatible,
            suitability_confidence_score=suit.suitability_confidence_score,
            constraints_applied=list(suit.constraints_applied),
            rejection_reasons=list(suit.rejection_reasons),
            provenance=suit.provenance,
            assessment_timestamp_utc=suit.reference.assessment_timestamp_utc,
            methodology_version=suit.methodology_version,
            rule_version=suit.rule_version,
        )

    def _build_portfolio_need_assessment_result(
        self,
        pneed: Optional[PortfolioNeedIntegrationContract],
    ) -> Optional[PortfolioNeedAssessmentResult]:
        """Reconstructs PortfolioNeedAssessmentResult compatibility object from PortfolioNeedIntegrationContract."""
        if pneed is None:
            return None

        return PortfolioNeedAssessmentResult(
            assessment_id=pneed.reference.assessment_id,
            investor_id=pneed.investor_id,
            goal_id=pneed.goal_id,
            scheme_id=pneed.candidate_scheme_id,
            primary_state=pneed.need_state,
            candidate_fulfillment_status=pneed.candidate_fulfillment,
            affordability_status=pneed.affordability_status,
            funding_status=pneed.funding_status,
            exposure_gap=None,
            confidence_score=pneed.reference.confidence or 1.0,
            observation_timestamp=pneed.reference.assessment_timestamp_utc,
            methodology_version=pneed.methodology_version,
            rule_version=pneed.rule_version,
        )

    def _aggregate_provenance(
        self,
        contracts: List[Any],
        now_utc: datetime,
    ) -> ProvenanceMetadata:
        """Aggregates provenance metadata across constituent integration contracts."""
        source_ids = []
        for contract in contracts:
            if contract and getattr(contract, "provenance", None):
                prov = contract.provenance
                if prov.source_id and prov.source_id not in source_ids:
                    source_ids.append(prov.source_id)

        agg_source_id = ";".join(source_ids) if source_ids else "orchestrator.py"
        return ProvenanceMetadata(
            source_id=agg_source_id,
            source_document_url="file:///d:/AI%20Portfolio/mutual-fund-decision-engine/integration/orchestrator.py",
            retrieval_timestamp_utc=now_utc,
            methodology_version=self.ORCHESTRATOR_VERSION,
        )
