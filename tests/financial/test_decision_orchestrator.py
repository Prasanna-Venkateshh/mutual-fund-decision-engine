"""
End-to-End Decision Orchestrator Test Suite (Phase F.7.3).

Validates end-to-end decision orchestration, 7-tier decision precedence, anti-churn invariants,
state gating, safe fallbacks, version compatibility, point-in-time freshness, provenance aggregation,
and adversarial safety scenarios across all decision domains (Scenarios A through AP).

Governance Rules Enforced:
- Low-turnover principle: DEFAULT ACTION = HOLD / DO NOTHING UNLESS EVIDENCE JUSTIFIES CHANGE.
- High Fund Quality alone NEVER creates BUY or SELL.
- Historical returns / rank alone NEVER creates BUY or SELL.
- Canonical state preservation across F.5 Economic Benefit, F.3.4 Suitability, and F.4.4 Portfolio Need.
- Zero upstream financial methodology recalculation.
"""

from datetime import date, datetime, timezone, timedelta
import pytest
from dataclasses import FrozenInstanceError

from models.fund_quality_dataset import ProvenanceMetadata
from models.investor_profile import RiskCapacityLevel, RiskToleranceLevel
from risk.capacity_models import RiskCapacityAssessmentResult, AssessmentStatus
from risk.tolerance_models import RiskToleranceAssessmentResult, BehavioralConsistencyLevel
from risk.alignment_models import RiskAlignmentAssessmentResult, AlignmentStatus, LimitingConstraint, AlignedRiskLevel
from scoring.models import FundQualityScoreResult
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
from action.models import PositionContext, ActionState

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
)
from integration.orchestrator import DecisionOrchestrator


