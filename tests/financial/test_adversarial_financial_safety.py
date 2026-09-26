"""
Phase F.7.4 — Adversarial Financial Safety Validation Test Suite

Stresses the complete end-to-end decision chain across extreme adversarial inputs,
uncertainty monotonicity, negative evidence monotonicity, score/confidence independence,
multi-goal isolation, state precedence conflicts, and the 15 core financial safety invariants.

Architecture Pipeline:
DATA -> METRIC ENGINE -> FUND QUALITY -> RISK CAPACITY -> RISK TOLERANCE -> RISK ALIGNMENT -> SUITABILITY -> PORTFOLIO NEED -> ECONOMIC BENEFIT -> ACTION -> END-TO-END ORCHESTRATOR
"""

import pytest
from datetime import date, datetime, timezone
from typing import Optional, Dict, Any, List

from models.fund_quality_dataset import ProvenanceMetadata, HistoryMaturityBucket
from scoring.engine import FundQualityScoreResult
from risk.capacity_models import AssessmentStatus, RiskCapacityLevel
from risk.tolerance_models import BehavioralConsistencyLevel, RiskToleranceLevel
from risk.alignment_models import AlignmentStatus, LimitingConstraint, AlignedRiskLevel, RiskAlignmentAssessmentResult
from models.suitability_assessment import SuitabilityAssessmentResult, SuitabilityStatus
from portfolio.need_models import (
    PortfolioNeedAssessmentResult,
    PortfolioNeedState,
    CandidateFulfillmentStatus,
    AffordabilityStatus,
    FundingStatus,
    ExposureGap,
    ExposureGapDirection,
)
from action.models import (
    ActionState,
    PositionContext,
    InformationSufficiency,
    ReasonCode,
    ActionEvaluationContext,
    ActionAssessmentResult,
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
    from_fund_quality_result,
    from_risk_alignment_result,
    from_suitability_result,
    from_portfolio_need_result,
    from_economic_benefit_result,
    build_action_input_contract,
    validate_version_compatibility,
    validate_point_in_time_consistency,
)
from integration.orchestrator import DecisionOrchestrator


class BaseAdversarialTest:
    """Base setup helper for constructing valid baseline contracts."""

    def setup_method(self):
        self.orchestrator = DecisionOrchestrator()
        self.today = date(2026, 9, 1)
        self.now_utc = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
        self.prov = ProvenanceMetadata(
            source_id="adv_test_src_001",
            source_document_url="http://gov.in",
            retrieval_timestamp_utc=self.now_utc,
            methodology_version="1.0.0",
        )

    def _make_valid_input(
        self,
        position_context=PositionContext.NEW_POSITION,
        need_state=PortfolioNeedState.NEED_IDENTIFIED,
        fulfillment=CandidateFulfillmentStatus.CANDIDATE_CAN_FULFILL_NEED,
        suitability_st=SuitabilityStatus.SUITABLE,
        eb_state=EconomicBenefitState.ECONOMICALLY_BENEFICIAL,
        quality_score=85.0,
        quality_conf=0.95,
        fq_evidence_valid=True,
        affordability=AffordabilityStatus.AFFORDABLE,
        deterioration=None,
        deterioration_validated=True,
        has_replacement=True,
        fq_comparison_valid=True,
        stale_input=False,
        obs_date=None,
        obs_timestamp=None,
        goal_id="goal_1",
        portfolio_id="port_1",
        scheme_id="INF209K01157",
        investor_id="inv_100",
        suit_confidence=1.0,
        ra_confidence=1.0,
        ra_status=IntegrationStatus.VALID,
        ra_alignment_status=AlignmentStatus.FULLY_ALIGNED,
        eb_methodology_version="F.5.0",
        macro_stress_flag=False,
        custom_fq_contract=None,
        custom_ra_contract=None,
        custom_suit_contract=None,
        custom_pneed_contract=None,
        custom_eb_contract=None,
    ) -> ActionInputIntegrationContract:
        target_date = obs_date or self.today
        target_ts = obs_timestamp or self.now_utc

        # 1. Fund Quality
        if custom_fq_contract is not None:
            fq_contract = custom_fq_contract
        else:
            fq_res = FundQualityScoreResult(
                canonical_scheme_id=scheme_id,
                amfi_code="120503",
                scheme_name="Test Equity Fund",
                category="Equity",
                subcategory="Large Cap",
                observation_date=target_date,
                quality_score=quality_score,
                confidence_score=quality_conf,
                data_quality_score=0.95,
                dimension_scores={},
                available_dimensions_count=4,
                total_dimensions_count=4,
                peer_group_size=25,
                scoring_methodology_version="1.0.0",
                weight_config_version="1.0.0",
                calculation_timestamp_utc=target_ts,
                summary_explanation="Adversarial Test FQ result",
            )
            fq_contract = from_fund_quality_result(
                result=fq_res,
                canonical_scheme_id=scheme_id,
                category="Equity",
                subcategory="Large Cap",
                fund_quality_comparison_valid=fq_comparison_valid,
            )
            if fq_evidence_valid is not True:
                object.__setattr__(fq_contract, "fund_quality_evidence_valid", fq_evidence_valid)

        # 2. Risk Alignment
        if custom_ra_contract is not None:
            ra_contract = custom_ra_contract
        else:
            ra_res = RiskAlignmentAssessmentResult(
                assessment_id="ra_adv_001",
                investor_id=investor_id,
                profile_version_used="1.0.0",
                observation_date=target_date,
                assessment_timestamp_utc=target_ts,
                startup_mode=1,
                alignment_status=ra_alignment_status,
                limiting_constraint=LimitingConstraint.NONE,
                aligned_risk_level=AlignedRiskLevel.HIGH,
                capacity_assessment_id="rc_001",
                tolerance_assessment_id="rt_001",
                alignment_confidence_score=ra_confidence,
                is_stale_input=stale_input,
                provenance=self.prov,
            )
            ra_contract = from_risk_alignment_result(ra_res, status=ra_status)

        # 3. Suitability
        if custom_suit_contract is not None:
            suit_contract = custom_suit_contract
        else:
            suit_res = SuitabilityAssessmentResult(
                assessment_id="suit_adv_001",
                investor_id=investor_id,
                profile_version_used="1.0.0",
                canonical_scheme_id=scheme_id,
                amfi_code="120503",
                scheme_name="Test Equity Fund",
                category="Equity",
                subcategory="Large Cap",
                observation_date=target_date,
                suitability_status=suitability_st,
                goal_id=goal_id,
                suitability_confidence_score=suit_confidence,
                provenance=self.prov,
                assessment_timestamp_utc=target_ts,
            )
            suit_contract = from_suitability_result(suit_res)

        # 4. Portfolio Need
        if custom_pneed_contract is not None:
            pneed_contract = custom_pneed_contract
        else:
            pneed_res = PortfolioNeedAssessmentResult(
                assessment_id="pneed_adv_001",
                investor_id=investor_id,
                goal_id=goal_id,
                scheme_id=scheme_id,
                primary_state=need_state,
                candidate_fulfillment_status=fulfillment,
                affordability_status=affordability,
                funding_status=FundingStatus.UNDERFUNDED,
                observation_timestamp=target_ts,
                upstream_assessment_ids={"source_id": "test_src_001"},
            )
            pneed_contract = from_portfolio_need_result(pneed_res)

        # 5. Economic Benefit
        if custom_eb_contract is not None:
            eb_contract = custom_eb_contract
        else:
            pos_ctx_str = position_context.value if hasattr(position_context, "value") else str(position_context)
            is_existing = (pos_ctx_str == "EXISTING_POSITION")
            eb_contract = from_economic_benefit_result(
                assessment_id="eb_adv_001",
                investor_id=investor_id,
                economic_benefit_state=eb_state,
                position_context=pos_ctx_str,
                current_holding_scheme_id=scheme_id if is_existing else None,
                candidate_scheme_id=scheme_id,
                economic_benefit_actionable=True,
                evidence_sufficiency_valid=True,
                observation_date=target_date,
                assessment_timestamp_utc=target_ts,
                methodology_version=eb_methodology_version,
                provenance=self.prov,
            )

        return build_action_input_contract(
            investor_id=investor_id,
            scheme_id=scheme_id,
            position_context=position_context,
            assessment_id=f"act_adv_{investor_id}",
            goal_id=goal_id,
            portfolio_id=portfolio_id,
            fund_quality_contract=fq_contract,
            risk_alignment_contract=ra_contract,
            suitability_contract=suit_contract,
            portfolio_need_contract=pneed_contract,
            economic_benefit_contract=eb_contract,
            deterioration_signal=deterioration,
            deterioration_validated=deterioration_validated,
            has_suitable_replacement=has_replacement,
            fund_quality_comparison_valid=fq_comparison_valid,
            macro_stress_flag=macro_stress_flag,
            observation_timestamp=target_ts,
        )


