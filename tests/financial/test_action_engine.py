"""
Action Decision Engine Financial & Architectural Test Suite (Phase F.6.2)

Tests decision orchestration, precedence hierarchy, low-turnover guardrails, adversarial scenarios,
and construct isolation invariants according to Phase F.6 test plan (TA-01 through TA-30).
"""

from datetime import datetime, timezone
import pytest

from action.models import (
    ActionState,
    PositionContext,
    InformationSufficiency,
    ReasonCode,
    ActionEvaluationContext,
    ActionAssessmentResult,
)
from action.engine import assess_action

from models.suitability_assessment import SuitabilityAssessmentResult, SuitabilityStatus
from portfolio.need_models import (
    PortfolioNeedAssessmentResult,
    PortfolioNeedState,
    CandidateFulfillmentStatus,
    AffordabilityStatus,
)


@pytest.fixture
def base_suitability_suitable():
    return SuitabilityAssessmentResult(
        assessment_id="suit_test_01",
        investor_id="inv_101",
        profile_version_used="1.0.0",
        canonical_scheme_id="scheme_equity_largecap",
        amfi_code="100001",
        scheme_name="Test Equity LargeCap Fund",
        category="Equity",
        subcategory="Large Cap",
        observation_date=datetime.now(timezone.utc).date(),
        suitability_status=SuitabilityStatus.SUITABLE,
        affordability_status="AFFORDABLE",
        fund_quality_score_consumed=85.0,
        suitability_confidence_score=1.0,
    )


@pytest.fixture
def base_suitability_unsuitable():
    return SuitabilityAssessmentResult(
        assessment_id="suit_test_unsuitable",
        investor_id="inv_101",
        profile_version_used="1.0.0",
        canonical_scheme_id="scheme_equity_largecap",
        amfi_code="100001",
        scheme_name="Test Equity LargeCap Fund",
        category="Equity",
        subcategory="Large Cap",
        observation_date=datetime.now(timezone.utc).date(),
        suitability_status=SuitabilityStatus.NOT_SUITABLE,
        rejection_reasons=["Risk alignment limit exceeded"],
        suitability_confidence_score=1.0,
    )


@pytest.fixture
def base_need_identified():
    return PortfolioNeedAssessmentResult(
        assessment_id="need_test_01",
        investor_id="inv_101",
        goal_id="goal_wealth",
        scheme_id="scheme_equity_largecap",
        primary_state=PortfolioNeedState.NEED_IDENTIFIED,
        candidate_fulfillment_status=CandidateFulfillmentStatus.CANDIDATE_CAN_FULFILL_NEED,
        affordability_status=AffordabilityStatus.AFFORDABLE,
        confidence_score=1.0,
    )


@pytest.fixture
def base_need_none():
    return PortfolioNeedAssessmentResult(
        assessment_id="need_test_none",
        investor_id="inv_101",
        goal_id="goal_wealth",
        scheme_id="scheme_equity_largecap",
        primary_state=PortfolioNeedState.NO_MATERIAL_NEED,
        candidate_fulfillment_status=CandidateFulfillmentStatus.CANDIDATE_CAN_FULFILL_NEED,
        affordability_status=AffordabilityStatus.AFFORDABLE,
        confidence_score=1.0,
    )


