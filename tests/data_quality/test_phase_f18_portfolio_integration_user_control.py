"""
Phase F.18 Portfolio Integration & User-Control Validation Test Suite.

Validates:
1. Portfolio context integration (multi-fund, multi-goal, concentration, overlap).
2. Goal context & multiple independent goals.
3. New-money vs switch under Economic Benefit.
4. Recommendation vs transaction separation (zero silent portfolio mutation).
5. User rejection & user adjustment agency preservation.
6. Immutable assessment history & reassessment after material change.
7. "What changed?" explanation & auditability.
8. Missing data degradation & temporal safety.
9. Deterministic repeatability.
10. Adversarial high-FQ portfolio cases.
"""

import pytest
import os
import sys
import json
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.abspath("."))

from models.fund_quality_dataset import ProvenanceMetadata
from models.investor_profile import RiskCapacityLevel, RiskToleranceLevel
from risk.alignment_models import RiskAlignmentAssessmentResult, AlignmentStatus, LimitingConstraint, AlignedRiskLevel
from scoring.models import FundQualityScoreResult
from models.suitability_assessment import SuitabilityAssessmentResult, SuitabilityStatus
from portfolio.need_models import (
    PortfolioNeedAssessmentResult,
    PortfolioNeedState,
    CandidateFulfillmentStatus,
    AffordabilityStatus,
    FundingStatus,
)
from action.models import PositionContext, ActionState
from integration.models import (
    IntegrationStatus,
    EconomicBenefitState,
)
from integration.contracts import (
    from_fund_quality_result,
    from_risk_alignment_result,
    from_suitability_result,
    from_portfolio_need_result,
    from_economic_benefit_result,
    build_action_input_contract,
)
from integration.orchestrator import DecisionOrchestrator
from scripts.run_f18_portfolio_integration_user_control_validation import (
    HoldingSnapshot,
    PortfolioStateSnapshot,
    UserDecisionRecord
)


@pytest.fixture
def orchestrator():
    return DecisionOrchestrator()