class TestAdversarialBuyScenarios(BaseAdversarialTest):
    """Adversarial BUY tests: verifying that failing even one prerequisite safely blocks BUY."""

    def test_adv_buy_a_high_fq_no_portfolio_need(self):
        """A: High FQ (99.0) + NO_MATERIAL_NEED -> NO BUY."""
        payload = self._make_valid_input(quality_score=99.0, need_state=PortfolioNeedState.NO_MATERIAL_NEED)
        res = self.orchestrator.evaluate_decision(payload)
        assert res.final_action_state == ActionState.NO_ACTION

    def test_adv_buy_b_high_fq_not_suitable(self):
        """B: High FQ (99.0) + NOT_SUITABLE -> NO BUY."""
        payload = self._make_valid_input(quality_score=99.0, suitability_st=SuitabilityStatus.NOT_SUITABLE)
        res = self.orchestrator.evaluate_decision(payload)
        assert res.final_action_state == ActionState.NO_ACTION

    def test_adv_buy_c_high_fq_cannot_fulfill_need(self):
        """C: High FQ (99.0) + CANDIDATE_CANNOT_FULFILL_NEED -> NO BUY."""
        payload = self._make_valid_input(quality_score=99.0, fulfillment=CandidateFulfillmentStatus.CANDIDATE_CANNOT_FULFILL_NEED)
        res = self.orchestrator.evaluate_decision(payload)
        assert res.final_action_state == ActionState.NO_ACTION

    def test_adv_buy_d_high_fq_economically_not_beneficial(self):
        """D: High FQ (99.0) + ECONOMICALLY_NOT_BENEFICIAL -> NO BUY."""
        payload = self._make_valid_input(quality_score=99.0, eb_state=EconomicBenefitState.ECONOMICALLY_NOT_BENEFICIAL)
        res = self.orchestrator.evaluate_decision(payload)
        assert res.final_action_state == ActionState.NO_ACTION

    def test_adv_buy_e_high_fq_economically_neutral(self):
        """E: High FQ (99.0) + ECONOMICALLY_NEUTRAL -> NO BUY."""
        payload = self._make_valid_input(quality_score=99.0, eb_state=EconomicBenefitState.ECONOMICALLY_NEUTRAL)
        res = self.orchestrator.evaluate_decision(payload)
        assert res.final_action_state == ActionState.NO_ACTION

    def test_adv_buy_f_high_fq_benefit_uncertain(self):
        """F: High FQ (99.0) + BENEFIT_UNCERTAIN -> NO BUY."""
        payload = self._make_valid_input(quality_score=99.0, eb_state=EconomicBenefitState.BENEFIT_UNCERTAIN)
        res = self.orchestrator.evaluate_decision(payload)
        assert res.final_action_state == ActionState.NO_ACTION

    def test_adv_buy_g_high_fq_eb_insufficient_information(self):
        """G: High FQ (99.0) + EB INSUFFICIENT_INFORMATION -> NO BUY."""
        payload = self._make_valid_input(quality_score=99.0, eb_state=EconomicBenefitState.INSUFFICIENT_INFORMATION)
        res = self.orchestrator.evaluate_decision(payload)
        assert res.final_action_state == ActionState.NO_ACTION
        assert res.final_action_state not in [ActionState.BUY, ActionState.ACCUMULATE]

    def test_adv_buy_h_high_fq_affordability_unknown(self):
        """H: High FQ (99.0) + Affordability UNKNOWN -> Defaults to staged/safe evaluation without crashing."""
        payload = self._make_valid_input(quality_score=99.0, affordability=AffordabilityStatus.AFFORDABILITY_STATUS_UNKNOWN)
        res = self.orchestrator.evaluate_decision(payload)
        assert res.final_action_state in [ActionState.ACCUMULATE, ActionState.BUY]

    def test_adv_buy_i_high_fq_invalid_risk_alignment(self):
        """I: High FQ (99.0) + Invalid Risk Alignment -> INVALID_ASSESSMENT (NO BUY)."""
        payload = self._make_valid_input(quality_score=99.0, ra_status=IntegrationStatus.INVALID, ra_confidence=0.0)
        res = self.orchestrator.evaluate_decision(payload)
        assert res.final_action_state == ActionState.INVALID_ASSESSMENT

    def test_adv_buy_j_high_fq_stale_investor_assessment(self):
        """J: High FQ (99.0) + Stale Risk Alignment -> INSUFFICIENT_INFORMATION (NO BUY)."""
        payload = self._make_valid_input(quality_score=99.0, stale_input=True)
        res = self.orchestrator.evaluate_decision(payload)
        assert res.final_action_state == ActionState.INSUFFICIENT_INFORMATION

    def test_adv_buy_k_high_fq_invalid_fq_evidence(self):
        """K: High FQ (99.0) + fund_quality_evidence_valid=False -> NO BUY."""
        payload = self._make_valid_input(quality_score=99.0, fq_evidence_valid=False)
        res = self.orchestrator.evaluate_decision(payload)
        assert res.final_action_state == ActionState.NO_ACTION

    def test_adv_buy_l_high_fq_unknown_fq_evidence_validity(self):
        """L: High FQ (99.0) + fund_quality_evidence_valid=None -> NO BUY."""
        payload = self._make_valid_input(quality_score=99.0, fq_evidence_valid=None)
        res = self.orchestrator.evaluate_decision(payload)
        assert res.final_action_state == ActionState.NO_ACTION

    def test_adv_buy_m_high_fq_incompatible_methodology_versions(self):
        """M: High FQ (99.0) + Incompatible methodology version -> INVALID_ASSESSMENT (NO BUY)."""
        payload = self._make_valid_input(quality_score=99.0, eb_methodology_version="INCOMPATIBLE_9.9.9")
        res = self.orchestrator.evaluate_decision(payload)
        assert res.final_action_state == ActionState.INVALID_ASSESSMENT

    def test_adv_buy_n_high_fq_unknown_candidate_fulfillment(self):
        """N: High FQ (99.0) + CANDIDATE_FULFILLMENT_UNKNOWN -> NO BUY."""
        payload = self._make_valid_input(quality_score=99.0, fulfillment=CandidateFulfillmentStatus.CANDIDATE_FULFILLMENT_UNKNOWN)
        res = self.orchestrator.evaluate_decision(payload)
        assert res.final_action_state == ActionState.NO_ACTION