class TestActionEngineCoreScenarios:

    def test_ta01_buy_valid_purchase(self, base_suitability_suitable, base_need_identified):
        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_equity_largecap",
            position_context=PositionContext.NEW_POSITION,
            fund_quality_evidence_valid=True,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_identified,
            economic_benefit_state="ECONOMICALLY_BENEFICIAL",
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.BUY
        assert res.actionability_status == "ACTIONABLE"
        assert res.primary_reason_code == ReasonCode.NEED_IDENTIFIED.value

    def test_ta02_accumulate_affordability_constrained(self, base_suitability_suitable):
        need_res = PortfolioNeedAssessmentResult(
            assessment_id="need_test_02",
            investor_id="inv_101",
            goal_id="goal_wealth",
            scheme_id="scheme_equity_largecap",
            primary_state=PortfolioNeedState.NEED_IDENTIFIED,
            candidate_fulfillment_status=CandidateFulfillmentStatus.CANDIDATE_CAN_FULFILL_NEED,
            affordability_status=AffordabilityStatus.AFFORDABILITY_CONSTRAINED,
            confidence_score=1.0,
        )
        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_equity_largecap",
            position_context=PositionContext.NEW_POSITION,
            fund_quality_evidence_valid=True,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=need_res,
            economic_benefit_state="ECONOMICALLY_BENEFICIAL",
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.ACCUMULATE
        assert res.actionability_status == "CONSTRAINED"
        assert res.primary_reason_code == ReasonCode.AFFORDABILITY_CONSTRAINED.value

    def test_ta03_hold_default_owned_fund(self, base_suitability_suitable, base_need_none):
        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_equity_largecap",
            position_context=PositionContext.EXISTING_POSITION,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_none,
            economic_benefit_state="NO_EVALUABLE_CHANGE",
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.HOLD
        assert res.primary_reason_code == ReasonCode.HOLD_DEFAULT.value

    def test_ta04_monitor_mild_deterioration(self, base_suitability_suitable, base_need_none):
        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_equity_largecap",
            position_context=PositionContext.EXISTING_POSITION,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_none,
            deterioration_signal="MILD_DETERIORATION",
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.MONITOR
        assert res.primary_reason_code == ReasonCode.MATERIAL_REVIEW_SIGNAL.value

    def test_ta05_review_material_deterioration_no_replacement(self, base_suitability_suitable, base_need_none):
        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_equity_largecap",
            position_context=PositionContext.EXISTING_POSITION,
            fund_quality_evidence_valid=True,
            deterioration_validated=True,
            fund_quality_comparison_valid=True,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_none,
            deterioration_signal="MATERIAL_DETERIORATION",
            has_suitable_replacement=False,
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.REVIEW
        assert res.primary_reason_code == ReasonCode.NO_SUITABLE_REPLACEMENT.value

    def test_ta06_sell_validated_switch(self, base_suitability_suitable, base_need_none):
        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_equity_largecap",
            position_context=PositionContext.EXISTING_POSITION,
            fund_quality_evidence_valid=True,
            deterioration_validated=True,
            fund_quality_comparison_valid=True,
            transaction_costs_known=True,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_none,
            deterioration_signal="MATERIAL_DETERIORATION",
            has_suitable_replacement=True,
            tax_liability_known=True,
            exit_load_known=True,
            economic_benefit_state="ECONOMICALLY_BENEFICIAL",
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.SELL
        assert res.primary_reason_code == ReasonCode.MATERIAL_REVIEW_SIGNAL.value

    def test_ta07_excellent_fund_no_need_no_buy(self, base_suitability_suitable, base_need_none):
        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_equity_largecap",
            position_context=PositionContext.NEW_POSITION,
            fund_quality_score=95.0,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_none,
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.NO_ACTION
        assert res.primary_reason_code == ReasonCode.NO_PORTFOLIO_NEED.value

    def test_ta08_excellent_fund_with_need_buy(self, base_suitability_suitable, base_need_identified):
        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_equity_largecap",
            position_context=PositionContext.NEW_POSITION,
            fund_quality_score=95.0,
            fund_quality_evidence_valid=True,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_identified,
            economic_benefit_state="ECONOMICALLY_BENEFICIAL",
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.BUY

    def test_ta09_need_and_unsuitable_fund(self, base_suitability_unsuitable, base_need_identified):
        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_equity_largecap",
            position_context=PositionContext.NEW_POSITION,
            fund_quality_score=90.0,
            suitability_result=base_suitability_unsuitable,
            portfolio_need_result=base_need_identified,
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.NO_ACTION
        assert res.primary_reason_code == ReasonCode.CANDIDATE_NOT_SUITABLE.value

    def test_ta10_need_and_constrained_affordability(self, base_suitability_suitable, base_need_identified):
        need_res = PortfolioNeedAssessmentResult(
            assessment_id="need_test_const",
            investor_id="inv_101",
            goal_id="goal_wealth",
            scheme_id="scheme_equity_largecap",
            primary_state=PortfolioNeedState.NEED_IDENTIFIED,
            candidate_fulfillment_status=CandidateFulfillmentStatus.CANDIDATE_CAN_FULFILL_NEED,
            affordability_status=AffordabilityStatus.AFFORDABILITY_CONSTRAINED,
        )
        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_equity_largecap",
            position_context=PositionContext.NEW_POSITION,
            fund_quality_evidence_valid=True,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=need_res,
            economic_benefit_state="ECONOMICALLY_BENEFICIAL",
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.ACCUMULATE
        assert res.primary_reason_code == ReasonCode.AFFORDABILITY_CONSTRAINED.value

    def test_ta12_unknown_expected_improvement(self, base_suitability_suitable, base_need_identified):
        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_equity_largecap",
            position_context=PositionContext.NEW_POSITION,
            fund_quality_evidence_valid=True,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_identified,
            economic_benefit_state="BENEFIT_UNCERTAIN",
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.NO_ACTION
        assert res.primary_reason_code == ReasonCode.ECONOMIC_BENEFIT_UNKNOWN.value

    def test_ta13_missing_tax_info_prevents_sell(self, base_suitability_suitable, base_need_none):
        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_equity_largecap",
            position_context=PositionContext.EXISTING_POSITION,
            fund_quality_evidence_valid=True,
            deterioration_validated=True,
            fund_quality_comparison_valid=True,
            transaction_costs_known=True,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_none,
            deterioration_signal="MATERIAL_DETERIORATION",
            has_suitable_replacement=True,
            tax_liability_known=False,
            exit_load_known=True,
            economic_benefit_state="ECONOMICALLY_BENEFICIAL",
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.REVIEW
        assert res.primary_reason_code == ReasonCode.TAX_COST_INFORMATION_MISSING.value

    def test_ta14_missing_exit_load_info_prevents_sell(self, base_suitability_suitable, base_need_none):
        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_equity_largecap",
            position_context=PositionContext.EXISTING_POSITION,
            fund_quality_evidence_valid=True,
            deterioration_validated=True,
            fund_quality_comparison_valid=True,
            transaction_costs_known=True,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_none,
            deterioration_signal="MATERIAL_DETERIORATION",
            has_suitable_replacement=True,
            tax_liability_known=True,
            exit_load_known=False,
            economic_benefit_state="ECONOMICALLY_BENEFICIAL",
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.REVIEW
        assert res.primary_reason_code == ReasonCode.EXIT_LOAD_INFORMATION_MISSING.value

    def test_ta15_high_switching_cost_prevents_sell(self, base_suitability_suitable, base_need_none):
        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_equity_largecap",
            position_context=PositionContext.EXISTING_POSITION,
            fund_quality_evidence_valid=True,
            deterioration_validated=True,
            fund_quality_comparison_valid=True,
            tax_liability_known=True,
            exit_load_known=True,
            transaction_costs_known=True,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_none,
            deterioration_signal="MATERIAL_DETERIORATION",
            has_suitable_replacement=True,
            economic_benefit_state="ECONOMICALLY_NOT_BENEFICIAL",
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.REVIEW
        assert res.primary_reason_code == ReasonCode.SWITCH_NOT_JUSTIFIED.value

    def test_ta16_lower_vs_higher_incumbent(self, base_suitability_suitable, base_need_none):
        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_equity_largecap",
            position_context=PositionContext.EXISTING_POSITION,
            fund_quality_score=75.0,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_none,
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.HOLD
        assert res.primary_reason_code == ReasonCode.HOLD_DEFAULT.value

    def test_ta19_temporary_underperformance(self, base_suitability_suitable, base_need_none):
        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_equity_largecap",
            position_context=PositionContext.EXISTING_POSITION,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_none,
            deterioration_signal="TEMPORARY_UNDERPERFORMANCE",
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.HOLD
        assert res.primary_reason_code == ReasonCode.TEMPORARY_UNDERPERFORMANCE.value

    def test_ta22_invalid_upstream_assessment(self, base_suitability_suitable):
        invalid_need = PortfolioNeedAssessmentResult(
            assessment_id="need_inv",
            investor_id="inv_101",
            goal_id="goal_1",
            scheme_id="scheme_1",
            primary_state=PortfolioNeedState.INVALID_ASSESSMENT,
            candidate_fulfillment_status=CandidateFulfillmentStatus.CANDIDATE_FULFILLMENT_UNKNOWN,
            affordability_status=AffordabilityStatus.AFFORDABILITY_STATUS_UNKNOWN,
        )
        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_1",
            position_context=PositionContext.NEW_POSITION,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=invalid_need,
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.INVALID_ASSESSMENT
        assert res.primary_reason_code == ReasonCode.INVALID_INPUT.value

    def test_ta23_insufficient_upstream_assessment(self, base_suitability_suitable):
        insuff_need = PortfolioNeedAssessmentResult(
            assessment_id="need_insuff",
            investor_id="inv_101",
            goal_id="goal_1",
            scheme_id="scheme_1",
            primary_state=PortfolioNeedState.INSUFFICIENT_INFORMATION,
            candidate_fulfillment_status=CandidateFulfillmentStatus.CANDIDATE_FULFILLMENT_UNKNOWN,
            affordability_status=AffordabilityStatus.AFFORDABILITY_STATUS_UNKNOWN,
        )
        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_1",
            position_context=PositionContext.NEW_POSITION,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=insuff_need,
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.INSUFFICIENT_INFORMATION
        assert res.primary_reason_code == ReasonCode.INSUFFICIENT_INPUT.value

    def test_ta24_stale_upstream_assessment(self, base_suitability_suitable, base_need_identified):
        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_equity_largecap",
            position_context=PositionContext.EXISTING_POSITION,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_identified,
            is_stale_input=True,
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.REVIEW
        assert res.primary_reason_code == ReasonCode.STALE_INPUT.value

    def test_ta26_excessive_concentration_context(self, base_suitability_suitable):
        need_conc = PortfolioNeedAssessmentResult(
            assessment_id="need_conc",
            investor_id="inv_101",
            goal_id="goal_1",
            scheme_id="scheme_1",
            primary_state=PortfolioNeedState.NEED_IDENTIFIED,
            candidate_fulfillment_status=CandidateFulfillmentStatus.CANDIDATE_CAN_FULFILL_NEED,
            affordability_status=AffordabilityStatus.AFFORDABLE,
            contextual_flags=["CATEGORY_OVEREXPOSED"],
        )
        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_1",
            position_context=PositionContext.NEW_POSITION,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=need_conc,
            economic_benefit_state="ECONOMICALLY_BENEFICIAL",
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.ACCUMULATE
        assert res.primary_reason_code == ReasonCode.CATEGORY_CONCENTRATION_EXCEEDED.value

    def test_ta28_candidate_cannot_fulfill_need(self, base_suitability_suitable):
        need_incapable = PortfolioNeedAssessmentResult(
            assessment_id="need_incapable",
            investor_id="inv_101",
            goal_id="goal_1",
            scheme_id="scheme_1",
            primary_state=PortfolioNeedState.NEED_IDENTIFIED,
            candidate_fulfillment_status=CandidateFulfillmentStatus.CANDIDATE_CANNOT_FULFILL_NEED,
            affordability_status=AffordabilityStatus.AFFORDABLE,
        )
        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_1",
            position_context=PositionContext.NEW_POSITION,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=need_incapable,
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.NO_ACTION
        assert res.primary_reason_code == ReasonCode.CANDIDATE_CANNOT_FULFILL_NEED.value

    def test_ta29_macro_stress_context(self, base_suitability_suitable, base_need_none):
        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_equity_largecap",
            position_context=PositionContext.EXISTING_POSITION,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_none,
            macro_stress_flag=True,
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.HOLD


