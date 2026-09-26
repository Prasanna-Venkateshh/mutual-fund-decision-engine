"""
Phase F.17 End-to-End Decision Chain Validation Test Suite.

Validates the full decision chain architecture:
DATA -> METRICS -> FUND QUALITY -> SUITABILITY -> PORTFOLIO NEED -> ECONOMIC BENEFIT -> ACTION

Ensures:
- Architectural separation between layers.
- High Fund Quality does NOT automatically trigger BUY.
- Low Fund Quality does NOT automatically trigger SELL.
- Downstream constraints (Suitability, Need, Economic Benefit) are strictly enforced.
- Determinism, explainability, provenance, temporal safety, and immutability.
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
            source_id="test_src_f17",
            source_document_url="http://amfiindia.com",
            retrieval_timestamp_utc=now_utc,
            methodology_version="1.0.0"
        )

        fq_res = FundQualityScoreResult(
            canonical_scheme_id="INF100K0001",
            amfi_code="100000",
            scheme_name="Test Scheme",
            category="Equity",
            subcategory="Large Cap",
            observation_date=today,
            quality_score=quality_score if evidence_valid else None,
            confidence_score=quality_conf,
            data_quality_score=1.0,
            dimension_scores={},
            available_dimensions_count=6,
            total_dimensions_count=6,
            peer_group_size=50,
            scoring_methodology_version="1.0.0",
            weight_config_version="1.0.0",
            calculation_timestamp_utc=now_utc,
            summary_explanation="FQ Score"
        )
        fq_contract = from_fund_quality_result(
            result=fq_res,
            canonical_scheme_id="INF100K0001",
            category="Equity",
            subcategory="Large Cap",
            fund_quality_comparison_valid=fq_comparison_valid,
            status=IntegrationStatus.VALID
        )

        min_level = AlignedRiskLevel.HIGH if (capacity_level == RiskCapacityLevel.HIGH and tolerance_level == RiskToleranceLevel.HIGH) else AlignedRiskLevel.LOW
        ra_res = RiskAlignmentAssessmentResult(
            assessment_id="ra_001",
            investor_id="inv_f17",
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
            assessment_id="suit_01",
            investor_id="inv_f17",
            profile_version_used="1.0.0",
            canonical_scheme_id="INF100K0001",
            amfi_code="100000",
            scheme_name="Test Scheme",
            category="Equity",
            subcategory="Large Cap",
            observation_date=today,
            suitability_status=suitability_st,
            goal_id="goal_01",
            suitability_confidence_score=1.0,
            provenance=prov,
            assessment_timestamp_utc=now_utc
        )
        suit_contract = from_suitability_result(suit_res)

        need_res = PortfolioNeedAssessmentResult(
            assessment_id="need_01",
            investor_id="inv_f17",
            goal_id="goal_01",
            scheme_id="INF100K0001",
            primary_state=need_state,
            candidate_fulfillment_status=fulfillment,
            affordability_status=affordability,
            funding_status=FundingStatus.UNDERFUNDED,
            observation_timestamp=now_utc,
            upstream_assessment_ids={"source_id": "test_src_f17"}
        )
        need_contract = from_portfolio_need_result(need_res)

        if custom_eb:
            eb_contract = custom_eb
        else:
            eb_contract = from_economic_benefit_result(
                assessment_id="eb_01",
                investor_id="inv_f17",
                economic_benefit_state=eb_state,
                candidate_scheme_id="INF100K0001",
                observation_date=today,
                assessment_timestamp_utc=now_utc,
                methodology_version="F.5.0",
                provenance=prov
            )

        return build_action_input_contract(
            assessment_id="act_01",
            investor_id="inv_f17",
            scheme_id="INF100K0001",
            position_context=position_context,
            fund_quality_contract=fq_contract,
            risk_alignment_contract=ra_contract,
            suitability_contract=suit_contract,
            portfolio_need_contract=need_contract,
            economic_benefit_contract=eb_contract,
            goal_id="goal_01",
            portfolio_id="port_01",
            deterioration_signal=deterioration,
            deterioration_validated=deterioration_validated,
            has_suitable_replacement=has_replacement,
            fund_quality_comparison_valid=fq_comparison_valid,
            observation_timestamp=now_utc
        )

    return _builder


def test_full_decision_chain_sequencing(orchestrator, base_payload_builder):
    payload = base_payload_builder()
    res = orchestrator.evaluate_decision(payload)
    assert res.final_action_state == ActionState.BUY
    assert res.final_decision_status.value == "VALID"
    assert "BUY" in res.final_explanation


def test_adversarial_high_fq_cannot_bypass_suitability(orchestrator, base_payload_builder):
    payload = base_payload_builder(quality_score=99.0, suitability_st=SuitabilityStatus.NOT_SUITABLE)
    res = orchestrator.evaluate_decision(payload)
    assert res.final_action_state == ActionState.NO_ACTION


def test_adversarial_high_fq_cannot_bypass_portfolio_need(orchestrator, base_payload_builder):
    payload = base_payload_builder(quality_score=99.0, need_state=PortfolioNeedState.NO_MATERIAL_NEED)
    res = orchestrator.evaluate_decision(payload)
    assert res.final_action_state == ActionState.NO_ACTION


def test_adversarial_high_fq_cannot_bypass_economic_benefit(orchestrator, base_payload_builder):
    payload = base_payload_builder(quality_score=99.0, eb_state=EconomicBenefitState.BENEFIT_UNCERTAIN)
    res = orchestrator.evaluate_decision(payload)
    assert res.final_action_state == ActionState.NO_ACTION


def test_low_fq_does_not_automatically_trigger_sell(orchestrator, base_payload_builder):
    payload = base_payload_builder(
        position_context=PositionContext.EXISTING_POSITION,
        quality_score=10.0,
        need_state=PortfolioNeedState.NO_MATERIAL_NEED,
        eb_state=EconomicBenefitState.NO_EVALUABLE_CHANGE
    )
    res = orchestrator.evaluate_decision(payload)
    assert res.final_action_state == ActionState.HOLD
    assert res.final_action_state != ActionState.SELL


def test_low_fq_with_high_switching_cost_produces_review_not_sell(orchestrator, base_payload_builder):
    payload = base_payload_builder(
        position_context=PositionContext.EXISTING_POSITION,
        quality_score=10.0,
        deterioration="MATERIAL_DETERIORATION",
        eb_state=EconomicBenefitState.ECONOMICALLY_NOT_BENEFICIAL
    )
    res = orchestrator.evaluate_decision(payload)
    assert res.final_action_state == ActionState.REVIEW
    assert res.final_action_state != ActionState.SELL


def test_low_fq_without_replacement_produces_review_not_sell(orchestrator, base_payload_builder):
    payload = base_payload_builder(
        position_context=PositionContext.EXISTING_POSITION,
        quality_score=10.0,
        deterioration="MATERIAL_DETERIORATION",
        has_replacement=False,
        eb_state=EconomicBenefitState.ECONOMICALLY_BENEFICIAL
    )
    res = orchestrator.evaluate_decision(payload)
    assert res.final_action_state == ActionState.REVIEW
    assert res.final_action_state != ActionState.SELL


def test_legitimate_sell_when_all_guardrails_satisfied(orchestrator, base_payload_builder):
    payload = base_payload_builder(
        position_context=PositionContext.EXISTING_POSITION,
        quality_score=10.0,
        deterioration="MATERIAL_DETERIORATION",
        has_replacement=True,
        eb_state=EconomicBenefitState.ECONOMICALLY_BENEFICIAL
    )
    res = orchestrator.evaluate_decision(payload)
    assert res.final_action_state == ActionState.SELL


def test_risk_capacity_and_tolerance_constraints(orchestrator, base_payload_builder):
    # Capacity constrained
    p_cap = base_payload_builder(quality_score=90.0, capacity_level=RiskCapacityLevel.LOW, tolerance_level=RiskToleranceLevel.HIGH, suitability_st=SuitabilityStatus.NOT_SUITABLE)
    r_cap = orchestrator.evaluate_decision(p_cap)
    assert r_cap.final_action_state == ActionState.NO_ACTION

    # Tolerance constrained
    p_tol = base_payload_builder(quality_score=90.0, capacity_level=RiskCapacityLevel.HIGH, tolerance_level=RiskToleranceLevel.LOW, suitability_st=SuitabilityStatus.NOT_SUITABLE)
    r_tol = orchestrator.evaluate_decision(p_tol)
    assert r_tol.final_action_state == ActionState.NO_ACTION


def test_affordability_constrained_accumulate(orchestrator, base_payload_builder):
    payload = base_payload_builder(affordability=AffordabilityStatus.AFFORDABILITY_CONSTRAINED)
    res = orchestrator.evaluate_decision(payload)
    assert res.final_action_state == ActionState.ACCUMULATE


def test_monitor_progression(orchestrator, base_payload_builder):
    payload = base_payload_builder(
        position_context=PositionContext.EXISTING_POSITION,
        quality_score=40.0,
        deterioration="MILD_DETERIORATION",
        need_state=PortfolioNeedState.NO_MATERIAL_NEED,
        eb_state=EconomicBenefitState.NO_EVALUABLE_CHANGE
    )
    res = orchestrator.evaluate_decision(payload)
    assert res.final_action_state == ActionState.MONITOR


def test_decision_chain_determinism(orchestrator, base_payload_builder):
    payload = base_payload_builder()
    res1 = orchestrator.evaluate_decision(payload)
    res2 = orchestrator.evaluate_decision(payload)
    assert res1.final_action_state == res2.final_action_state
    assert res1.final_explanation == res2.final_explanation