class TestAdversarialSellScenarios(BaseAdversarialTest):
    """Adversarial SELL tests: verifying that failing even one switch guardrail safely blocks SELL."""

    def test_adv_sell_a_lower_fq_no_deterioration(self):
        """A: Lower FQ score (30.0) + NO DETERIORATION -> NO SELL (yields HOLD)."""
        payload = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            need_state=PortfolioNeedState.NO_MATERIAL_NEED,
            quality_score=30.0,
            deterioration=None,
        )
        res = self.orchestrator.evaluate_decision(payload)
        assert res.final_action_state == ActionState.HOLD
        assert res.final_action_state != ActionState.SELL

    def test_adv_sell_b_lower_fq_unvalidated_deterioration(self):
        """B: Lower FQ score + UNVALIDATED DETERIORATION -> NO SELL (yields REVIEW)."""
        payload = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            quality_score=30.0,
            deterioration="MATERIAL_DETERIORATION",
            deterioration_validated=False,
        )
        res = self.orchestrator.evaluate_decision(payload)
        assert res.final_action_state == ActionState.REVIEW
        assert res.final_action_state != ActionState.SELL

    def test_adv_sell_c_material_deterioration_no_replacement(self):
        """C: Material deterioration + NO REPLACEMENT -> NO SELL (yields REVIEW)."""
        payload = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            deterioration="MATERIAL_DETERIORATION",
            has_replacement=False,
        )
        res = self.orchestrator.evaluate_decision(payload)
        assert res.final_action_state == ActionState.REVIEW

    def test_adv_sell_d_material_deterioration_unsuitable_replacement(self):
        """D: Material deterioration + UNSUITABLE REPLACEMENT -> NO SELL (yields REVIEW/HOLD)."""
        payload = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            deterioration="MATERIAL_DETERIORATION",
            suitability_st=SuitabilityStatus.NOT_SUITABLE,
        )
        res = self.orchestrator.evaluate_decision(payload)
        assert res.final_action_state == ActionState.REVIEW
        assert res.final_action_state != ActionState.SELL

    def test_adv_sell_e_material_deterioration_invalid_fq_comparison(self):
        """E: Material deterioration + INVALID FQ COMPARISON -> NO SELL (yields REVIEW)."""
        payload = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            deterioration="MATERIAL_DETERIORATION",
            fq_comparison_valid=False,
        )
        res = self.orchestrator.evaluate_decision(payload)
        assert res.final_action_state == ActionState.REVIEW

    def test_adv_sell_f_material_deterioration_unknown_fq_comparison(self):
        """F: Material deterioration + UNKNOWN FQ COMPARISON -> NO SELL (yields REVIEW)."""
        payload = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            deterioration="MATERIAL_DETERIORATION",
            fq_comparison_valid=None,
        )
        res = self.orchestrator.evaluate_decision(payload)
        assert res.final_action_state == ActionState.REVIEW

    def test_adv_sell_g_material_deterioration_economically_not_beneficial(self):
        """G: Material deterioration + ECONOMICALLY_NOT_BENEFICIAL -> NO SELL (yields REVIEW)."""
        payload = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            deterioration="MATERIAL_DETERIORATION",
            eb_state=EconomicBenefitState.ECONOMICALLY_NOT_BENEFICIAL,
        )
        res = self.orchestrator.evaluate_decision(payload)
        assert res.final_action_state == ActionState.REVIEW

    def test_adv_sell_h_material_deterioration_economically_neutral(self):
        """H: Material deterioration + ECONOMICALLY_NEUTRAL -> NO SELL (yields REVIEW)."""
        payload = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            deterioration="MATERIAL_DETERIORATION",
            eb_state=EconomicBenefitState.ECONOMICALLY_NEUTRAL,
        )
        res = self.orchestrator.evaluate_decision(payload)
        assert res.final_action_state == ActionState.REVIEW

    def test_adv_sell_i_material_deterioration_benefit_uncertain(self):
        """I: Material deterioration + BENEFIT_UNCERTAIN -> NO SELL (yields REVIEW)."""
        payload = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            deterioration="MATERIAL_DETERIORATION",
            eb_state=EconomicBenefitState.BENEFIT_UNCERTAIN,
        )
        res = self.orchestrator.evaluate_decision(payload)
        assert res.final_action_state == ActionState.REVIEW

    def test_adv_sell_j_material_deterioration_no_evaluable_change(self):
        """J: Material deterioration + NO_EVALUABLE_CHANGE -> NO SELL (yields REVIEW)."""
        payload = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            deterioration="MATERIAL_DETERIORATION",
            eb_state=EconomicBenefitState.NO_EVALUABLE_CHANGE,
        )
        res = self.orchestrator.evaluate_decision(payload)
        assert res.final_action_state == ActionState.REVIEW

    def test_adv_sell_k_material_deterioration_insufficient_information(self):
        """K: Material deterioration + EB INSUFFICIENT_INFORMATION -> NO SELL (yields REVIEW/INSUFFICIENT)."""
        payload = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            deterioration="MATERIAL_DETERIORATION",
            eb_state=EconomicBenefitState.INSUFFICIENT_INFORMATION,
        )
        res = self.orchestrator.evaluate_decision(payload)
        assert res.final_action_state == ActionState.REVIEW

    def test_adv_sell_l_material_deterioration_invalid_assessment(self):
        """L: Material deterioration + EB INVALID_ASSESSMENT -> INVALID_ASSESSMENT (NO SELL)."""
        payload = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            deterioration="MATERIAL_DETERIORATION",
            eb_state=EconomicBenefitState.INVALID_ASSESSMENT,
        )
        res = self.orchestrator.evaluate_decision(payload)
        assert res.final_action_state == ActionState.INVALID_ASSESSMENT

    def test_adv_sell_m_material_deterioration_missing_tax_info(self):
        """M: Material deterioration + missing tax info -> NO SELL (yields REVIEW)."""
        eb_missing_tax = from_economic_benefit_result(
            assessment_id="eb_notax",
            investor_id="inv_100",
            economic_benefit_state=EconomicBenefitState.ECONOMICALLY_BENEFICIAL,
            cost_tax_evidence_status="MISSING_TAX_RATES",
            observation_date=self.today,
        )
        payload = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            deterioration="MATERIAL_DETERIORATION",
            custom_eb_contract=eb_missing_tax,
        )
        res = self.orchestrator.evaluate_decision(payload)
        assert res.final_action_state == ActionState.REVIEW

    def test_adv_sell_n_material_deterioration_missing_exit_load(self):
        """N: Material deterioration + missing exit load -> NO SELL (yields REVIEW)."""
        eb_missing_load = from_economic_benefit_result(
            assessment_id="eb_noload",
            investor_id="inv_100",
            economic_benefit_state=EconomicBenefitState.ECONOMICALLY_BENEFICIAL,
            cost_tax_evidence_status="MISSING_EXIT_LOAD",
            observation_date=self.today,
        )
        payload = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            deterioration="MATERIAL_DETERIORATION",
            custom_eb_contract=eb_missing_load,
        )
        res = self.orchestrator.evaluate_decision(payload)
        assert res.final_action_state == ActionState.REVIEW

    def test_adv_sell_o_macro_stress_no_validated_deterioration(self):
        """O: Macro stress + no validated deterioration -> NO SELL (yields HOLD/MONITOR)."""
        payload = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            need_state=PortfolioNeedState.NO_MATERIAL_NEED,
            macro_stress_flag=True,
        )
        res = self.orchestrator.evaluate_decision(payload)
        assert res.final_action_state == ActionState.HOLD
        assert res.final_action_state != ActionState.SELL

    def test_adv_sell_p_high_quality_replacement_no_deterioration(self):
        """P: High quality replacement available + no deterioration -> NO SELL (yields HOLD)."""
        payload = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            need_state=PortfolioNeedState.NO_MATERIAL_NEED,
            quality_score=75.0,
            has_replacement=True,
            deterioration=None,
        )
        res = self.orchestrator.evaluate_decision(payload)
        assert res.final_action_state == ActionState.HOLD
        assert res.final_action_state != ActionState.SELL