class TestAdversarialScenarios:

    def test_adv_a_quality_99_unsuitable_must_not_buy(self, base_suitability_unsuitable, base_need_identified):
        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_equity_largecap",
            position_context=PositionContext.NEW_POSITION,
            fund_quality_score=99.0,
            suitability_result=base_suitability_unsuitable,
            portfolio_need_result=base_need_identified,
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.NO_ACTION
        assert res.primary_reason_code == ReasonCode.CANDIDATE_NOT_SUITABLE.value

    def test_adv_b_candidate_rank_1_healthy_holding_must_not_sell(self, base_suitability_suitable, base_need_none):
        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_equity_largecap",
            position_context=PositionContext.EXISTING_POSITION,
            fund_quality_score=80.0,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_none,
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.HOLD
        assert res.primary_reason_code == ReasonCode.HOLD_DEFAULT.value

    def test_adv_c_need_none_quality_99_must_not_buy(self, base_suitability_suitable, base_need_none):
        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_equity_largecap",
            position_context=PositionContext.NEW_POSITION,
            fund_quality_score=99.0,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_none,
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.NO_ACTION

    def test_adv_d_benefit_uncertain_must_not_claim_economic_buy(self, base_suitability_suitable, base_need_identified):
        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_equity_largecap",
            position_context=PositionContext.NEW_POSITION,
            fund_quality_evidence_valid=True,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_identified,
            economic_benefit_state="BENEFIT_UNCERTAIN",
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.NO_ACTION
        assert res.primary_reason_code == ReasonCode.ECONOMIC_BENEFIT_UNKNOWN.value

    def test_adv_e_missing_tax_must_not_assume_zero(self, base_suitability_suitable, base_need_none):
        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_equity_largecap",
            position_context=PositionContext.EXISTING_POSITION,
            fund_quality_evidence_valid=True,
            deterioration_validated=True,
            fund_quality_comparison_valid=True,
            exit_load_known=True,
            transaction_costs_known=True,
            economic_benefit_state="ECONOMICALLY_BENEFICIAL",
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_none,
            deterioration_signal="MATERIAL_DETERIORATION",
            has_suitable_replacement=True,
            tax_liability_known=False,
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.REVIEW
        assert res.primary_reason_code == ReasonCode.TAX_COST_INFORMATION_MISSING.value

    def test_adv_j_incapable_candidate_must_not_buy(self, base_suitability_suitable):
        need_incapable = PortfolioNeedAssessmentResult(
            assessment_id="need_incap",
            investor_id="inv_101",
            goal_id="goal_1",
            scheme_id="scheme_1",
            primary_state=PortfolioNeedState.NEED_IDENTIFIED,
            candidate_fulfillment_status=CandidateFulfillmentStatus.CANDIDATE_CANNOT_FULFILL_NEED,
            affordability_status=AffordabilityStatus.AFFORDABLE,
        )
        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_1",
            position_context=PositionContext.NEW_POSITION,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=need_incapable,
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.NO_ACTION

    def test_adv_k_invalid_upstream_must_not_recommend(self, base_suitability_suitable):
        invalid_need = PortfolioNeedAssessmentResult(
            assessment_id="need_inv",
            investor_id="inv_101",
            goal_id="goal_1",
            scheme_id="scheme_1",
            primary_state=PortfolioNeedState.INVALID_ASSESSMENT,
            candidate_fulfillment_status=CandidateFulfillmentStatus.CANDIDATE_FULFILLMENT_UNKNOWN,
            affordability_status=AffordabilityStatus.AFFORDABILITY_STATUS_UNKNOWN,
        )
        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_1",
            position_context=PositionContext.NEW_POSITION,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=invalid_need,
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.INVALID_ASSESSMENT


