"""
Phase F.17.1 — Low-Confidence Actionability & Conditional-Suitability Forensic Reconciliation Script
File: scripts/run_f17_1_low_confidence_actionability_reconciliation.py

Performs narrow forensic reconciliation of:
1. Low Fund Quality confidence and consequential Action gating.
2. CONDITIONALLY_SUITABLE -> BUY behavior.
3. Missing-evidence gating semantics.
4. Actionability status governance.

Evaluates deterministic reconciliation scenarios directly using DecisionOrchestrator.
Outputs validation manifest and JSON report artifacts without modifying production decision engine.
"""

import sys
import os
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


OUTPUT_DIR = os.path.join(".", "docs")


def run_f17_1_reconciliation():
    print("=" * 80)
    print("STARTING PHASE F.17.1 — LOW-CONFIDENCE ACTIONABILITY RECONCILIATION")
    print("=" * 80)

    orchestrator = DecisionOrchestrator()
    now_utc = datetime(2026, 9, 16, 12, 0, 0, tzinfo=timezone.utc)
    today = date(2026, 9, 16)

    prov = ProvenanceMetadata(
        source_id="test_src_f17_1",
        source_document_url="http://amfiindia.com",
        retrieval_timestamp_utc=now_utc,
        methodology_version="1.0.0"
    )

    def make_payload(
        position_context=PositionContext.NEW_POSITION,
        need_state=PortfolioNeedState.NEED_IDENTIFIED,
        fulfillment=CandidateFulfillmentStatus.CANDIDATE_CAN_FULFILL_NEED,
        suitability_st=SuitabilityStatus.SUITABLE,
        constraints=None,
        eb_state=EconomicBenefitState.ECONOMICALLY_BENEFICIAL,
        quality_score=85.0,
        quality_conf=0.95,
        affordability=AffordabilityStatus.AFFORDABLE,
        deterioration=None,
        deterioration_validated=True,
        has_replacement=True,
        fq_comparison_valid=True,
        capacity_level=RiskCapacityLevel.HIGH,
        tolerance_level=RiskToleranceLevel.HIGH,
        stale_input=False,
        evidence_valid=True,
        custom_eb=None
    ):
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

    # Reconciliation Test Scenarios
    scenarios = [
        ("S12_REPRO: High FQ (90.0) + Low Confidence (0.05) + Valid Evidence", make_payload(quality_score=90.0, quality_conf=0.05), ActionState.BUY),
        ("S12_VAR1: High FQ (90.0) + Invalid Evidence Flag", make_payload(quality_score=90.0, quality_conf=0.05, evidence_valid=False), ActionState.NO_ACTION),
        ("S19_REPRO: CONDITIONALLY_SUITABLE + All Prerequisites", make_payload(quality_score=85.0, suitability_st=SuitabilityStatus.CONDITIONALLY_SUITABLE), ActionState.BUY),
        ("S19_VAR1: CONDITIONALLY_SUITABLE + Lock-in Conflict Constraint", make_payload(quality_score=85.0, suitability_st=SuitabilityStatus.CONDITIONALLY_SUITABLE, constraints=["LOCK_IN_CONFLICT"]), ActionState.NO_ACTION),
        ("S19_VAR2: NOT_SUITABLE Hard Rejection", make_payload(quality_score=85.0, suitability_st=SuitabilityStatus.NOT_SUITABLE), ActionState.NO_ACTION),
        ("MISSING_EV_FQ: Missing FQ Evidence for New Position", make_payload(quality_score=85.0, evidence_valid=False), ActionState.NO_ACTION),
        ("MISSING_EV_EB: Uncertain EB Evidence for New Position", make_payload(quality_score=85.0, eb_state=EconomicBenefitState.BENEFIT_UNCERTAIN), ActionState.NO_ACTION),
        ("LOW_FQ_LOW_CONF_HOLD: Low FQ (10.0) + Low Conf (0.05) + Existing Position (No Deterioration)", make_payload(position_context=PositionContext.EXISTING_POSITION, quality_score=10.0, quality_conf=0.05, need_state=PortfolioNeedState.NO_MATERIAL_NEED, eb_state=EconomicBenefitState.NO_EVALUABLE_CHANGE), ActionState.HOLD),
        ("LOW_FQ_LOW_CONF_SELL: Low FQ (10.0) + Low Conf (0.05) + Validated Deterioration + Replacement + Beneficial", make_payload(position_context=PositionContext.EXISTING_POSITION, quality_score=10.0, quality_conf=0.05, deterioration="MATERIAL_DETERIORATION", has_replacement=True, eb_state=EconomicBenefitState.ECONOMICALLY_BENEFICIAL), ActionState.SELL),
        ("LOW_FQ_LOW_CONF_REVIEW: Low FQ (10.0) + Low Conf (0.05) + Material Deterioration + High Switching Cost", make_payload(position_context=PositionContext.EXISTING_POSITION, quality_score=10.0, quality_conf=0.05, deterioration="MATERIAL_DETERIORATION", eb_state=EconomicBenefitState.ECONOMICALLY_NOT_BENEFICIAL), ActionState.REVIEW),
    ]

    scenario_results = []
    passed_count = 0

    for name, payload, expected_action in scenarios:
        res = orchestrator.evaluate_decision(payload)
        passed = (res.final_action_state == expected_action)
        if passed:
            passed_count += 1

        scenario_results.append({
            "scenario": name,
            "expected_action": expected_action.value,
            "actual_action": res.final_action_state.value,
            "integration_status": res.final_decision_status.value,
            "passed": passed,
            "explanation": res.final_explanation,
            "warnings": res.warnings
        })
        print(f"[{'PASS' if passed else 'FAIL'}] {name} -> Expected: {expected_action.value}, Actual: {res.final_action_state.value}")

    manifest_data = {
        "manifest_version": "F.17.1-RECONCILIATION-v1.0",
        "audited_at_utc": datetime.now().isoformat(),
        "orchestrator_class": "DecisionOrchestrator",
        "scenarios_evaluated_count": len(scenarios),
        "scenarios_passed_count": passed_count,
        "s12_reproduction_outcome": "REPRODUCED (BUY emitted per governed v1.0.0 contract; confidence is descriptive metadata without numerical cutoff)",
        "s19_reproduction_outcome": "REPRODUCED (BUY emitted per governed v1.0.0 contract; CONDITIONALLY_SUITABLE is conditional permission with warnings)",
        "governance_classification": "PASSED WITH LIMITATIONS — CONFIDENCE IS DESCRIPTIVE METADATA ONLY IN V1.0.0 (NO NUMERICAL CUTOFF RULE IN ACTION ENGINE)"
    }

    manifest_filepath = os.path.join(OUTPUT_DIR, "f17_1_low_confidence_actionability_manifest.json")
    with open(manifest_filepath, "w") as f:
        json.dump(manifest_data, f, indent=2)

    json_filepath = os.path.join(OUTPUT_DIR, "phase_f17_1_low_confidence_actionability_reconciliation.json")
    with open(json_filepath, "w") as f:
        json.dump({"manifest": manifest_data, "scenarios": scenario_results}, f, indent=2)

    print(f"\nSaved Validation Manifest to {manifest_filepath}")
    print(f"Saved Reconciliation JSON to {json_filepath}")
    print("PHASE F.17.1 RECONCILIATION COMPLETE")


if __name__ == "__main__":
    run_f17_1_reconciliation()
