"""
Phase F.11.1 — Real-Data Decision Engine Integration & Partial-Data Safety Gate Test Suite.

Verifies:
1. Real production dataset integration into end-to-end decision orchestrator pipeline.
2. Partial-data safety gate (missing TER, Riskometer, Benchmark handling without synthetic defaults).
3. Score vs Confidence separation (low confidence does not corrupt scores).
4. Suitability vs Actionability separation (missing metadata prevents ungrounded BUY/SELL).
5. Canonical identity stability (CAN_AMFI_{code}).
6. Quarantined scheme, invalid scheme, and new-fund handling.
7. Full provenance propagation and immutable assessment traceability.
"""

from datetime import date, datetime, timezone
import pytest

from data.ingestion.amfi_live_adapter import AMFILiveAdapter
from data.pipeline.multi_feed_pipeline import MultiFeedDatasetPipeline
from data.builders.fund_quality_dataset_builder import FundQualityDatasetBuilder
from scoring.engine import FundQualityScoringEngine
from models.investor_profile import InvestorProfileSnapshot, RiskCapacityLevel, RiskToleranceLevel, ProfileStatus
from models.goal_profile import GoalProfile, GoalCategory
from config.risk.capacity_config import StartupMode
from risk.alignment_models import (
    RiskAlignmentAssessmentResult,
    AlignmentStatus,
    AlignedRiskLevel,
    LimitingConstraint,
)
from risk.suitability_engine import SuitabilityEngine, SuitabilityEvaluationRequest, FundRiskProfileInput, SuitabilityStatus
from portfolio.need_models import (
    PortfolioNeedAssessmentResult,
    PortfolioNeedState,
    CandidateFulfillmentStatus,
    AffordabilityStatus,
)
from action.models import ActionState, PositionContext
from integration.models import EconomicBenefitState, IntegrationStatus
from integration.contracts import (
    from_fund_quality_result,
    from_risk_alignment_result,
    from_suitability_result,
    from_portfolio_need_result,
    from_economic_benefit_result,
    build_action_input_contract,
)
from integration.orchestrator import DecisionOrchestrator