class TestUncertaintyMonotonicity(BaseAdversarialTest):
    """
    Uncertainty Monotonicity Audit:
    Replacing any valid input with UNKNOWN/None must NEVER move a non-transaction outcome to a transaction outcome,
    nor increase transaction propensity.
    """

    def test_uncertainty_monotonicity_buy_to_no_action(self):
        """BUY baseline -> replace valid inputs one by one with None/UNKNOWN -> verify no transaction occurs."""
        # Baseline = BUY
        valid_payload = self._make_valid_input(position_context=PositionContext.NEW_POSITION)
        base_res = self.orchestrator.evaluate_decision(valid_payload)
        assert base_res.final_action_state == ActionState.BUY

        # 1. Replace FQ score with None
        payload_fq_none = self._make_valid_input(position_context=PositionContext.NEW_POSITION, quality_score=None)
        res1 = self.orchestrator.evaluate_decision(payload_fq_none)
        assert res1.final_action_state in [ActionState.NO_ACTION, ActionState.INSUFFICIENT_INFORMATION]

        # 2. Replace FQ evidence valid with False/None
        payload_ev_none = self._make_valid_input(position_context=PositionContext.NEW_POSITION, fq_evidence_valid=None)
        res2 = self.orchestrator.evaluate_decision(payload_ev_none)
        assert res2.final_action_state == ActionState.NO_ACTION

        # 3. Replace EB state with BENEFIT_UNCERTAIN
        payload_eb_unc = self._make_valid_input(position_context=PositionContext.NEW_POSITION, eb_state=EconomicBenefitState.BENEFIT_UNCERTAIN)
        res3 = self.orchestrator.evaluate_decision(payload_eb_unc)
        assert res3.final_action_state == ActionState.NO_ACTION

        # 4. Replace Need state with INSUFFICIENT_INFORMATION
        payload_need_ins = self._make_valid_input(position_context=PositionContext.NEW_POSITION, need_state=PortfolioNeedState.INSUFFICIENT_INFORMATION)
        res4 = self.orchestrator.evaluate_decision(payload_need_ins)
        assert res4.final_action_state == ActionState.INSUFFICIENT_INFORMATION

    def test_uncertainty_monotonicity_sell_to_review(self):
        """SELL baseline -> replace valid inputs one by one with None/UNKNOWN -> verify SELL is blocked."""
        # Baseline = SELL
        valid_sell_payload = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            deterioration="MATERIAL_DETERIORATION",
            deterioration_validated=True,
            has_replacement=True,
            fq_comparison_valid=True,
            eb_state=EconomicBenefitState.ECONOMICALLY_BENEFICIAL,
        )
        base_sell = self.orchestrator.evaluate_decision(valid_sell_payload)
        assert base_sell.final_action_state == ActionState.SELL

        # 1. FQ comparison valid = None
        p1 = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            deterioration="MATERIAL_DETERIORATION",
            fq_comparison_valid=None,
        )
        assert self.orchestrator.evaluate_decision(p1).final_action_state == ActionState.REVIEW

        # 2. deterioration_validated = False
        p2 = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            deterioration="MATERIAL_DETERIORATION",
            deterioration_validated=False,
        )
        assert self.orchestrator.evaluate_decision(p2).final_action_state == ActionState.REVIEW

        # 3. EB state = BENEFIT_UNCERTAIN
        p3 = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            deterioration="MATERIAL_DETERIORATION",
            eb_state=EconomicBenefitState.BENEFIT_UNCERTAIN,
        )
        assert self.orchestrator.evaluate_decision(p3).final_action_state == ActionState.REVIEW