class TestConstructIsolation:

    def test_construct_isolation_no_upstream_mutation(self, base_suitability_suitable, base_need_identified):
        suit_status_before = base_suitability_suitable.suitability_status
        need_state_before = base_need_identified.primary_state

        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_equity_largecap",
            position_context=PositionContext.NEW_POSITION,
            fund_quality_evidence_valid=True,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_identified,
            economic_benefit_state="ECONOMICALLY_BENEFICIAL",
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.BUY

        # Verify upstream dataclasses were completely untouched
        assert base_suitability_suitable.suitability_status == suit_status_before
        assert base_need_identified.primary_state == need_state_before


class TestF622PreQAForensics:

    def test_f622_test1_unvalidated_deterioration_cannot_produce_sell(self, base_suitability_suitable, base_need_none):
        """Verify unvalidated deterioration methodology prohibits SELL, falling back to REVIEW."""
        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_equity_largecap",
            position_context=PositionContext.EXISTING_POSITION,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_none,
            deterioration_signal="MATERIAL_DETERIORATION",
            deterioration_validated=False,  # Unvalidated methodology
            has_suitable_replacement=True,
            tax_liability_known=True,
            exit_load_known=True,
            economic_benefit_state="ECONOMICALLY_BENEFICIAL",
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.REVIEW
        assert res.primary_reason_code == ReasonCode.UNVALIDATED_DETERIORATION.value
        assert "Unvalidated deterioration methodology prevents SELL" in res.warnings[0]

    def test_f622_test2_confidence_is_actionability_indicator_not_probability(self, base_suitability_suitable, base_need_none):
        """Verify action_confidence reflects input completeness/actionability, not financial probability."""
        # Fully sufficient context -> confidence 1.0
        ctx_full = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_equity_largecap",
            position_context=PositionContext.EXISTING_POSITION,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_none,
            fund_quality_confidence=0.6,  # Upstream low confidence
        )
        res_full = assess_action(ctx_full)
        assert res_full.action_confidence == 1.0  # Structural readiness is complete
        assert res_full.action_confidence != 0.6  # Does NOT override or mirror Fund Quality confidence as probability

        # Constrained/Partial context -> confidence 0.5
        ctx_partial = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_equity_largecap",
            position_context=PositionContext.EXISTING_POSITION,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_none,
            deterioration_signal="MATERIAL_DETERIORATION",
            tax_liability_known=False,
        )
        res_partial = assess_action(ctx_partial)
        assert res_partial.action_confidence == 0.5  # Input completeness is partial
        assert res_partial.action_state == ActionState.REVIEW

    def test_f622_test3_sell_requires_all_governed_prerequisites(self, base_suitability_suitable, base_need_none):
        """Verify SELL requires ALL governed prerequisites simultaneously and fails safely if any is missing."""
        # 1. Complete prerequisites -> SELL
        ctx_valid = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_equity_largecap",
            position_context=PositionContext.EXISTING_POSITION,
            fund_quality_evidence_valid=True,
            fund_quality_comparison_valid=True,
            transaction_costs_known=True,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_none,
            deterioration_signal="MATERIAL_DETERIORATION",
            deterioration_validated=True,
            has_suitable_replacement=True,
            tax_liability_known=True,
            exit_load_known=True,
            economic_benefit_state="ECONOMICALLY_BENEFICIAL",
        )
        assert assess_action(ctx_valid).action_state == ActionState.SELL

        # 2. Missing replacement -> REVIEW
        ctx_no_rep = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_equity_largecap",
            position_context=PositionContext.EXISTING_POSITION,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_none,
            deterioration_signal="MATERIAL_DETERIORATION",
            has_suitable_replacement=False,
            tax_liability_known=True,
            exit_load_known=True,
            economic_benefit_state="ECONOMICALLY_BENEFICIAL",
        )
        assert assess_action(ctx_no_rep).action_state == ActionState.REVIEW

        # 3. Missing tax info -> REVIEW
        ctx_no_tax = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_equity_largecap",
            position_context=PositionContext.EXISTING_POSITION,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_none,
            deterioration_signal="MATERIAL_DETERIORATION",
            has_suitable_replacement=True,
            tax_liability_known=False,
            exit_load_known=True,
            economic_benefit_state="ECONOMICALLY_BENEFICIAL",
        )
        assert assess_action(ctx_no_tax).action_state == ActionState.REVIEW

        # 4. Missing exit load -> REVIEW
        ctx_no_load = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_equity_largecap",
            position_context=PositionContext.EXISTING_POSITION,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_none,
            deterioration_signal="MATERIAL_DETERIORATION",
            has_suitable_replacement=True,
            tax_liability_known=True,
            exit_load_known=False,
            economic_benefit_state="ECONOMICALLY_BENEFICIAL",
        )
        assert assess_action(ctx_no_load).action_state == ActionState.REVIEW

        # 5. Benefit uncertain -> REVIEW
        ctx_benefit_unc = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_equity_largecap",
            position_context=PositionContext.EXISTING_POSITION,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_none,
            deterioration_signal="MATERIAL_DETERIORATION",
            has_suitable_replacement=True,
            tax_liability_known=True,
            exit_load_known=True,
            economic_benefit_state="BENEFIT_UNCERTAIN",
        )
        assert assess_action(ctx_benefit_unc).action_state == ActionState.REVIEW