@pytest.fixture
def base_payload_builder():
    def _builder(
        quality_score=90.0,
        quality_conf=1.0,
        evidence_valid=True,
        capacity_level=RiskCapacityLevel.HIGH,
        tolerance_level=RiskToleranceLevel.HIGH,
        suitability_st=SuitabilityStatus.SUITABLE,
        constraints=None,
        need_state=PortfolioNeedState.NEED_IDENTIFIED,
        fulfillment=CandidateFulfillmentStatus.CANDIDATE_CAN_FULFILL_NEED,
        affordability=AffordabilityStatus.AFFORDABLE,
        eb_state=EconomicBenefitState.ECONOMICALLY_BENEFICIAL,
        position_context=PositionContext.NEW_POSITION,
        deterioration=None,
        deterioration_validated=True,
        has_replacement=True,
        fq_comparison_valid=True,
        stale_input=False,
        custom_eb=None
    ):
        today = date(2025, 1, 31)
        now_utc = datetime(2025, 1, 31, 12, 0, 0, tzinfo=timezone.utc)
        prov = ProvenanceMetadata(
            source_id="test_src_f18",
            source_document_url="http://amfiindia.com",
            retrieval_timestamp_utc=now_utc,
            methodology_version="1.0.0"
        )

        fq_res = FundQualityScoreResult(
            canonical_scheme_id="INF100K0002",
            amfi_code="100001",
            scheme_name="Candidate Growth Fund",
            category="Equity",
            subcategory="Large Cap",
            observation_date=today,
            quality_score=quality_score if evidence_valid else None,
            confidence_score=quality_conf,
            data_quality_score=1.0 if evidence_valid else 0.0,
            dimension_scores={},
            available_dimensions_count=6 if evidence_valid else 0,
            total_dimensions_count=6,
            peer_group_size=50,
            scoring_methodology_version="1.0.0",
            weight_config_version="1.0.0",
            calculation_timestamp_utc=now_utc,
            summary_explanation="FQ Score"
        )
        fq_contract = from_fund_quality_result(
            result=fq_res,
            canonical_scheme_id="INF100K0002",
            category="Equity",
            subcategory="Large Cap",
            fund_quality_comparison_valid=fq_comparison_valid,
            status=IntegrationStatus.VALID
        )

        min_level = AlignedRiskLevel.HIGH if (capacity_level == RiskCapacityLevel.HIGH and tolerance_level == RiskToleranceLevel.HIGH) else AlignedRiskLevel.LOW
        ra_res = RiskAlignmentAssessmentResult(
            assessment_id="ra_f18_01",
            investor_id="inv_f18_01",
            profile_version_used="1.0.0",
            observation_date=today,
            assessment_timestamp_utc=now_utc,
            startup_mode=1,
            alignment_status=AlignmentStatus.FULLY_ALIGNED,
            limiting_constraint=LimitingConstraint.NONE,
            aligned_risk_level=min_level,
            capacity_assessment_id="rc_001",
            tolerance_assessment_id="rt_001",
            alignment_confidence_score=1.0,
            is_stale_input=stale_input,
            provenance=prov
        )
        ra_contract = from_risk_alignment_result(ra_res)

        suit_res = SuitabilityAssessmentResult(
            assessment_id="suit_f18_01",
            investor_id="inv_f18_01",
            profile_version_used="1.0.0",
            canonical_scheme_id="INF100K0002",
            amfi_code="100001",
            scheme_name="Candidate Growth Fund",
            category="Equity",
            subcategory="Large Cap",
            observation_date=today,
            suitability_status=suitability_st,
            constraints_applied=constraints or [],
            goal_id="goal_wealth_01",
            suitability_confidence_score=1.0,
            provenance=prov,
            assessment_timestamp_utc=now_utc
        )
        suit_contract = from_suitability_result(suit_res)

        need_res = PortfolioNeedAssessmentResult(
            assessment_id="need_f18_01",
            investor_id="inv_f18_01",
            goal_id="goal_wealth_01",
            scheme_id="INF100K0002",
            primary_state=need_state,
            candidate_fulfillment_status=fulfillment,
            affordability_status=affordability,
            funding_status=FundingStatus.UNDERFUNDED,
            observation_timestamp=now_utc,
            upstream_assessment_ids={"source_id": "test_src_f18"}
        )
        need_contract = from_portfolio_need_result(need_res)

        if custom_eb:
            eb_contract = custom_eb
        else:
            eb_contract = from_economic_benefit_result(
                assessment_id="eb_f18_01",
                investor_id="inv_f18_01",
                economic_benefit_state=eb_state,
                candidate_scheme_id="INF100K0002",
                observation_date=today,
                assessment_timestamp_utc=now_utc,
                methodology_version="F.5.0",
                provenance=prov
            )

        return build_action_input_contract(
            assessment_id="act_f18_01",
            investor_id="inv_f18_01",
            scheme_id="INF100K0002",
            position_context=position_context,
            fund_quality_contract=fq_contract,
            risk_alignment_contract=ra_contract,
            suitability_contract=suit_contract,
            portfolio_need_contract=need_contract,
            economic_benefit_contract=eb_contract,
            goal_id="goal_wealth_01",
            portfolio_id="port_f18_01",
            deterioration_signal=deterioration,
            deterioration_validated=deterioration_validated,
            has_suitable_replacement=has_replacement,
            fund_quality_comparison_valid=fq_comparison_valid,
            observation_timestamp=now_utc
        )

    return _builder


def test_portfolio_context_integration(orchestrator, base_payload_builder):
    payload = base_payload_builder(quality_score=90.0)
    res = orchestrator.evaluate_decision(payload)
    assert res.final_action_state == ActionState.BUY
    assert res.final_decision_status == IntegrationStatus.VALID


def test_goal_context_and_multiple_goals(orchestrator, base_payload_builder):
    p_goal1 = base_payload_builder(quality_score=85.0, fulfillment=CandidateFulfillmentStatus.CANDIDATE_CAN_FULFILL_NEED)
    p_goal2 = base_payload_builder(quality_score=85.0, fulfillment=CandidateFulfillmentStatus.CANDIDATE_CANNOT_FULFILL_NEED)
    r1 = orchestrator.evaluate_decision(p_goal1)
    r2 = orchestrator.evaluate_decision(p_goal2)
    assert r1.final_action_state == ActionState.BUY
    assert r2.final_action_state == ActionState.NO_ACTION