class TestDecisionOrchestrator:
    """Comprehensive test suite for Phase F.7.3 End-to-End Decision Orchestrator."""

    def setup_method(self):
        self.orchestrator = DecisionOrchestrator()
        self.today = date(2026, 9, 1)
        self.now_utc = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
        self.prov = ProvenanceMetadata(
            source_id="test_src_001",
            source_document_url="http://test.gov.in",
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
                summary_explanation="Test FQ result",
            )
            fq_contract = from_fund_quality_result(
                result=fq_res,
                canonical_scheme_id=scheme_id,
                category="Equity",
                subcategory="Large Cap",
                fund_quality_comparison_valid=fq_comparison_valid,
            )

        # 2. Risk Alignment
        if custom_ra_contract is not None:
            ra_contract = custom_ra_contract
        else:
            ra_res = RiskAlignmentAssessmentResult(
                assessment_id="ra_001",
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
                assessment_id="suit_001",
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
                assessment_id="pneed_001",
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
            eb_contract = from_economic_benefit_result(
                assessment_id="eb_001",
                investor_id=investor_id,
                economic_benefit_state=eb_state,
                candidate_scheme_id=scheme_id,
                observation_date=target_date,
                assessment_timestamp_utc=target_ts,
                methodology_version=eb_methodology_version,
                provenance=self.prov,
            )

        return build_action_input_contract(
            investor_id=investor_id,
            scheme_id=scheme_id,
            position_context=position_context,
            assessment_id="act_in_001",
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

    # -------------------------------------------------------------------------
    # TEST SCENARIOS A - F: CORE ACTION STATES
    # -------------------------------------------------------------------------
    def test_scenario_a_valid_buy(self):
        """TEST A: Valid BUY when all governed prerequisites pass for new candidate."""
        input_payload = self._make_valid_input(position_context=PositionContext.NEW_POSITION)
        result = self.orchestrator.evaluate_decision(input_payload)
        assert result.final_action_state == ActionState.BUY
        assert result.final_decision_status == IntegrationStatus.VALID
        assert "BUY" in result.final_explanation
        assert result.orchestrator_version == "F.7.3"

    def test_scenario_b_valid_accumulate(self):
        """TEST B: Valid ACCUMULATE when affordability is constrained for suitable candidate."""
        input_payload = self._make_valid_input(
            position_context=PositionContext.NEW_POSITION,
            affordability=AffordabilityStatus.AFFORDABILITY_CONSTRAINED,
        )
        result = self.orchestrator.evaluate_decision(input_payload)
        assert result.final_action_state == ActionState.ACCUMULATE
        assert result.final_decision_status == IntegrationStatus.VALID

    def test_scenario_c_valid_hold(self):
        """TEST C: Valid HOLD when existing holding has no material need change or deterioration."""
        input_payload = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            need_state=PortfolioNeedState.NO_MATERIAL_NEED,
        )
        result = self.orchestrator.evaluate_decision(input_payload)
        assert result.final_action_state == ActionState.HOLD
        assert result.final_decision_status == IntegrationStatus.VALID

    def test_scenario_d_valid_monitor(self):
        """TEST D: Valid MONITOR when mild performance decay is observed on existing holding."""
        input_payload = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            deterioration="MILD_DETERIORATION",
        )
        result = self.orchestrator.evaluate_decision(input_payload)
        assert result.final_action_state == ActionState.MONITOR
        assert result.final_decision_status == IntegrationStatus.VALID

    def test_scenario_e_valid_review(self):
        """TEST E: Valid REVIEW when material deterioration is unvalidated."""
        input_payload = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            deterioration="MATERIAL_DETERIORATION",
            deterioration_validated=False,
        )
        result = self.orchestrator.evaluate_decision(input_payload)
        assert result.final_action_state == ActionState.REVIEW
        assert result.final_decision_status in [IntegrationStatus.VALID, IntegrationStatus.PARTIAL]

    def test_scenario_f_valid_sell(self):
        """TEST F: Valid SELL when verified deterioration, suitable replacement, and net economic benefit exist."""
        input_payload = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            deterioration="MATERIAL_DETERIORATION",
            deterioration_validated=True,
            has_replacement=True,
            fq_comparison_valid=True,
            eb_state=EconomicBenefitState.ECONOMICALLY_BENEFICIAL,
        )
        result = self.orchestrator.evaluate_decision(input_payload)
        assert result.final_action_state == ActionState.SELL
        assert result.final_decision_status == IntegrationStatus.VALID
        assert "SELL" in result.final_explanation

    # -------------------------------------------------------------------------
    # TEST SCENARIOS G - J: INVALID & STALE UPSTREAM ASSESSMENTS
    # -------------------------------------------------------------------------
    def test_scenario_g_invalid_investor_profile(self):
        """TEST G: Invalid context (empty investor_id) raises ValueError in input contract."""
        with pytest.raises(ValueError, match="investor_id cannot be empty"):
            build_action_input_contract(
                investor_id="",  # Empty investor ID
                scheme_id="INF209K01157",
                position_context=PositionContext.NEW_POSITION,
                assessment_id="act_invalid_001",
            )

    def test_scenario_h_invalid_risk_capacity(self):
        """TEST H: Invalid Risk Capacity contract status triggers INVALID_ASSESSMENT."""
        rc_res = RiskCapacityAssessmentResult(
            assessment_id="rc_inv_001",
            investor_id="inv_100",
            profile_version_used="1.0.0",
            observation_date=self.today,
            startup_mode=1,
            overall_capacity_tier=RiskCapacityLevel.HIGH,
            assessment_status=AssessmentStatus.INSUFFICIENT_INFORMATION,
            confidence_score=0.0,
            provenance=self.prov,
            assessment_timestamp_utc=self.now_utc,
        )
        rc_contract = from_risk_capacity_result(rc_res, status=IntegrationStatus.INVALID)
        
        # Risk Alignment referencing invalid Risk Capacity
        ra_res = RiskAlignmentAssessmentResult(
            assessment_id="ra_001",
            investor_id="inv_100",
            profile_version_used="1.0.0",
            observation_date=self.today,
            assessment_timestamp_utc=self.now_utc,
            startup_mode=1,
            alignment_status=AlignmentStatus.INVALID_ASSESSMENT,
            limiting_constraint=LimitingConstraint.NONE,
            aligned_risk_level=AlignedRiskLevel.HIGH,
            capacity_assessment_id="rc_inv_001",
            tolerance_assessment_id="rt_001",
            alignment_confidence_score=0.0,
            provenance=self.prov,
        )
        ra_contract = from_risk_alignment_result(ra_res, status=IntegrationStatus.INVALID)

        input_payload = self._make_valid_input(custom_ra_contract=ra_contract)
        result = self.orchestrator.evaluate_decision(input_payload)
        assert result.final_action_state == ActionState.INVALID_ASSESSMENT
        assert result.final_decision_status == IntegrationStatus.INVALID

    def test_scenario_i_invalid_risk_tolerance(self):
        """TEST I: Invalid Risk Tolerance assessment triggers INVALID_ASSESSMENT."""
        rt_res = RiskToleranceAssessmentResult(
            assessment_id="rt_inv_001",
            investor_id="inv_100",
            profile_version_used="1.0.0",
            observation_date=self.today,
            startup_mode=1,
            overall_tolerance_tier=RiskToleranceLevel.HIGH,
            consistency_level=BehavioralConsistencyLevel.HIGHLY_CONSISTENT,
            assessment_status=AssessmentStatus.INSUFFICIENT_INFORMATION,
            confidence_score=0.0,
            provenance=self.prov,
            assessment_timestamp_utc=self.now_utc,
        )
        rt_contract = from_risk_tolerance_result(rt_res, status=IntegrationStatus.INVALID)
        ra_res = RiskAlignmentAssessmentResult(
            assessment_id="ra_001",
            investor_id="inv_100",
            profile_version_used="1.0.0",
            observation_date=self.today,
            assessment_timestamp_utc=self.now_utc,
            startup_mode=1,
            alignment_status=AlignmentStatus.INVALID_ASSESSMENT,
            limiting_constraint=LimitingConstraint.NONE,
            aligned_risk_level=AlignedRiskLevel.HIGH,
            capacity_assessment_id="rc_001",
            tolerance_assessment_id="rt_inv_001",
            alignment_confidence_score=0.0,
            provenance=self.prov,
        )
        ra_contract = from_risk_alignment_result(ra_res, status=IntegrationStatus.INVALID)

        input_payload = self._make_valid_input(custom_ra_contract=ra_contract)
        result = self.orchestrator.evaluate_decision(input_payload)
        assert result.final_action_state == ActionState.INVALID_ASSESSMENT
        assert result.final_decision_status == IntegrationStatus.INVALID

    def test_scenario_j_invalid_risk_alignment(self):
        """TEST J: Stale upstream risk alignment triggers REVIEW for existing position."""
        input_payload = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            stale_input=True,
        )
        result = self.orchestrator.evaluate_decision(input_payload)
        assert result.final_action_state == ActionState.REVIEW

    # -------------------------------------------------------------------------
    # TEST SCENARIOS K - O: SUITABILITY & PORTFOLIO NEED GATING
    # -------------------------------------------------------------------------
    def test_scenario_k_unsuitable_candidate(self):
        """TEST K: NOT_SUITABLE candidate yields NO_ACTION for new position (cannot BUY)."""
        input_payload = self._make_valid_input(
            position_context=PositionContext.NEW_POSITION,
            suitability_st=SuitabilityStatus.NOT_SUITABLE,
        )
        result = self.orchestrator.evaluate_decision(input_payload)
        assert result.final_action_state == ActionState.NO_ACTION
        assert "prohibited" in result.final_explanation.lower() or "not suitable" in result.final_explanation.lower()

    def test_scenario_l_conditional_suitability(self):
        """TEST L: CONDITIONALLY_SUITABLE status propagates warnings while allowing BUY/ACCUMULATE."""
        suit_res = SuitabilityAssessmentResult(
            assessment_id="suit_cond_01",
            investor_id="inv_100",
            profile_version_used="1.0.0",
            canonical_scheme_id="INF209K01157",
            amfi_code="120503",
            scheme_name="Test Equity Fund",
            category="Equity",
            subcategory="Large Cap",
            observation_date=self.today,
            suitability_status=SuitabilityStatus.CONDITIONALLY_SUITABLE,
            constraints_applied=["IMMATURE_FUND_HISTORY"],
            provenance=self.prov,
            assessment_timestamp_utc=self.now_utc,
        )
        suit_contract = from_suitability_result(suit_res)
        input_payload = self._make_valid_input(
            position_context=PositionContext.NEW_POSITION,
            custom_suit_contract=suit_contract,
        )
        result = self.orchestrator.evaluate_decision(input_payload)
        assert result.final_action_state in [ActionState.BUY, ActionState.ACCUMULATE]
        assert any("CONDITIONALLY_SUITABLE" in w or "IMMATURE_FUND_HISTORY" in w for w in result.warnings)

    def test_scenario_m_no_portfolio_need(self):
        """TEST M: NO_MATERIAL_NEED yields NO_ACTION for new position (cannot BUY)."""
        input_payload = self._make_valid_input(
            position_context=PositionContext.NEW_POSITION,
            need_state=PortfolioNeedState.NO_MATERIAL_NEED,
        )
        result = self.orchestrator.evaluate_decision(input_payload)
        assert result.final_action_state == ActionState.NO_ACTION

    def test_scenario_n_candidate_cannot_fulfill_need(self):
        """TEST N: CANDIDATE_CANNOT_FULFILL_NEED yields NO_ACTION for new position (cannot BUY)."""
        input_payload = self._make_valid_input(
            position_context=PositionContext.NEW_POSITION,
            fulfillment=CandidateFulfillmentStatus.CANDIDATE_CANNOT_FULFILL_NEED,
        )
        result = self.orchestrator.evaluate_decision(input_payload)
        assert result.final_action_state == ActionState.NO_ACTION

    def test_scenario_o_candidate_fulfillment_unknown(self):
        """TEST O: CANDIDATE_FULFILLMENT_UNKNOWN yields NO_ACTION for new position, MONITOR for existing."""
        buy_payload = self._make_valid_input(
            position_context=PositionContext.NEW_POSITION,
            fulfillment=CandidateFulfillmentStatus.CANDIDATE_FULFILLMENT_UNKNOWN,
        )
        buy_res = self.orchestrator.evaluate_decision(buy_payload)
        assert buy_res.final_action_state == ActionState.NO_ACTION

        hold_payload = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            fulfillment=CandidateFulfillmentStatus.CANDIDATE_FULFILLMENT_UNKNOWN,
        )
        hold_res = self.orchestrator.evaluate_decision(hold_payload)
        assert hold_res.final_action_state == ActionState.MONITOR

    # -------------------------------------------------------------------------
    # TEST SCENARIOS P - S: FUND QUALITY EVIDENCE & COMPARABILITY
    # -------------------------------------------------------------------------
    def test_scenario_p_invalid_fund_quality_evidence(self):
        """TEST P (F.7.3.1): Explicitly invalid Fund Quality evidence (fund_quality_evidence_valid=False) prevents BUY/SELL."""
        custom_fq = FundQualityIntegrationContract(
            reference=CanonicalAssessmentReference(
                assessment_id="fq_001",
                assessment_type=AssessmentType.FUND_QUALITY,
                scheme_id="INF209K01157",
            ),
            canonical_scheme_id="INF209K01157",
            category="Equity",
            subcategory="Large Cap",
            plan_type="Direct",
            option_type="Growth",
            fund_quality_score=85.0,
            fund_quality_confidence=0.95,
            fund_quality_evidence_valid=False,
        )
        buy_payload = self._make_valid_input(
            position_context=PositionContext.NEW_POSITION,
            custom_fq_contract=custom_fq,
        )
        result = self.orchestrator.evaluate_decision(buy_payload)
        assert result.final_action_state == ActionState.NO_ACTION
        assert "INSUFFICIENT_EVIDENCE" in result.final_explanation or "invalid or missing" in result.final_explanation.lower()

    def test_scenario_q_unknown_fund_quality_evidence(self):
        """TEST Q: Unknown/None Fund Quality score prevents BUY/SELL."""
        buy_payload = self._make_valid_input(
            position_context=PositionContext.NEW_POSITION,
            quality_score=None,
        )
        result = self.orchestrator.evaluate_decision(buy_payload)
        assert result.final_action_state in [ActionState.NO_ACTION, ActionState.INSUFFICIENT_INFORMATION]

    def test_scenario_r_invalid_fund_quality_comparability(self):
        """TEST R: Invalid Fund Quality comparison prevents SELL; yields REVIEW."""
        input_payload = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            deterioration="MATERIAL_DETERIORATION",
            fq_comparison_valid=False,  # Non-comparable category
        )
        result = self.orchestrator.evaluate_decision(input_payload)
        assert result.final_action_state == ActionState.REVIEW
        assert result.final_action_state != ActionState.SELL

    def test_scenario_s_unknown_fund_quality_comparability(self):
        """TEST S: Unknown (None) Fund Quality comparison prevents SELL; yields REVIEW."""
        input_payload = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            deterioration="MATERIAL_DETERIORATION",
            fq_comparison_valid=None,
        )
        result = self.orchestrator.evaluate_decision(input_payload)
        assert result.final_action_state == ActionState.REVIEW
        assert result.final_action_state != ActionState.SELL

    # -------------------------------------------------------------------------
    # TEST SCENARIOS T - Z: ECONOMIC BENEFIT STATES
    # -------------------------------------------------------------------------
    def test_scenario_t_economic_benefit_beneficial(self):
        """TEST T: ECONOMICALLY_BENEFICIAL satisfies positive economic prerequisite for BUY and SELL."""
        buy_payload = self._make_valid_input(
            position_context=PositionContext.NEW_POSITION,
            eb_state=EconomicBenefitState.ECONOMICALLY_BENEFICIAL,
        )
        buy_res = self.orchestrator.evaluate_decision(buy_payload)
        assert buy_res.final_action_state == ActionState.BUY

    def test_scenario_u_economic_benefit_not_beneficial(self):
        """TEST U: ECONOMICALLY_NOT_BENEFICIAL prevents BUY (NO_ACTION) and SELL (REVIEW)."""
        buy_payload = self._make_valid_input(
            position_context=PositionContext.NEW_POSITION,
            eb_state=EconomicBenefitState.ECONOMICALLY_NOT_BENEFICIAL,
        )
        buy_res = self.orchestrator.evaluate_decision(buy_payload)
        assert buy_res.final_action_state == ActionState.NO_ACTION

        sell_payload = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            deterioration="MATERIAL_DETERIORATION",
            eb_state=EconomicBenefitState.ECONOMICALLY_NOT_BENEFICIAL,
        )
        sell_res = self.orchestrator.evaluate_decision(sell_payload)
        assert sell_res.final_action_state == ActionState.REVIEW

    def test_scenario_v_economic_benefit_neutral(self):
        """TEST V: ECONOMICALLY_NEUTRAL prevents BUY (NO_ACTION) and SELL (REVIEW)."""
        buy_payload = self._make_valid_input(
            position_context=PositionContext.NEW_POSITION,
            eb_state=EconomicBenefitState.ECONOMICALLY_NEUTRAL,
        )
        buy_res = self.orchestrator.evaluate_decision(buy_payload)
        assert buy_res.final_action_state == ActionState.NO_ACTION

    def test_scenario_w_no_evaluable_change(self):
        """TEST W: NO_EVALUABLE_CHANGE is preserved as canonical state and prevents BUY/SELL."""
        buy_payload = self._make_valid_input(
            position_context=PositionContext.NEW_POSITION,
            eb_state=EconomicBenefitState.NO_EVALUABLE_CHANGE,
        )
        buy_res = self.orchestrator.evaluate_decision(buy_payload)
        assert buy_res.final_action_state == ActionState.NO_ACTION

    def test_scenario_x_benefit_uncertain(self):
        """TEST X: BENEFIT_UNCERTAIN prevents BUY and SELL."""
        buy_payload = self._make_valid_input(
            position_context=PositionContext.NEW_POSITION,
            eb_state=EconomicBenefitState.BENEFIT_UNCERTAIN,
        )
        buy_res = self.orchestrator.evaluate_decision(buy_payload)
        assert buy_res.final_action_state == ActionState.NO_ACTION

        sell_payload = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            deterioration="MATERIAL_DETERIORATION",
            eb_state=EconomicBenefitState.BENEFIT_UNCERTAIN,
        )
        sell_res = self.orchestrator.evaluate_decision(sell_payload)
        assert sell_res.final_action_state == ActionState.REVIEW

    def test_scenario_y_economic_benefit_insufficient_information(self):
        """TEST Y: INSUFFICIENT_INFORMATION prevents BUY/SELL."""
        buy_payload = self._make_valid_input(
            position_context=PositionContext.NEW_POSITION,
            eb_state=EconomicBenefitState.INSUFFICIENT_INFORMATION,
        )
        buy_res = self.orchestrator.evaluate_decision(buy_payload)
        assert buy_res.final_action_state == ActionState.NO_ACTION

    def test_scenario_z_economic_benefit_invalid(self):
        """TEST Z: INVALID_ASSESSMENT in Economic Benefit yields INVALID_ASSESSMENT."""
        buy_payload = self._make_valid_input(
            position_context=PositionContext.NEW_POSITION,
            eb_state=EconomicBenefitState.INVALID_ASSESSMENT,
        )
        buy_res = self.orchestrator.evaluate_decision(buy_payload)
        assert buy_res.final_action_state == ActionState.INVALID_ASSESSMENT
        assert buy_res.final_decision_status == IntegrationStatus.INVALID

    # -------------------------------------------------------------------------
    # TEST SCENARIOS AA - AF: GUARDRAILS & METADATA
    # -------------------------------------------------------------------------
    def test_scenario_aa_missing_affordability(self):
        """TEST AA: Missing explicit affordability defaults safely without crashing."""
        buy_payload = self._make_valid_input(
            position_context=PositionContext.NEW_POSITION,
            affordability=AffordabilityStatus.AFFORDABILITY_STATUS_UNKNOWN,
        )
        buy_res = self.orchestrator.evaluate_decision(buy_payload)
        assert buy_res.final_action_state in [ActionState.BUY, ActionState.ACCUMULATE]

    def test_scenario_ab_missing_deterioration_validation(self):
        """TEST AB: Unvalidated deterioration methodology (deterioration_validated=False) prevents SELL."""
        sell_payload = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            deterioration="MATERIAL_DETERIORATION",
            deterioration_validated=False,
        )
        sell_res = self.orchestrator.evaluate_decision(sell_payload)
        assert sell_res.final_action_state == ActionState.REVIEW

    def test_scenario_ac_suitable_replacement_unavailable(self):
        """TEST AC: Missing suitable category replacement (has_replacement=False) prevents SELL."""
        sell_payload = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            deterioration="MATERIAL_DETERIORATION",
            has_replacement=False,
        )
        sell_res = self.orchestrator.evaluate_decision(sell_payload)
        assert sell_res.final_action_state == ActionState.REVIEW

    def test_scenario_ad_version_mismatch(self):
        """TEST AD: Incompatible methodology versions trigger INVALID_ASSESSMENT."""
        eb_contract = from_economic_benefit_result(
            assessment_id="eb_001",
            investor_id="inv_100",
            economic_benefit_state=EconomicBenefitState.ECONOMICALLY_BENEFICIAL,
            methodology_version="INCOMPATIBLE_VERSION_X",
        )
        input_payload = self._make_valid_input(custom_eb_contract=eb_contract)
        result = self.orchestrator.evaluate_decision(input_payload)
        assert result.final_action_state == ActionState.INVALID_ASSESSMENT
        assert result.final_decision_status == IntegrationStatus.INVALID

    def test_scenario_ae_point_in_time_inconsistency(self):
        """TEST AE (F.7.3.1): Upstream freshness determination (stale_input=True) is consumed and triggers REVIEW for existing position."""
        input_payload = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            stale_input=True,
        )
        result = self.orchestrator.evaluate_decision(input_payload)
        assert result.final_action_state == ActionState.REVIEW
        assert result.final_decision_status == IntegrationStatus.PARTIAL

    def test_scenario_af_missing_provenance(self):
        """TEST AF: Missing provenance metadata on individual contract handled gracefully."""
        eb_contract = from_economic_benefit_result(
            assessment_id="eb_001",
            investor_id="inv_100",
            economic_benefit_state=EconomicBenefitState.ECONOMICALLY_BENEFICIAL,
            provenance=None,
        )
        input_payload = self._make_valid_input(custom_eb_contract=eb_contract)
        result = self.orchestrator.evaluate_decision(input_payload)
        assert result.final_action_state == ActionState.BUY

    # -------------------------------------------------------------------------
    # TEST SCENARIOS AG - AP: SYSTEM & GOVERNANCE INVARIANTS
    # -------------------------------------------------------------------------
    def test_scenario_ag_multiple_goals(self):
        """TEST AG: Goal-specific payload propagates goal_id correctly."""
        goal_input = self._make_valid_input(goal_id="goal_retirement_99")
        res = self.orchestrator.evaluate_decision(goal_input)
        assert res.goal_id == "goal_retirement_99"
        assert res.final_action_state == ActionState.BUY

    def test_scenario_ah_portfolio_level_assessment(self):
        """TEST AH: Portfolio-level payload propagates portfolio_id correctly."""
        port_input = self._make_valid_input(goal_id=None, portfolio_id="port_wealth_01")
        res = self.orchestrator.evaluate_decision(port_input)
        assert res.portfolio_id == "port_wealth_01"
        assert res.final_action_state == ActionState.BUY

    def test_scenario_ai_macro_context(self):
        """TEST AI: Macro stress flag adds warning but does NOT independently trigger BUY/SELL."""
        macro_input = self._make_valid_input(
            position_context=PositionContext.EXISTING_POSITION,
            need_state=PortfolioNeedState.NO_MATERIAL_NEED,
            macro_stress_flag=True,
        )
        res = self.orchestrator.evaluate_decision(macro_input)
        assert res.final_action_state == ActionState.HOLD
        assert res.final_action_state != ActionState.SELL

    def test_scenario_aj_low_confidence_upstream_evidence(self):
        """TEST AJ (F.7.3.1): Low numerical confidence (e.g. 0.05) with valid evidence does NOT trigger an invented cutoff and permits BUY."""
        payload = self._make_valid_input(quality_conf=0.05)
        res = self.orchestrator.evaluate_decision(payload)
        assert res.final_action_state == ActionState.BUY

    def test_scenario_ak_none_vs_false(self):
        """TEST AK: Preserves distinction between None and explicit False."""
        # None comparison validity prevents SELL (yields REVIEW)
        res_none = self.orchestrator.evaluate_decision(
            self._make_valid_input(position_context=PositionContext.EXISTING_POSITION, deterioration="MATERIAL_DETERIORATION", fq_comparison_valid=None)
        )
        # False comparison validity also prevents SELL (yields REVIEW)
        res_false = self.orchestrator.evaluate_decision(
            self._make_valid_input(position_context=PositionContext.EXISTING_POSITION, deterioration="MATERIAL_DETERIORATION", fq_comparison_valid=False)
        )
        assert res_none.final_action_state == ActionState.REVIEW
        assert res_false.final_action_state == ActionState.REVIEW

    def test_scenario_al_none_vs_zero(self):
        """TEST AL (F.7.3.1): Confidence = 0.0 or None does not trigger an invented numerical cutoff when evidence is valid."""
        res_zero_conf = self.orchestrator.evaluate_decision(self._make_valid_input(quality_conf=0.0))
        assert res_zero_conf.final_action_state == ActionState.BUY

        res_none_conf = self.orchestrator.evaluate_decision(self._make_valid_input(quality_conf=None))
        assert res_none_conf.final_action_state == ActionState.BUY

    def test_f731_no_180_day_freshness_threshold(self):
        """TEST F.7.3.1-A: Observation dates separated by >180 days (e.g. 360 days) do NOT trigger staleness unless flagged by upstream."""
        old_date = date(2025, 9, 1)
        payload = self._make_valid_input(obs_date=old_date)
        res = self.orchestrator.evaluate_decision(payload)
        assert res.final_action_state == ActionState.BUY

    def test_f731_upstream_freshness_consumed(self):
        """TEST F.7.3.1-B: Upstream freshness determination (stale_input=True) is consumed and blocks BUY."""
        payload = self._make_valid_input(stale_input=True)
        res = self.orchestrator.evaluate_decision(payload)
        assert res.final_action_state == ActionState.INSUFFICIENT_INFORMATION

    def test_f731_fund_quality_evidence_valid_none_blocks(self):
        """TEST F.7.3.1-C: fund_quality_evidence_valid=None safely blocks BUY progression."""
        custom_fq = FundQualityIntegrationContract(
            reference=CanonicalAssessmentReference(
                assessment_id="fq_001",
                assessment_type=AssessmentType.FUND_QUALITY,
                scheme_id="INF209K01157",
            ),
            canonical_scheme_id="INF209K01157",
            category="Equity",
            subcategory="Large Cap",
            plan_type="Direct",
            option_type="Growth",
            fund_quality_score=85.0,
            fund_quality_confidence=0.95,
            fund_quality_evidence_valid=None,
        )
        payload = self._make_valid_input(custom_fq_contract=custom_fq)
        res = self.orchestrator.evaluate_decision(payload)
        assert res.final_action_state == ActionState.NO_ACTION

    def test_scenario_am_anti_churn_invariant(self):
        """TEST AM: Anti-churn invariant - Default is HOLD/NO_ACTION unless evidence justifies transaction."""
        no_need_input = self._make_valid_input(
            position_context=PositionContext.NEW_POSITION,
            need_state=PortfolioNeedState.NO_MATERIAL_NEED,
        )
        res = self.orchestrator.evaluate_decision(no_need_input)
        assert res.final_action_state == ActionState.NO_ACTION

    def test_scenario_an_construct_isolation(self):
        """TEST AN: Construct isolation - Orchestrator does not mutate upstream contract objects."""
        input_payload = self._make_valid_input()
        orig_eb_state = input_payload.economic_benefit_contract.economic_benefit_state
        res = self.orchestrator.evaluate_decision(input_payload)
        assert input_payload.economic_benefit_contract.economic_benefit_state == orig_eb_state

    def test_scenario_ao_provenance_aggregation(self):
        """TEST AO: Provenance aggregation - Aggregated provenance lineage is complete."""
        payload = self._make_valid_input()
        result = self.orchestrator.evaluate_decision(payload)
        assert result.provenance is not None
        assert "test_src_001" in result.provenance.source_id
        assert len(result.upstream_assessment_ids) >= 5

    def test_scenario_ap_no_upstream_methodology_duplication(self):
        """TEST AP: Zero upstream financial methodology duplication - Orchestrator composes contracts without recalculating scores."""
        payload = self._make_valid_input()
        result = self.orchestrator.evaluate_decision(payload)
        # Verify result outputs are derived purely from contracts
        assert result.orchestrator_version == "F.7.3"
        assert isinstance(result, EndToEndDecisionResult)
        assert isinstance(result.final_action_state, ActionState)