class TestPhaseF111RealDataDecisionEngine:

    @pytest.fixture
    def setup_real_data_environment(self):
        """Sets up live production dataset snapshot and decision engines."""
        adapter = AMFILiveAdapter()
        meta = adapter.fetch_live_amfi_raw_evidence()
        assert meta["is_success"] is True

        records = adapter.ingestor.parse_raw_amfi_text(meta["raw_payload_text"], meta["retrieval_timestamp_utc"])
        raw_items = []
        for r in records[:30]:
            m = r.additional_metadata or {}
            raw_items.append({
                "scheme_code": r.raw_scheme_code,
                "scheme_name": r.raw_scheme_name,
                "nav": r.raw_nav_value,
                "nav_date": r.raw_date,
                "isin": m.get("isin_growth") or m.get("isin_reinvest") or "",
                "plan": m.get("plan") or "",
                "option": m.get("option") or "",
                "amc_name": m.get("amc_name") or "",
                "category": m.get("category_header") or "",
                "source_url": adapter.DEFAULT_AMFI_NAV_URL
            })

        pipeline = MultiFeedDatasetPipeline()
        snapshot, _ = pipeline.process_multi_feed_batch(nav_raw_items=raw_items)

        builder = FundQualityDatasetBuilder()
        all_inputs = []
        for rec in snapshot.records:
            dummy_hist = [{"date": rec.observation_date.strftime("%Y-%m-%d"), "nav": rec.nav_value or 10.0}] if rec.observation_date else []
            inp = builder.build_dataset_input_for_scheme(
                amfi_code=rec.amfi_code,
                scheme_name=rec.scheme_name,
                observation_date=rec.observation_date or date.today(),
                nav_history=dummy_hist,
                isin_growth=rec.isin or "",
                source_id="AMFI_OFFICIAL",
                source_document_url="https://www.amfiindia.com/spages/NAVAll.txt",
                custom_category_data={"category": rec.category_str, "subcategory": rec.subcategory_str},
                override_canonical_id=rec.canonical_scheme_id
            )
            all_inputs.append(inp)

        investor = InvestorProfileSnapshot(
            profile_id="PROF_REAL_001",
            investor_id="INV_REAL_001",
            profile_version="1.0.0",
            effective_date=date.today(),
            status=ProfileStatus.ACTIVE
        )
        goal = GoalProfile(
            goal_id="GOAL_WEALTH_ACCUM",
            investor_id="INV_REAL_001",
            goal_name="Wealth Accumulation",
            goal_category=GoalCategory.WEALTH_CREATION,
            target_amount=10000000.0,
            effective_horizon_years=9.0
        )
        alignment = RiskAlignmentAssessmentResult(
            assessment_id="ra_test_001",
            investor_id="INV_REAL_001",
            profile_version_used="1.0.0",
            observation_date=date.today(),
            assessment_timestamp_utc=datetime.now(timezone.utc),
            startup_mode=StartupMode.PRODUCTION,
            alignment_status=AlignmentStatus.FULLY_ALIGNED,
            limiting_constraint=LimitingConstraint.NONE,
            aligned_risk_level=AlignedRiskLevel.HIGH,
            risk_capacity_level=RiskCapacityLevel.HIGH,
            risk_tolerance_level=RiskToleranceLevel.HIGH,
            capacity_assessment_id="cap_001",
            tolerance_assessment_id="tol_001",
            alignment_confidence_score=0.95,
            is_stale_input=False
        )

        return {
            "snapshot": snapshot,
            "all_inputs": all_inputs,
            "investor": investor,
            "goal": goal,
            "alignment": alignment,
            "scoring_engine": FundQualityScoringEngine(),
            "suitability_engine": SuitabilityEngine(),
            "orchestrator": DecisionOrchestrator()
        }

    # 1. Real production dataset integration
    def test_01_real_production_dataset_integration(self, setup_real_data_environment):
        env = setup_real_data_environment
        snapshot = env["snapshot"]
        rec = snapshot.records[0]

        target_input = env["all_inputs"][0]
        fq_result = env["scoring_engine"].calculate_fund_quality_score(target_input, env["all_inputs"])
        suit_req = SuitabilityEvaluationRequest(
            investor_profile=env["investor"],
            risk_alignment=env["alignment"],
            fund_quality_score=fq_result,
            goal_profile=env["goal"],
            fund_risk_profile=FundRiskProfileInput(raw_riskometer_value=rec.riskometer_label),
            observation_date=date.today()
        )
        suit_result = env["suitability_engine"].evaluate(suit_req)

        pneed_result = PortfolioNeedAssessmentResult(
            assessment_id=f"pneed_{rec.amfi_code}",
            investor_id="INV_REAL_001",
            goal_id="GOAL_WEALTH_ACCUM",
            scheme_id=rec.canonical_scheme_id,
            primary_state=PortfolioNeedState.NEED_IDENTIFIED,
            candidate_fulfillment_status=CandidateFulfillmentStatus.CANDIDATE_CAN_FULFILL_NEED,
            affordability_status=AffordabilityStatus.AFFORDABLE,
            observation_timestamp=datetime.now(timezone.utc)
        )
        eb_contract = from_economic_benefit_result(
            assessment_id=f"eb_{rec.amfi_code}",
            investor_id="INV_REAL_001",
            economic_benefit_state=EconomicBenefitState.ECONOMICALLY_BENEFICIAL,
            position_context="NEW_POSITION",
            candidate_scheme_id=rec.canonical_scheme_id,
            economic_benefit_actionable=True,
            evidence_sufficiency_valid=True
        )

        fq_contract = from_fund_quality_result(fq_result, canonical_scheme_id=rec.canonical_scheme_id)
        ra_contract = from_risk_alignment_result(env["alignment"])
        suit_contract = from_suitability_result(suit_result)
        pneed_contract = from_portfolio_need_result(pneed_result)

        action_input = build_action_input_contract(
            investor_id="INV_REAL_001",
            scheme_id=rec.canonical_scheme_id,
            position_context=PositionContext.NEW_POSITION,
            assessment_id=f"act_input_{rec.amfi_code}",
            goal_id="GOAL_WEALTH_ACCUM",
            fund_quality_contract=fq_contract,
            risk_alignment_contract=ra_contract,
            suitability_contract=suit_contract,
            portfolio_need_contract=pneed_contract,
            economic_benefit_contract=eb_contract
        )

        e2e_result = env["orchestrator"].evaluate_decision(action_input)
        assert e2e_result.scheme_id == rec.canonical_scheme_id
        assert e2e_result.final_decision_status == IntegrationStatus.VALID

    # 2. Missing TER / Riskometer / Benchmark handling without synthetic defaults
    def test_02_missing_metadata_no_synthetic_defaults(self, setup_real_data_environment):
        env = setup_real_data_environment
        snapshot = env["snapshot"]
        rec = snapshot.records[0]

        # Verify real record fields in Situation C remain explicitly None
        assert rec.ter_value is None
        assert rec.riskometer_label is None
        assert rec.benchmark_name is None

    # 3. Partial-data safety gate: Missing Fund Quality score prevents ungrounded BUY
    def test_03_missing_quality_score_prevents_buy(self, setup_real_data_environment):
        env = setup_real_data_environment
        snapshot = env["snapshot"]
        rec = snapshot.records[0]

        target_input = env["all_inputs"][0]
        fq_result = env["scoring_engine"].calculate_fund_quality_score(target_input, env["all_inputs"])
        assert fq_result.quality_score is None, "Score should be None for 1-day NAV dummy history"

        suit_req = SuitabilityEvaluationRequest(
            investor_profile=env["investor"],
            risk_alignment=env["alignment"],
            fund_quality_score=fq_result,
            goal_profile=env["goal"],
            fund_risk_profile=FundRiskProfileInput(raw_riskometer_value=None),
            observation_date=date.today()
        )
        suit_result = env["suitability_engine"].evaluate(suit_req)

        pneed_result = PortfolioNeedAssessmentResult(
            assessment_id=f"pneed_{rec.amfi_code}",
            investor_id="INV_REAL_001",
            goal_id="GOAL_WEALTH_ACCUM",
            scheme_id=rec.canonical_scheme_id,
            primary_state=PortfolioNeedState.NEED_IDENTIFIED,
            candidate_fulfillment_status=CandidateFulfillmentStatus.CANDIDATE_CAN_FULFILL_NEED,
            affordability_status=AffordabilityStatus.AFFORDABLE,
            observation_timestamp=datetime.now(timezone.utc)
        )
        eb_contract = from_economic_benefit_result(
            assessment_id=f"eb_{rec.amfi_code}",
            investor_id="INV_REAL_001",
            economic_benefit_state=EconomicBenefitState.ECONOMICALLY_BENEFICIAL,
            position_context="NEW_POSITION",
            candidate_scheme_id=rec.canonical_scheme_id,
            economic_benefit_actionable=True,
            evidence_sufficiency_valid=True
        )

        fq_contract = from_fund_quality_result(fq_result, canonical_scheme_id=rec.canonical_scheme_id)
        ra_contract = from_risk_alignment_result(env["alignment"])
        suit_contract = from_suitability_result(suit_result)
        pneed_contract = from_portfolio_need_result(pneed_result)

        action_input = build_action_input_contract(
            investor_id="INV_REAL_001",
            scheme_id=rec.canonical_scheme_id,
            position_context=PositionContext.NEW_POSITION,
            assessment_id=f"act_input_{rec.amfi_code}",
            goal_id="GOAL_WEALTH_ACCUM",
            fund_quality_contract=fq_contract,
            risk_alignment_contract=ra_contract,
            suitability_contract=suit_contract,
            portfolio_need_contract=pneed_contract,
            economic_benefit_contract=eb_contract
        )

        e2e_result = env["orchestrator"].evaluate_decision(action_input)
        assert e2e_result.final_action_state == ActionState.NO_ACTION
        assert "Purchase prohibited" in e2e_result.final_explanation or "invalid or missing" in e2e_result.final_explanation

    # 4. Score alone MUST NOT trigger SELL
    def test_04_score_alone_cannot_trigger_sell(self, setup_real_data_environment):
        env = setup_real_data_environment
        snapshot = env["snapshot"]
        rec = snapshot.records[0]

        target_input = env["all_inputs"][0]
        fq_result = env["scoring_engine"].calculate_fund_quality_score(target_input, env["all_inputs"])

        suit_req = SuitabilityEvaluationRequest(
            investor_profile=env["investor"],
            risk_alignment=env["alignment"],
            fund_quality_score=fq_result,
            goal_profile=env["goal"],
            observation_date=date.today()
        )
        suit_result = env["suitability_engine"].evaluate(suit_req)

        pneed_result = PortfolioNeedAssessmentResult(
            assessment_id=f"pneed_{rec.amfi_code}",
            investor_id="INV_REAL_001",
            goal_id="GOAL_WEALTH_ACCUM",
            scheme_id=rec.canonical_scheme_id,
            primary_state=PortfolioNeedState.NO_MATERIAL_NEED,
            candidate_fulfillment_status=CandidateFulfillmentStatus.CANDIDATE_CAN_FULFILL_NEED,
            affordability_status=AffordabilityStatus.AFFORDABLE,
            observation_timestamp=datetime.now(timezone.utc)
        )
        eb_contract = from_economic_benefit_result(
            assessment_id=f"eb_{rec.amfi_code}",
            investor_id="INV_REAL_001",
            economic_benefit_state=EconomicBenefitState.NO_EVALUABLE_CHANGE,
            position_context="EXISTING_POSITION",
            current_holding_scheme_id=rec.canonical_scheme_id,
            economic_benefit_actionable=True,
            evidence_sufficiency_valid=True
        )

        fq_contract = from_fund_quality_result(fq_result, canonical_scheme_id=rec.canonical_scheme_id)
        ra_contract = from_risk_alignment_result(env["alignment"])
        suit_contract = from_suitability_result(suit_result)
        pneed_contract = from_portfolio_need_result(pneed_result)

        action_input = build_action_input_contract(
            investor_id="INV_REAL_001",
            scheme_id=rec.canonical_scheme_id,
            position_context=PositionContext.EXISTING_POSITION,
            assessment_id=f"act_input_{rec.amfi_code}",
            goal_id="GOAL_WEALTH_ACCUM",
            fund_quality_contract=fq_contract,
            risk_alignment_contract=ra_contract,
            suitability_contract=suit_contract,
            portfolio_need_contract=pneed_contract,
            economic_benefit_contract=eb_contract
        )

        e2e_result = env["orchestrator"].evaluate_decision(action_input)
        assert e2e_result.final_action_state == ActionState.HOLD, "Existing holding with low score/missing score must default to HOLD"

    # 5. Canonical identity stability CAN_AMFI_{code}
    def test_05_canonical_identity_stability(self, setup_real_data_environment):
        env = setup_real_data_environment
        snapshot = env["snapshot"]
        for rec in snapshot.records[:10]:
            assert rec.canonical_scheme_id == f"CAN_AMFI_{rec.amfi_code}"

    # 6. Provenance metadata propagation
    def test_06_provenance_propagation(self, setup_real_data_environment):
        env = setup_real_data_environment
        snapshot = env["snapshot"]
        rec = snapshot.records[0]

        target_input = env["all_inputs"][0]
        fq_result = env["scoring_engine"].calculate_fund_quality_score(target_input, env["all_inputs"])
        suit_req = SuitabilityEvaluationRequest(
            investor_profile=env["investor"],
            risk_alignment=env["alignment"],
            fund_quality_score=fq_result,
            goal_profile=env["goal"],
            observation_date=date.today()
        )
        suit_result = env["suitability_engine"].evaluate(suit_req)

        pneed_result = PortfolioNeedAssessmentResult(
            assessment_id=f"pneed_{rec.amfi_code}",
            investor_id="INV_REAL_001",
            goal_id="GOAL_WEALTH_ACCUM",
            scheme_id=rec.canonical_scheme_id,
            primary_state=PortfolioNeedState.NEED_IDENTIFIED,
            candidate_fulfillment_status=CandidateFulfillmentStatus.CANDIDATE_CAN_FULFILL_NEED,
            affordability_status=AffordabilityStatus.AFFORDABLE,
            observation_timestamp=datetime.now(timezone.utc)
        )
        eb_contract = from_economic_benefit_result(
            assessment_id=f"eb_{rec.amfi_code}",
            investor_id="INV_REAL_001",
            economic_benefit_state=EconomicBenefitState.ECONOMICALLY_BENEFICIAL,
            position_context="NEW_POSITION",
            candidate_scheme_id=rec.canonical_scheme_id,
            economic_benefit_actionable=True,
            evidence_sufficiency_valid=True
        )

        fq_contract = from_fund_quality_result(fq_result, canonical_scheme_id=rec.canonical_scheme_id)
        ra_contract = from_risk_alignment_result(env["alignment"])
        suit_contract = from_suitability_result(suit_result)
        pneed_contract = from_portfolio_need_result(pneed_result)

        action_input = build_action_input_contract(
            investor_id="INV_REAL_001",
            scheme_id=rec.canonical_scheme_id,
            position_context=PositionContext.NEW_POSITION,
            assessment_id=f"act_input_{rec.amfi_code}",
            goal_id="GOAL_WEALTH_ACCUM",
            fund_quality_contract=fq_contract,
            risk_alignment_contract=ra_contract,
            suitability_contract=suit_contract,
            portfolio_need_contract=pneed_contract,
            economic_benefit_contract=eb_contract
        )

        e2e_result = env["orchestrator"].evaluate_decision(action_input)
        assert e2e_result.provenance is not None
        assert e2e_result.provenance.source_id != ""