class TestF63IndependentQAFindingFixes:

    def test_qa_defect1_invalid_upstream_suitability_must_return_invalid_assessment(self, base_need_identified):
        """Verify Tier 1 catches SuitabilityStatus.INVALID_ASSESSMENT and halts execution."""
        # Construct an uninitialized/invalid suitability result with empty assessment_id
        invalid_suitability = object.__new__(SuitabilityAssessmentResult)
        object.__setattr__(invalid_suitability, "assessment_id", "")
        object.__setattr__(invalid_suitability, "investor_id", "inv_101")
        object.__setattr__(invalid_suitability, "suitability_status", SuitabilityStatus.INSUFFICIENT_INFORMATION)

        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_1",
            position_context=PositionContext.NEW_POSITION,
            suitability_result=invalid_suitability,
            portfolio_need_result=base_need_identified,
            economic_benefit_state="ECONOMICALLY_BENEFICIAL",
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.INVALID_ASSESSMENT
        assert res.primary_reason_code == ReasonCode.INVALID_INPUT.value

    def test_qa_defect2_missing_or_unknown_economic_benefit_must_not_buy_or_sell(self, base_suitability_suitable, base_need_identified, base_need_none):
        """Verify None or UNKNOWN economic_benefit_state cannot bypass guardrails to produce BUY or SELL."""
        # Stage 6 check: None economic benefit -> must NOT produce BUY
        ctx_buy_none = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_1",
            position_context=PositionContext.NEW_POSITION,
            fund_quality_evidence_valid=True,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_identified,
            economic_benefit_state=None,  # Unset / unknown
        )
        res_buy = assess_action(ctx_buy_none)
        assert res_buy.action_state == ActionState.NO_ACTION  # Guardrail engaged
        assert res_buy.primary_reason_code == ReasonCode.ECONOMIC_BENEFIT_UNKNOWN.value

        # Stage 4 check: None economic benefit -> must NOT produce SELL
        ctx_sell_none = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_1",
            position_context=PositionContext.EXISTING_POSITION,
            fund_quality_evidence_valid=True,
            fund_quality_comparison_valid=True,
            transaction_costs_known=True,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_none,
            deterioration_signal="MATERIAL_DETERIORATION",
            deterioration_validated=True,
            has_suitable_replacement=True,
            tax_liability_known=True,
            exit_load_known=True,
            economic_benefit_state=None,  # Unset / unknown
        )
        res_sell = assess_action(ctx_sell_none)
        assert res_sell.action_state == ActionState.REVIEW  # Guardrail engaged
        assert res_sell.primary_reason_code == ReasonCode.ECONOMIC_BENEFIT_UNKNOWN.value

    def test_qa_defect3_missing_position_context_must_return_invalid_assessment(self, base_suitability_suitable, base_need_none):
        """Verify missing position_context in Tier 1 returns ActionState.INVALID_ASSESSMENT."""
        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_1",
            position_context=None,  # Missing mandatory position context
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_none,
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.INVALID_ASSESSMENT
        assert res.primary_reason_code == ReasonCode.INVALID_INPUT.value