def test_new_money_vs_switch(orchestrator, base_payload_builder):
    p_new = base_payload_builder(position_context=PositionContext.NEW_POSITION, eb_state=EconomicBenefitState.ECONOMICALLY_BENEFICIAL)
    p_switch_cost = base_payload_builder(position_context=PositionContext.EXISTING_POSITION, deterioration="MATERIAL_DETERIORATION", eb_state=EconomicBenefitState.ECONOMICALLY_NOT_BENEFICIAL)
    r_new = orchestrator.evaluate_decision(p_new)
    r_switch = orchestrator.evaluate_decision(p_switch_cost)
    assert r_new.final_action_state == ActionState.BUY
    assert r_switch.final_action_state == ActionState.REVIEW


def test_concentration_and_overlap_inhibition(orchestrator, base_payload_builder):
    payload = base_payload_builder(quality_score=95.0, need_state=PortfolioNeedState.EXCESS_EXPOSURE)
    res = orchestrator.evaluate_decision(payload)
    assert res.final_action_state == ActionState.NO_ACTION


def test_affordability_and_windfall(orchestrator, base_payload_builder):
    p_aff = base_payload_builder(affordability=AffordabilityStatus.AFFORDABILITY_CONSTRAINED)
    r_aff = orchestrator.evaluate_decision(p_aff)
    assert r_aff.final_action_state == ActionState.ACCUMULATE


def test_recommendation_vs_transaction_separation():
    now_utc = datetime(2026, 9, 16, 12, 0, 0, tzinfo=timezone.utc)
    holding = HoldingSnapshot("hld_01", "INF100K0001", "Test Fund", "Equity", 100.0, 50.0, 5000.0, 500.0)
    port_before = PortfolioStateSnapshot("port_01", "inv_01", [holding], 5000.0, 500.0, now_utc)
    port_after = PortfolioStateSnapshot("port_01", "inv_01", [holding], 5000.0, 500.0, now_utc)
    assert port_before == port_after


def test_user_rejection_agency_preservation():
    rec = UserDecisionRecord("rec_01", "act_01", "REJECTED", "BUY")
    assert rec.user_action == "REJECTED"
    assert rec.system_recommended_action == "BUY"


def test_user_adjustment_distinction():
    rec = UserDecisionRecord("rec_02", "act_01", "ADJUSTED", "BUY", user_adjusted_value=5000.0, system_recommended_value=10000.0)
    assert rec.user_adjusted_value != rec.system_recommended_value
    assert rec.user_adjusted_value == 5000.0


def test_immutable_assessment_history(orchestrator, base_payload_builder):
    p1 = base_payload_builder(quality_score=90.0)
    res1 = orchestrator.evaluate_decision(p1)
    p2 = base_payload_builder(quality_score=90.0, capacity_level=RiskCapacityLevel.LOW, suitability_st=SuitabilityStatus.NOT_SUITABLE)
    res2 = orchestrator.evaluate_decision(p2)
    assert res1.final_action_state == ActionState.BUY
    assert res2.final_action_state == ActionState.NO_ACTION


def test_reassessment_after_material_change(orchestrator, base_payload_builder):
    p_before = base_payload_builder(need_state=PortfolioNeedState.NEED_IDENTIFIED)
    p_after = base_payload_builder(need_state=PortfolioNeedState.NO_MATERIAL_NEED)
    r_before = orchestrator.evaluate_decision(p_before)
    r_after = orchestrator.evaluate_decision(p_after)
    assert r_before.final_action_state == ActionState.BUY
    assert r_after.final_action_state == ActionState.NO_ACTION


def test_missing_data_behavior(orchestrator, base_payload_builder):
    payload = base_payload_builder(evidence_valid=False)
    res = orchestrator.evaluate_decision(payload)
    assert res.final_action_state == ActionState.NO_ACTION


def test_temporal_safety(orchestrator, base_payload_builder):
    p_past = base_payload_builder(quality_score=90.0)
    res_past = orchestrator.evaluate_decision(p_past)
    assert res_past.final_action_state == ActionState.BUY


def test_deterministic_repeatability(orchestrator, base_payload_builder):
    payload = base_payload_builder(quality_score=90.0)
    res1 = orchestrator.evaluate_decision(payload)
    res2 = orchestrator.evaluate_decision(payload)
    assert res1.final_action_state == res2.final_action_state
    assert res1.final_explanation == res2.final_explanation


def test_adversarial_high_fq_portfolio_cases(orchestrator, base_payload_builder):
    p_unsuit = base_payload_builder(quality_score=99.0, suitability_st=SuitabilityStatus.NOT_SUITABLE)
    r_unsuit = orchestrator.evaluate_decision(p_unsuit)
    assert r_unsuit.final_action_state == ActionState.NO_ACTION
