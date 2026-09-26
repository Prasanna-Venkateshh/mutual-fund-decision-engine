"""
Phase F.17.1 — Low-Confidence Actionability & Conditional-Suitability Forensic Reconciliation Test Suite.

Validates:
1. Exact reproduction of S12 (High FQ 90.0 + Low Confidence 0.05 + Valid Evidence -> BUY).
2. Existing confidence/actionability contract (confidence is descriptive metadata, not a numerical filter cutoff).
3. Conditional suitability behavior (CONDITIONALLY_SUITABLE allows BUY/ACCUMULATE with warnings attached unless hard constraints exist).
4. Missing required evidence gating.
5. High-FQ BUY guardrails & Low-FQ SELL guardrails under low confidence.
6. Determinism.
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
            source_id="test_src_f17_1",
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
            canonical_scheme_id="INF100K0001",
            category="Equity",
            subcategory="Large Cap",
            fund_quality_comparison_valid=fq_comparison_valid,
            status=IntegrationStatus.VALID
        )

        min_level = AlignedRiskLevel.HIGH if (capacity_level == RiskCapacityLevel.HIGH and tolerance_level == RiskToleranceLevel.HIGH) else AlignedRiskLevel.LOW
        ra_res = RiskAlignmentAssessmentResult(
            assessment_id="ra_001",
            investor_id="inv_f17_1",
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
            investor_id="inv_f17_1",
            profile_version_used="1.0.0",
            canonical_scheme_id="INF100K0001",
            amfi_code="100000",
            scheme_name="Test Scheme",
            category="Equity",
            subcategory="Large Cap",
            observation_date=today,
            suitability_status=suitability_st,
            constraints_applied=constraints or [],
            goal_id="goal_01",
            suitability_confidence_score=1.0,
            provenance=prov,
            assessment_timestamp_utc=now_utc
        )
        suit_contract = from_suitability_result(suit_res)

        need_res = PortfolioNeedAssessmentResult(
            assessment_id="need_01",
            investor_id="inv_f17_1",
            goal_id="goal_01",
            scheme_id="INF100K0001",
            primary_state=need_state,
            candidate_fulfillment_status=fulfillment,
            affordability_status=affordability,
            funding_status=FundingStatus.UNDERFUNDED,
            observation_timestamp=now_utc,
            upstream_assessment_ids={"source_id": "test_src_f17_1"}
        )
        need_contract = from_portfolio_need_result(need_res)

        if custom_eb:
            eb_contract = custom_eb
        else:
            eb_contract = from_economic_benefit_result(
                assessment_id="eb_01",
                investor_id="inv_f17_1",
                economic_benefit_state=eb_state,
                candidate_scheme_id="INF100K0001",
                observation_date=today,
                assessment_timestamp_utc=now_utc,
                methodology_version="F.5.0",
                provenance=prov
            )

        return build_action_input_contract(
            assessment_id="act_01",
            investor_id="inv_f17_1",
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


def test_s12_exact_reproduction(orchestrator, base_payload_builder):
    """Test 1: S12 reproduction — High FQ (90.0) + Low Confidence (0.05) + Valid Evidence -> BUY."""
    payload = base_payload_builder(quality_score=90.0, quality_conf=0.05, evidence_valid=True)
    res = orchestrator.evaluate_decision(payload)
    assert res.final_action_state == ActionState.BUY
    assert res.final_decision_status.value == "VALID"


def test_low_confidence_behavior_with_invalid_evidence(orchestrator, base_payload_builder):
    """Test 2: Low confidence with invalid evidence flag -> NO_ACTION."""
    payload = base_payload_builder(quality_score=90.0, quality_conf=0.05, evidence_valid=False)
    res = orchestrator.evaluate_decision(payload)
    assert res.final_action_state == ActionState.NO_ACTION


def test_existing_confidence_actionability_contract_note(orchestrator, base_payload_builder):
    """Test 3: Verify confidence score is preserved in contract and does not act as numerical action cutoff."""
    payload = base_payload_builder(quality_score=90.0, quality_conf=0.01)
    res = orchestrator.evaluate_decision(payload)
    assert res.final_action_state == ActionState.BUY


def test_conditional_suitability_reproduction(orchestrator, base_payload_builder):
    """Test 4: CONDITIONALLY_SUITABLE status allows BUY with attached warning."""
    payload = base_payload_builder(quality_score=85.0, suitability_st=SuitabilityStatus.CONDITIONALLY_SUITABLE)
    res = orchestrator.evaluate_decision(payload)
    assert res.final_action_state == ActionState.BUY
    assert any("CONDITIONALLY_SUITABLE" in w for w in res.warnings)


def test_conditional_suitability_satisfied_conditions(orchestrator, base_payload_builder):
    """Test 5: CONDITIONALLY_SUITABLE + all downstream prerequisites -> BUY."""
    payload = base_payload_builder(
        quality_score=85.0,
        suitability_st=SuitabilityStatus.CONDITIONALLY_SUITABLE,
        need_state=PortfolioNeedState.NEED_IDENTIFIED,
        eb_state=EconomicBenefitState.ECONOMICALLY_BENEFICIAL
    )
    res = orchestrator.evaluate_decision(payload)
    assert res.final_action_state == ActionState.BUY


def test_conditional_suitability_not_satisfied_lock_in_conflict(orchestrator, base_payload_builder):
    """Test 6: CONDITIONALLY_SUITABLE + LOCK_IN_CONFLICT hard constraint -> NO_ACTION."""
    payload = base_payload_builder(
        quality_score=85.0,
        suitability_st=SuitabilityStatus.CONDITIONALLY_SUITABLE,
        constraints=["LOCK_IN_CONFLICT"]
    )
    res = orchestrator.evaluate_decision(payload)
    assert res.final_action_state == ActionState.NO_ACTION


def test_missing_required_evidence_fq(orchestrator, base_payload_builder):
    """Test 7: Missing FQ evidence for NEW_POSITION -> NO_ACTION."""
    payload = base_payload_builder(evidence_valid=False)
    res = orchestrator.evaluate_decision(payload)
    assert res.final_action_state == ActionState.NO_ACTION


def test_non_required_missing_metadata(orchestrator, base_payload_builder):
    """Test 8: Valid essential evidence with default friction metadata -> BUY."""
    payload = base_payload_builder(quality_score=90.0, quality_conf=0.5)
    res = orchestrator.evaluate_decision(payload)
    assert res.final_action_state == ActionState.BUY


def test_high_fq_buy_guardrail(orchestrator, base_payload_builder):
    """Test 9: High FQ + Unsuitable investor -> NO_ACTION."""
    payload = base_payload_builder(quality_score=95.0, suitability_st=SuitabilityStatus.NOT_SUITABLE)
    res = orchestrator.evaluate_decision(payload)
    assert res.final_action_state == ActionState.NO_ACTION


def test_low_fq_sell_guardrail(orchestrator, base_payload_builder):
    """Test 10: Low FQ + Existing Position (No Deterioration) -> HOLD."""
    payload = base_payload_builder(
        position_context=PositionContext.EXISTING_POSITION,
        quality_score=10.0,
        need_state=PortfolioNeedState.NO_MATERIAL_NEED,
        eb_state=EconomicBenefitState.NO_EVALUABLE_CHANGE
    )
    res = orchestrator.evaluate_decision(payload)
    assert res.final_action_state == ActionState.HOLD


def test_low_confidence_sell_evaluation(orchestrator, base_payload_builder):
    """Test 11: Low FQ + Low Conf + Validated Deterioration + Replacement + Beneficial -> SELL."""
    payload = base_payload_builder(
        position_context=PositionContext.EXISTING_POSITION,
        quality_score=10.0,
        quality_conf=0.05,
        deterioration="MATERIAL_DETERIORATION",
        has_replacement=True,
        eb_state=EconomicBenefitState.ECONOMICALLY_BENEFICIAL
    )
    res = orchestrator.evaluate_decision(payload)
    assert res.final_action_state == ActionState.SELL


def test_reconciliation_determinism(orchestrator, base_payload_builder):
    """Test 12: Determinism across repeated executions."""
    payload = base_payload_builder(quality_score=90.0, quality_conf=0.05)
    res1 = orchestrator.evaluate_decision(payload)
    res2 = orchestrator.evaluate_decision(payload)
    assert res1.final_action_state == res2.final_action_state
    assert res1.final_explanation == res2.final_explanation