class TestF631QACorrection:

    def test_f631_test_a_canonical_economically_beneficial_allows_buy_and_sell(self, base_suitability_suitable, base_need_identified, base_need_none):
        """Verify canonical ECONOMICALLY_BENEFICIAL state satisfies economic benefit prerequisite for BUY and SELL."""
        # BUY path
        ctx_buy = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_1",
            position_context=PositionContext.NEW_POSITION,
            fund_quality_evidence_valid=True,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_identified,
            economic_benefit_state="ECONOMICALLY_BENEFICIAL",
        )
        assert assess_action(ctx_buy).action_state == ActionState.BUY

        # SELL path
        ctx_sell = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_1",
            position_context=PositionContext.EXISTING_POSITION,
            fund_quality_evidence_valid=True,
            transaction_costs_known=True,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_none,
            deterioration_signal="MATERIAL_DETERIORATION",
            deterioration_validated=True,
            has_suitable_replacement=True,
            fund_quality_comparison_valid=True,
            tax_liability_known=True,
            exit_load_known=True,
            economic_benefit_state="ECONOMICALLY_BENEFICIAL",
        )
        assert assess_action(ctx_sell).action_state == ActionState.SELL

    def test_f631_test_b_high_or_moderate_benefit_cannot_be_relied_upon(self, base_suitability_suitable, base_need_identified):
        """Verify non-canonical states like HIGH_BENEFIT or MODERATE_BENEFIT cannot produce BUY."""
        ctx_high = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_1",
            position_context=PositionContext.NEW_POSITION,
            fund_quality_evidence_valid=True,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_identified,
            economic_benefit_state="HIGH_BENEFIT",  # Non-canonical state
        )
        res = assess_action(ctx_high)
        assert res.action_state == ActionState.NO_ACTION  # Prohibited
        assert res.primary_reason_code == ReasonCode.ECONOMIC_BENEFIT_UNKNOWN.value

    def test_f631_test_c_benefit_uncertain_cannot_produce_buy_or_sell(self, base_suitability_suitable, base_need_identified, base_need_none):
        """Verify BENEFIT_UNCERTAIN cannot produce BUY or SELL."""
        ctx_buy = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_1",
            position_context=PositionContext.NEW_POSITION,
            fund_quality_evidence_valid=True,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_identified,
            economic_benefit_state="BENEFIT_UNCERTAIN",
        )
        assert assess_action(ctx_buy).action_state == ActionState.NO_ACTION

        ctx_sell = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_1",
            position_context=PositionContext.EXISTING_POSITION,
            fund_quality_evidence_valid=True,
            fund_quality_comparison_valid=True,
            transaction_costs_known=True,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_none,
            deterioration_signal="MATERIAL_DETERIORATION",
            deterioration_validated=True,
            has_suitable_replacement=True,
            tax_liability_known=True,
            exit_load_known=True,
            economic_benefit_state="BENEFIT_UNCERTAIN",
        )
        assert assess_action(ctx_sell).action_state == ActionState.REVIEW

    def test_f631_test_d_no_evaluable_change_cannot_produce_buy_or_sell(self, base_suitability_suitable, base_need_identified, base_need_none):
        """Verify NO_EVALUABLE_CHANGE cannot produce BUY or SELL."""
        ctx_buy = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_1",
            position_context=PositionContext.NEW_POSITION,
            fund_quality_evidence_valid=True,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_identified,
            economic_benefit_state="NO_EVALUABLE_CHANGE",
        )
        assert assess_action(ctx_buy).action_state == ActionState.NO_ACTION

        ctx_sell = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_1",
            position_context=PositionContext.EXISTING_POSITION,
            fund_quality_evidence_valid=True,
            fund_quality_comparison_valid=True,
            transaction_costs_known=True,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_none,
            deterioration_signal="MATERIAL_DETERIORATION",
            deterioration_validated=True,
            has_suitable_replacement=True,
            tax_liability_known=True,
            exit_load_known=True,
            economic_benefit_state="NO_EVALUABLE_CHANGE",
        )
        assert assess_action(ctx_sell).action_state == ActionState.REVIEW

    def test_f631_test_e_economically_not_beneficial_cannot_produce_buy_or_sell(self, base_suitability_suitable, base_need_identified, base_need_none):
        """Verify ECONOMICALLY_NOT_BENEFICIAL cannot produce BUY or SELL."""
        ctx_buy = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_1",
            position_context=PositionContext.NEW_POSITION,
            fund_quality_evidence_valid=True,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_identified,
            economic_benefit_state="ECONOMICALLY_NOT_BENEFICIAL",
        )
        assert assess_action(ctx_buy).action_state == ActionState.NO_ACTION

        ctx_sell = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_1",
            position_context=PositionContext.EXISTING_POSITION,
            fund_quality_evidence_valid=True,
            fund_quality_comparison_valid=True,
            transaction_costs_known=True,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_none,
            deterioration_signal="MATERIAL_DETERIORATION",
            deterioration_validated=True,
            has_suitable_replacement=True,
            tax_liability_known=True,
            exit_load_known=True,
            economic_benefit_state="ECONOMICALLY_NOT_BENEFICIAL",
        )
        res_sell = assess_action(ctx_sell)
        assert res_sell.action_state == ActionState.REVIEW
        assert res_sell.primary_reason_code == ReasonCode.SWITCH_NOT_JUSTIFIED.value

    def test_f631_test_f_non_comparable_fund_quality_scores_cannot_support_sell(self, base_suitability_suitable, base_need_none):
        """Verify fund_quality_comparison_valid=False prevents SELL, falling back to REVIEW."""
        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_1",
            position_context=PositionContext.EXISTING_POSITION,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_none,
            deterioration_signal="MATERIAL_DETERIORATION",
            deterioration_validated=True,
            has_suitable_replacement=True,
            fund_quality_comparison_valid=False,  # Scores non-comparable
            tax_liability_known=True,
            exit_load_known=True,
            economic_benefit_state="ECONOMICALLY_BENEFICIAL",
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.REVIEW
        assert res.primary_reason_code == ReasonCode.INSUFFICIENT_EVIDENCE.value
        assert "Fund Quality comparison is invalid or unknown" in res.warnings[0]

    def test_f631_test_g_unknown_fund_quality_comparability_cannot_support_sell(self, base_suitability_suitable, base_need_none):
        """Verify fund_quality_comparison_valid=None prevents SELL, falling back to REVIEW."""
        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_1",
            position_context=PositionContext.EXISTING_POSITION,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_none,
            deterioration_signal="MATERIAL_DETERIORATION",
            deterioration_validated=True,
            has_suitable_replacement=True,
            fund_quality_comparison_valid=None,  # Comparability unknown
            tax_liability_known=True,
            exit_load_known=True,
            economic_benefit_state="ECONOMICALLY_BENEFICIAL",
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.REVIEW
        assert res.primary_reason_code == ReasonCode.INSUFFICIENT_EVIDENCE.value

    def test_f631_test_h_valid_comparable_fund_quality_scores_support_sell(self, base_suitability_suitable, base_need_none):
        """Verify fund_quality_comparison_valid=True allows SELL when all other prerequisites are satisfied."""
        ctx = ActionEvaluationContext(
            investor_id="inv_101",
            scheme_id="scheme_1",
            position_context=PositionContext.EXISTING_POSITION,
            suitability_result=base_suitability_suitable,
            portfolio_need_result=base_need_none,
            deterioration_signal="MATERIAL_DETERIORATION",
            deterioration_validated=True,
            has_suitable_replacement=True,
            fund_quality_comparison_valid=True,  # Valid comparable scores
            tax_liability_known=True,
            exit_load_known=True,
            economic_benefit_state="ECONOMICALLY_BENEFICIAL",
        )
        res = assess_action(ctx)
        assert res.action_state == ActionState.SELL
        assert "candidate Fund Quality comparison is valid" in res.explanation