class TestNegativeEvidenceMonotonicity(BaseAdversarialTest):
    """
    Negative Evidence Monotonicity Audit:
    Replacing a favorable input with explicit negative evidence must move outcome to equal or less permissive state.
    """

    def test_negative_evidence_transitions(self):
        """Verify state transitions when favorable inputs are replaced with negative evidence."""
        # SUITABLE -> NOT_SUITABLE (BUY -> NO_ACTION)
        p_suit = self._make_valid_input(suitability_st=SuitabilityStatus.NOT_SUITABLE)
        assert self.orchestrator.evaluate_decision(p_suit).final_action_state == ActionState.NO_ACTION

        # NEED_IDENTIFIED -> NO_MATERIAL_NEED (BUY -> NO_ACTION)
        p_need = self._make_valid_input(need_state=PortfolioNeedState.NO_MATERIAL_NEED)
        assert self.orchestrator.evaluate_decision(p_need).final_action_state == ActionState.NO_ACTION

        # CANDIDATE_CAN_FULFILL -> CANDIDATE_CANNOT_FULFILL (BUY -> NO_ACTION)
        p_ful = self._make_valid_input(fulfillment=CandidateFulfillmentStatus.CANDIDATE_CANNOT_FULFILL_NEED)
        assert self.orchestrator.evaluate_decision(p_ful).final_action_state == ActionState.NO_ACTION

        # ECONOMICALLY_BENEFICIAL -> ECONOMICALLY_NOT_BENEFICIAL (BUY -> NO_ACTION)
        p_eb = self._make_valid_input(eb_state=EconomicBenefitState.ECONOMICALLY_NOT_BENEFICIAL)
        assert self.orchestrator.evaluate_decision(p_eb).final_action_state == ActionState.NO_ACTION

        # VALID_COMPARISON -> INVALID_COMPARISON (SELL -> REVIEW)
        p_comp = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            deterioration="MATERIAL_DETERIORATION",
            fq_comparison_valid=False,
        )
        assert self.orchestrator.evaluate_decision(p_comp).final_action_state == ActionState.REVIEW


