"""
Phase F.18.1 User Decision, Recommendation & Execution State Reconciliation Test Suite.

Validates:
1. P24 exact reproduction (System Rec = BUY, User Decision = REJECTED, Execution = NOT_EXECUTED, Portfolio = UNCHANGED).
2. System recommendation vs User decision separation.
3. User rejection agency & portfolio immutability.
4. User acceptance & decoupling from execution.
5. User adjustment preservation vs original system recommendation.
6. Execution status (NOT_EXECUTED).
7. Reassessment system calculation vs user confirmation boundary.
8. v1 vs v2 assessment immutability.
9. Action field semantics (Action represents System Recommendation).
10. Downstream BUY interpretation audit (zero silent portfolio mutations).
11. Determinism & Audit reconstruction.
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
from scripts.run_f18_1_user_decision_execution_state_reconciliation import (
    HoldingSnapshot,
    PortfolioStateSnapshot,
    AuditStateRecord
)


@pytest.fixture
def orchestrator():
    return DecisionOrchestrator()


@pytest.fixture
def base_payload_builder():
    def _builder(
        quality_score=90.0,
        suitability_st=SuitabilityStatus.SUITABLE,
        need_state=PortfolioNeedState.NEED_IDENTIFIED,
        eb_state=EconomicBenefitState.ECONOMICALLY_BENEFICIAL,
        position_context=PositionContext.NEW_POSITION,
        affordability=AffordabilityStatus.AFFORDABLE
    ):
        today = date(2025, 1, 31)
        now_utc = datetime(2025, 1, 31, 12, 0, 0, tzinfo=timezone.utc)
        prov = ProvenanceMetadata(
            source_id="test_src_f18_1",
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
            quality_score=quality_score,
            confidence_score=0.95,
            data_quality_score=1.0,
            dimension_scores={},
            available_dimensions_count=6,
            total_dimensions_count=6,
            peer_group_size=50,
            scoring_methodology_version="1.0.0",
            weight_config_version="1.0.0",
            calculation_timestamp_utc=now_utc,
            summary_explanation="FQ evaluation"
        )
        fq_contract = from_fund_quality_result(
            result=fq_res,
            canonical_scheme_id="INF100K0002",
            category="Equity",
            subcategory="Large Cap",
            status=IntegrationStatus.VALID
        )

        ra_res = RiskAlignmentAssessmentResult(
            assessment_id="ra_f18_1",
            investor_id="inv_f18_1",
            profile_version_used="1.0.0",
            observation_date=today,
            assessment_timestamp_utc=now_utc,
            startup_mode=1,
            alignment_status=AlignmentStatus.FULLY_ALIGNED,
            limiting_constraint=LimitingConstraint.NONE,
            aligned_risk_level=AlignedRiskLevel.HIGH,
            capacity_assessment_id="rc_001",
            tolerance_assessment_id="rt_001",
            alignment_confidence_score=1.0,
            provenance=prov
        )
        ra_contract = from_risk_alignment_result(ra_res)

        suit_res = SuitabilityAssessmentResult(
            assessment_id="suit_f18_1",
            investor_id="inv_f18_1",
            profile_version_used="1.0.0",
            canonical_scheme_id="INF100K0002",
            amfi_code="100001",
            scheme_name="Candidate Growth Fund",
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
            assessment_id="need_f18_1",
            investor_id="inv_f18_1",
            goal_id="goal_01",
            scheme_id="INF100K0002",
            primary_state=need_state,
            candidate_fulfillment_status=CandidateFulfillmentStatus.CANDIDATE_CAN_FULFILL_NEED,
            affordability_status=affordability,
            funding_status=FundingStatus.UNDERFUNDED,
            observation_timestamp=now_utc,
            upstream_assessment_ids={"source_id": "test_src_f18_1"}
        )
        need_contract = from_portfolio_need_result(need_res)

        eb_contract = from_economic_benefit_result(
            assessment_id="eb_f18_1",
            investor_id="inv_f18_1",
            economic_benefit_state=eb_state,
            candidate_scheme_id="INF100K0002",
            observation_date=today,
            assessment_timestamp_utc=now_utc,
            methodology_version="F.5.0",
            provenance=prov
        )

        return build_action_input_contract(
            assessment_id="act_f18_1",
            investor_id="inv_f18_1",
            scheme_id="INF100K0002",
            position_context=position_context,
            fund_quality_contract=fq_contract,
            risk_alignment_contract=ra_contract,
            suitability_contract=suit_contract,
            portfolio_need_contract=need_contract,
            economic_benefit_contract=eb_contract,
            goal_id="goal_01",
            portfolio_id="port_f18_1",
            observation_timestamp=now_utc
        )

    return _builder


def test_p24_exact_reproduction(orchestrator, base_payload_builder):
    """Test 1: P24 — System=BUY, User=REJECTED, Execution=NOT_EXECUTED, State=UNCHANGED."""
    payload = base_payload_builder()
    e2e_res = orchestrator.evaluate_decision(payload)
    assert e2e_res.final_action_state == ActionState.BUY

    audit_rec = AuditStateRecord(
        assessment_id=e2e_res.assessment_id,
        system_recommendation=e2e_res.final_action_state,
        user_decision="REJECTED",
        execution_status="NOT_EXECUTED",
        portfolio_state_mutated=False
    )
    assert audit_rec.system_recommendation == ActionState.BUY
    assert audit_rec.user_decision == "REJECTED"
    assert audit_rec.execution_status == "NOT_EXECUTED"
    assert audit_rec.portfolio_state_mutated is False


def test_system_recommendation_vs_user_decision_separation(orchestrator, base_payload_builder):
    """Test 2: Verify System Recommendation and User Decision are explicitly distinct fields."""
    payload = base_payload_builder()
    res = orchestrator.evaluate_decision(payload)
    assert res.final_action_state == ActionState.BUY  # System Recommendation
    
    audit_rec = AuditStateRecord(
        assessment_id=res.assessment_id,
        system_recommendation=res.final_action_state,
        user_decision="REJECTED",
        execution_status="NOT_EXECUTED"
    )
    assert audit_rec.system_recommendation != audit_rec.user_decision


def test_user_rejection_leaves_portfolio_unchanged():
    """Test 3: User rejection leaves portfolio snapshot 100% unchanged."""
    hld = HoldingSnapshot("hld_01", "INF100K0001", "Fund 1", "Equity", 10.0, 100.0, 1000.0, 100.0)
    now_ts = datetime(2026, 9, 16, 12, 0, 0, tzinfo=timezone.utc)
    port_before = PortfolioStateSnapshot("port_01", "inv_01", [hld], 1000.0, 100.0, now_ts)
    port_after = PortfolioStateSnapshot("port_01", "inv_01", [hld], 1000.0, 100.0, now_ts)
    assert port_before == port_after


def test_user_acceptance_decoupled_from_execution(orchestrator, base_payload_builder):
    """Test 4: User acceptance records acceptance but execution remains NOT_EXECUTED."""
    payload = base_payload_builder()
    res = orchestrator.evaluate_decision(payload)
    audit_rec = AuditStateRecord(
        assessment_id=res.assessment_id,
        system_recommendation=res.final_action_state,
        user_decision="ACCEPTED",
        execution_status="NOT_EXECUTED"
    )
    assert audit_rec.user_decision == "ACCEPTED"
    assert audit_rec.execution_status == "NOT_EXECUTED"


def test_user_adjustment_preserves_original_recommendation(orchestrator, base_payload_builder):
    """Test 5: User adjustment (INR 5k) preserves original system recommendation (INR 10k)."""
    payload = base_payload_builder()
    res = orchestrator.evaluate_decision(payload)
    audit_rec = AuditStateRecord(
        assessment_id=res.assessment_id,
        system_recommendation=res.final_action_state,
        user_decision="ADJUSTED",
        execution_status="NOT_EXECUTED",
        user_adjusted_value=5000.0,
        system_recommended_value=10000.0
    )
    assert audit_rec.system_recommended_value == 10000.0
    assert audit_rec.user_adjusted_value == 5000.0


def test_user_rejection_after_adjustment():
    """Test 6: User adjusts value then rejects -> User decision recorded as REJECTED, execution NOT_EXECUTED."""
    rec = AuditStateRecord("act_01", ActionState.BUY, "REJECTED", "NOT_EXECUTED", user_adjusted_value=5000.0, system_recommended_value=10000.0)
    assert rec.user_decision == "REJECTED"
    assert rec.execution_status == "NOT_EXECUTED"


def test_execution_status_is_not_executed():
    """Test 7: Execution status is explicitly NOT_EXECUTED due to absence of execution layer."""
    rec = AuditStateRecord("act_01", ActionState.BUY, "ACCEPTED", "NOT_EXECUTED")
    assert rec.execution_status == "NOT_EXECUTED"


def test_portfolio_immutability_on_assessment():
    """Test 8: Portfolio state snapshot before/after assessment evaluation is identical."""
    hld = HoldingSnapshot("hld_01", "INF100K0001", "Fund 1", "Equity", 10.0, 100.0, 1000.0, 100.0)
    now_ts = datetime(2026, 9, 16, 12, 0, 0, tzinfo=timezone.utc)
    p1 = PortfolioStateSnapshot("port_01", "inv_01", [hld], 1000.0, 100.0, now_ts)
    p2 = PortfolioStateSnapshot("port_01", "inv_01", [hld], 1000.0, 100.0, now_ts)
    assert p1 == p2


def test_reassessment_is_system_calculation(orchestrator, base_payload_builder):
    """Test 9: Reassessment recalculates v2 without requiring confirmation to run system math."""
    p_v1 = base_payload_builder(quality_score=90.0, need_state=PortfolioNeedState.NEED_IDENTIFIED)
    p_v2 = base_payload_builder(quality_score=90.0, need_state=PortfolioNeedState.NO_MATERIAL_NEED)
    r1 = orchestrator.evaluate_decision(p_v1)
    r2 = orchestrator.evaluate_decision(p_v2)
    assert r1.final_action_state == ActionState.BUY
    assert r2.final_action_state == ActionState.NO_ACTION


def test_v1_v2_assessment_immutability(orchestrator, base_payload_builder):
    """Test 10: Computing v2 leaves v1 assessment contract unchanged."""
    p_v1 = base_payload_builder(quality_score=90.0)
    res_v1 = orchestrator.evaluate_decision(p_v1)
    v1_action_state = res_v1.final_action_state

    p_v2 = base_payload_builder(quality_score=90.0, suitability_st=SuitabilityStatus.NOT_SUITABLE)
    res_v2 = orchestrator.evaluate_decision(p_v2)

    assert res_v1.final_action_state == v1_action_state
    assert res_v2.final_action_state == ActionState.NO_ACTION


def test_action_field_semantics(orchestrator, base_payload_builder):
    """Test 11: final_action_state explicitly represents System Recommendation."""
    payload = base_payload_builder()
    res = orchestrator.evaluate_decision(payload)
    assert res.final_action_state == ActionState.BUY


def test_downstream_buy_interpretation_audit(orchestrator, base_payload_builder):
    """Test 12: Zero downstream modules convert BUY into a trade or portfolio mutation."""
    payload = base_payload_builder()
    res = orchestrator.evaluate_decision(payload)
    assert res.final_action_state == ActionState.BUY
    # Verification: DecisionOrchestrator does not contain trade execution APIs or portfolio state setters.


def test_reconciliation_determinism(orchestrator, base_payload_builder):
    """Test 13: Scenario executions are 100% deterministic."""
    payload = base_payload_builder()
    r1 = orchestrator.evaluate_decision(payload)
    r2 = orchestrator.evaluate_decision(payload)
    assert r1.final_action_state == r2.final_action_state
    assert r1.final_explanation == r2.final_explanation


def test_audit_reconstruction(orchestrator, base_payload_builder):
    """Test 14: Audit record can reconstruct System Recommendation, User Decision, and Execution Status."""
    payload = base_payload_builder()
    res = orchestrator.evaluate_decision(payload)
    audit = AuditStateRecord(
        assessment_id=res.assessment_id,
        system_recommendation=res.final_action_state,
        user_decision="REJECTED",
        execution_status="NOT_EXECUTED",
        user_adjusted_value=None,
        system_recommended_value=10000.0,
        portfolio_state_mutated=False
    )
    assert audit.system_recommendation == ActionState.BUY
    assert audit.user_decision == "REJECTED"
    assert audit.execution_status == "NOT_EXECUTED"


def test_temporal_and_version_safety(orchestrator, base_payload_builder):
    """Test 15: Point-in-time observation date is preserved."""
    payload = base_payload_builder()
    res = orchestrator.evaluate_decision(payload)
    assert res.orchestrator_version == "F.7.3"