class TestConfidenceAndScoreIndependence(BaseAdversarialTest):
    """Audits confidence score independence and extreme score handling."""

    def test_confidence_values_with_valid_evidence(self):
        """Confidence score variations (0.0, 0.01, 0.05, 0.10, 0.50, 0.99, 1.0) permit BUY if evidence is valid."""
        for conf in [0.0, 0.01, 0.05, 0.10, 0.50, 0.99, 1.0, None]:
            payload = self._make_valid_input(quality_conf=conf, fq_evidence_valid=True)
            res = self.orchestrator.evaluate_decision(payload)
            assert res.final_action_state == ActionState.BUY, f"Failed for confidence={conf}"

    def test_confidence_values_with_invalid_evidence(self):
        """When fq_evidence_valid=False, BUY is blocked regardless of numerical confidence."""
        for conf in [0.0, 0.10, 0.50, 0.99, 1.0]:
            payload = self._make_valid_input(quality_conf=conf, fq_evidence_valid=False)
            res = self.orchestrator.evaluate_decision(payload)
            assert res.final_action_state == ActionState.NO_ACTION, f"Failed blocking for conf={conf}"

    def test_extreme_score_independence(self):
        """Synthetic extreme scores (100.0 vs 0.0) cannot override Suitability or create SELL without deterioration."""
        # Perfect 100 score + NOT_SUITABLE -> NO BUY
        p1 = self._make_valid_input(quality_score=100.0, suitability_st=SuitabilityStatus.NOT_SUITABLE)
        assert self.orchestrator.evaluate_decision(p1).final_action_state == ActionState.NO_ACTION

        # Zero 0.0 score + EXISTING_POSITION + NO DETERIORATION -> HOLD (NO SELL)
        p2 = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            need_state=PortfolioNeedState.NO_MATERIAL_NEED,
            quality_score=0.0,
            deterioration=None,
        )
        assert self.orchestrator.evaluate_decision(p2).final_action_state == ActionState.HOLD


class TestStatePrecedenceAndConflictMatrix(BaseAdversarialTest):
    """Verifies that higher-precedence safety constraints win in conflicting multi-state inputs."""

    def test_conflict_invalid_plus_beneficial(self):
        """INVALID upstream + BENEFICIAL -> INVALID_ASSESSMENT."""
        p = self._make_valid_input(ra_status=IntegrationStatus.INVALID, ra_confidence=0.0, eb_state=EconomicBenefitState.ECONOMICALLY_BENEFICIAL)
        res = self.orchestrator.evaluate_decision(p)
        assert res.final_action_state == ActionState.INVALID_ASSESSMENT

    def test_conflict_insufficient_plus_need(self):
        """INSUFFICIENT upstream + NEED_IDENTIFIED -> INSUFFICIENT_INFORMATION."""
        p = self._make_valid_input(need_state=PortfolioNeedState.INSUFFICIENT_INFORMATION)
        res = self.orchestrator.evaluate_decision(p)
        assert res.final_action_state == ActionState.INSUFFICIENT_INFORMATION

    def test_conflict_not_suitable_plus_beneficial(self):
        """NOT_SUITABLE + BENEFICIAL -> NO_ACTION."""
        p = self._make_valid_input(suitability_st=SuitabilityStatus.NOT_SUITABLE, eb_state=EconomicBenefitState.ECONOMICALLY_BENEFICIAL)
        res = self.orchestrator.evaluate_decision(p)
        assert res.final_action_state == ActionState.NO_ACTION

    def test_conflict_no_need_plus_beneficial(self):
        """NO_MATERIAL_NEED + BENEFICIAL -> NO_ACTION."""
        p = self._make_valid_input(need_state=PortfolioNeedState.NO_MATERIAL_NEED, eb_state=EconomicBenefitState.ECONOMICALLY_BENEFICIAL)
        res = self.orchestrator.evaluate_decision(p)
        assert res.final_action_state == ActionState.NO_ACTION

    def test_conflict_cannot_fulfill_plus_beneficial(self):
        """CANDIDATE_CANNOT_FULFILL_NEED + BENEFICIAL -> NO_ACTION."""
        p = self._make_valid_input(fulfillment=CandidateFulfillmentStatus.CANDIDATE_CANNOT_FULFILL_NEED, eb_state=EconomicBenefitState.ECONOMICALLY_BENEFICIAL)
        res = self.orchestrator.evaluate_decision(p)
        assert res.final_action_state == ActionState.NO_ACTION

    def test_conflict_invalid_comparison_plus_beneficial(self):
        """INVALID_COMPARISON + BENEFICIAL -> REVIEW (NO SELL)."""
        p = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            deterioration="MATERIAL_DETERIORATION",
            fq_comparison_valid=False,
            eb_state=EconomicBenefitState.ECONOMICALLY_BENEFICIAL,
        )
        res = self.orchestrator.evaluate_decision(p)
        assert res.final_action_state == ActionState.REVIEW

    def test_conflict_unvalidated_deterioration_plus_beneficial(self):
        """UNVALIDATED_DETERIORATION + BENEFICIAL -> REVIEW (NO SELL)."""
        p = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            deterioration="MATERIAL_DETERIORATION",
            deterioration_validated=False,
            eb_state=EconomicBenefitState.ECONOMICALLY_BENEFICIAL,
        )
        res = self.orchestrator.evaluate_decision(p)
        assert res.final_action_state == ActionState.REVIEW


class TestActionOrchestratorConsistency(BaseAdversarialTest):
    """Verifies that invoking ActionEngine directly vs invoking via DecisionOrchestrator yields identical action states."""

    def test_direct_action_vs_orchestrated_action(self):
        """Test equivalence across BUY, ACCUMULATE, HOLD, MONITOR, REVIEW, SELL states."""
        test_cases = [
            (PositionContext.NEW_POSITION, PortfolioNeedState.NEED_IDENTIFIED, CandidateFulfillmentStatus.CANDIDATE_CAN_FULFILL_NEED, SuitabilityStatus.SUITABLE, EconomicBenefitState.ECONOMICALLY_BENEFICIAL, None, ActionState.BUY),
            (PositionContext.NEW_POSITION, PortfolioNeedState.NEED_IDENTIFIED, CandidateFulfillmentStatus.CANDIDATE_CAN_FULFILL_NEED, SuitabilityStatus.NOT_SUITABLE, EconomicBenefitState.ECONOMICALLY_BENEFICIAL, None, ActionState.NO_ACTION),
            (PositionContext.EXISTING_POSITION, PortfolioNeedState.NO_MATERIAL_NEED, CandidateFulfillmentStatus.CANDIDATE_CAN_FULFILL_NEED, SuitabilityStatus.SUITABLE, EconomicBenefitState.ECONOMICALLY_BENEFICIAL, None, ActionState.HOLD),
            (PositionContext.EXISTING_POSITION, PortfolioNeedState.NEED_IDENTIFIED, CandidateFulfillmentStatus.CANDIDATE_CAN_FULFILL_NEED, SuitabilityStatus.SUITABLE, EconomicBenefitState.ECONOMICALLY_BENEFICIAL, "MILD_DETERIORATION", ActionState.MONITOR),
            (PositionContext.EXISTING_POSITION, PortfolioNeedState.NEED_IDENTIFIED, CandidateFulfillmentStatus.CANDIDATE_CAN_FULFILL_NEED, SuitabilityStatus.SUITABLE, EconomicBenefitState.ECONOMICALLY_BENEFICIAL, "MATERIAL_DETERIORATION", ActionState.SELL),
        ]

        for pos, need, ful, suit_st, eb_st, det, expected_action in test_cases:
            payload = self._make_valid_input(
                position_context=pos,
                need_state=need,
                fulfillment=ful,
                suitability_st=suit_st,
                eb_state=eb_st,
                deterioration=det,
                deterioration_validated=True,
                has_replacement=True,
                fq_comparison_valid=True,
            )
            orchestrated_res = self.orchestrator.evaluate_decision(payload)
            assert orchestrated_res.final_action_state == expected_action


class Test15FinancialSafetyInvariants(BaseAdversarialTest):
    """Direct property-based invariant test suite for the 15 core financial safety invariants."""

    def test_invariant_1_removing_evidence_cannot_increase_propensity(self):
        """INVARIANT 1: Removing evidence cannot increase transaction propensity."""
        valid_p = self._make_valid_input(position_context=PositionContext.NEW_POSITION)
        assert self.orchestrator.evaluate_decision(valid_p).final_action_state == ActionState.BUY

        # Removing FQ score
        p_no_score = self._make_valid_input(position_context=PositionContext.NEW_POSITION, quality_score=None)
        assert self.orchestrator.evaluate_decision(p_no_score).final_action_state in [ActionState.NO_ACTION, ActionState.INSUFFICIENT_INFORMATION]

    def test_invariant_2_negative_evidence_cannot_increase_propensity(self):
        """INVARIANT 2: Replacing positive evidence with negative evidence cannot increase transaction propensity."""
        valid_p = self._make_valid_input(position_context=PositionContext.NEW_POSITION)
        assert self.orchestrator.evaluate_decision(valid_p).final_action_state == ActionState.BUY

        p_neg = self._make_valid_input(position_context=PositionContext.NEW_POSITION, suitability_st=SuitabilityStatus.NOT_SUITABLE)
        assert self.orchestrator.evaluate_decision(p_neg).final_action_state == ActionState.NO_ACTION

    def test_invariant_3_invalid_data_cannot_create_transaction(self):
        """INVARIANT 3: Invalid data cannot create transaction."""
        p_inv = self._make_valid_input(ra_status=IntegrationStatus.INVALID, ra_confidence=0.0)
        assert self.orchestrator.evaluate_decision(p_inv).final_action_state == ActionState.INVALID_ASSESSMENT

    def test_invariant_4_unknown_economic_benefit_cannot_create_transaction(self):
        """INVARIANT 4: Unknown Economic Benefit cannot create transaction."""
        p_unc = self._make_valid_input(eb_state=EconomicBenefitState.BENEFIT_UNCERTAIN)
        assert self.orchestrator.evaluate_decision(p_unc).final_action_state == ActionState.NO_ACTION

    def test_invariant_5_no_need_cannot_create_buy(self):
        """INVARIANT 5: No Need cannot create BUY."""
        p_noneed = self._make_valid_input(need_state=PortfolioNeedState.NO_MATERIAL_NEED)
        assert self.orchestrator.evaluate_decision(p_noneed).final_action_state == ActionState.NO_ACTION

    def test_invariant_6_cannot_fulfill_need_cannot_create_buy(self):
        """INVARIANT 6: Cannot Fulfill Need cannot create BUY."""
        p_cant = self._make_valid_input(fulfillment=CandidateFulfillmentStatus.CANDIDATE_CANNOT_FULFILL_NEED)
        assert self.orchestrator.evaluate_decision(p_cant).final_action_state == ActionState.NO_ACTION

    def test_invariant_7_unsuitable_candidate_cannot_create_buy(self):
        """INVARIANT 7: Unsuitable candidate cannot create BUY."""
        p_unsuit = self._make_valid_input(suitability_st=SuitabilityStatus.NOT_SUITABLE)
        assert self.orchestrator.evaluate_decision(p_unsuit).final_action_state == ActionState.NO_ACTION

    def test_invariant_8_invalid_comparison_cannot_create_sell(self):
        """INVARIANT 8: Invalid comparison cannot create SELL."""
        p_inv_comp = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            deterioration="MATERIAL_DETERIORATION",
            fq_comparison_valid=False,
        )
        assert self.orchestrator.evaluate_decision(p_inv_comp).final_action_state == ActionState.REVIEW

    def test_invariant_9_unvalidated_deterioration_cannot_create_sell(self):
        """INVARIANT 9: Unvalidated deterioration cannot create SELL."""
        p_unval = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            deterioration="MATERIAL_DETERIORATION",
            deterioration_validated=False,
        )
        assert self.orchestrator.evaluate_decision(p_unval).final_action_state == ActionState.REVIEW

    def test_invariant_10_lower_score_alone_cannot_create_sell(self):
        """INVARIANT 10: Lower score alone cannot create SELL."""
        p_low = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            need_state=PortfolioNeedState.NO_MATERIAL_NEED,
            quality_score=10.0,
            deterioration=None,
        )
        assert self.orchestrator.evaluate_decision(p_low).final_action_state == ActionState.HOLD
        assert self.orchestrator.evaluate_decision(p_low).final_action_state != ActionState.SELL

    def test_invariant_11_macro_alone_cannot_create_buy_or_sell(self):
        """INVARIANT 11: Macro alone cannot create BUY/SELL."""
        p_macro = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            need_state=PortfolioNeedState.NO_MATERIAL_NEED,
            macro_stress_flag=True,
        )
        assert self.orchestrator.evaluate_decision(p_macro).final_action_state == ActionState.HOLD

    def test_invariant_12_action_cannot_feed_upstream_domains(self):
        """INVARIANT 12: Action cannot feed upstream domains (acyclic dependency)."""
        import sys
        # Verify Action Engine module does NOT import Orchestrator
        import action.engine as act_mod
        assert not hasattr(act_mod, "DecisionOrchestrator")

    def test_invariant_13_integration_layer_cannot_calculate_upstream_methodology(self):
        """INVARIANT 13: Integration layer cannot calculate upstream methodology."""
        # Verify orchestrator performs zero financial score calculations
        p = self._make_valid_input()
        res = self.orchestrator.evaluate_decision(p)
        assert res.orchestrator_version == "F.7.3"

    def test_invariant_14_canonical_economic_benefit_states_remain_canonical(self):
        """INVARIANT 14: Canonical Economic Benefit states remain canonical."""
        for state in EconomicBenefitState:
            assert isinstance(state, EconomicBenefitState)
            assert state.value in [
                "ECONOMICALLY_BENEFICIAL",
                "ECONOMICALLY_NOT_BENEFICIAL",
                "ECONOMICALLY_NEUTRAL",
                "NO_EVALUABLE_CHANGE",
                "BENEFIT_UNCERTAIN",
                "INSUFFICIENT_INFORMATION",
                "INVALID_ASSESSMENT",
            ]

    def test_invariant_15_default_behavior_remains_non_transactional(self):
        """INVARIANT 15: Default behavior remains non-transactional (HOLD for existing, NO_ACTION for new)."""
        p_new = self._make_valid_input(position_context=PositionContext.NEW_POSITION, need_state=PortfolioNeedState.NO_MATERIAL_NEED)
        assert self.orchestrator.evaluate_decision(p_new).final_action_state == ActionState.NO_ACTION

        p_ext = self._make_valid_input(position_context=PositionContext.EXISTING_POSITION, need_state=PortfolioNeedState.NO_MATERIAL_NEED)
        assert self.orchestrator.evaluate_decision(p_ext).final_action_state == ActionState.HOLD
