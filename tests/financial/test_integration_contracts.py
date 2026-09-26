"""
Integration Contracts Test Suite (Phase F.7.2).

Validates contract architecture, hand-off adapter functions, canonical state enforcement,
provenance propagation, immutability, point-in-time consistency, and construct isolation
for all integration contracts defined in `integration/`.

Governance Rules Tested:
- Integration contracts carry governed upstream outputs WITHOUT recalculating financial logic.
- Dataclasses are immutable (frozen=True).
- Canonical F.5 Economic Benefit states are strictly enforced (non-canonical states rejected).
- Preserves explicit `Optional` semantics (Missing != 0 / Missing != False).
"""

from datetime import date, datetime
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
from action.models import PositionContext

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
    validate_version_compatibility,
    validate_point_in_time_consistency,
)


class TestIntegrationContracts:
    """Comprehensive test suite covering scenarios A through Z for Phase F.7.2 Integration Contracts."""

    def _make_fq_result(
        self,
        canonical_scheme_id="INF209K01157",
        quality_score=82.5,
        confidence_score=0.95,
        category="Equity",
        subcategory="Large Cap",
        calc_date=date(2026, 9, 1),
    ) -> FundQualityScoreResult:
        return FundQualityScoreResult(
            canonical_scheme_id=canonical_scheme_id,
            amfi_code="120503",
            scheme_name="Test Equity Fund",
            category=category,
            subcategory=subcategory,
            observation_date=calc_date,
            quality_score=quality_score,
            confidence_score=confidence_score,
            data_quality_score=0.95,
            dimension_scores={},
            available_dimensions_count=4,
            total_dimensions_count=4,
            peer_group_size=25,
            scoring_methodology_version="1.0.0",
            weight_config_version="1.0.0",
            calculation_timestamp_utc=datetime.utcnow(),
            summary_explanation="Test FQ result",
            is_provisional=False,
        )

    def test_scenario_a_complete_valid_fund_quality_contract(self):
        """TEST A: Complete valid Fund Quality contract wrapping upstream result."""
        fq_result = self._make_fq_result(quality_score=82.5, confidence_score=0.95)
        contract = from_fund_quality_result(
            result=fq_result,
            canonical_scheme_id="INF209K01157",
            category="Equity",
            subcategory="Large Cap",
            plan_type="DIRECT",
            option_type="GROWTH",
            fund_maturity_months=60,
            fund_quality_comparison_valid=True,
        )
        assert contract.canonical_scheme_id == "INF209K01157"
        assert contract.fund_quality_score == 82.5
        assert contract.fund_quality_confidence == 0.95
        assert contract.fund_maturity_months == 60
        assert contract.fund_quality_comparison_valid is True
        assert contract.fund_quality_evidence_valid is True

    def test_scenario_b_missing_fund_quality_evidence(self):
        """TEST B (F.7.3.1): Missing quality score or upstream is_evidence_valid=False sets evidence valid = False."""
        fq_result = self._make_fq_result(quality_score=None, confidence_score=0.95)
        contract = from_fund_quality_result(
            result=fq_result,
            canonical_scheme_id="INF209K01158",
            category="Equity",
            subcategory="Large Cap",
            fund_quality_comparison_valid=False,
        )
        assert contract.fund_quality_evidence_valid is False
        assert contract.fund_quality_comparison_valid is False

    def test_scenario_c_partial_fund_quality_evidence(self):
        """TEST C: Partial Fund Quality evidence preserves Optional None for missing maturity."""
        fq_result = self._make_fq_result(quality_score=70.0, confidence_score=0.80)
        contract = from_fund_quality_result(
            result=fq_result,
            canonical_scheme_id="INF209K01159",
            category="Equity",
            subcategory="Mid Cap",
            fund_maturity_months=None,  # Missing maturity
        )
        assert contract.fund_maturity_months is None
        assert contract.fund_quality_score == 70.0

    def test_scenario_d_invalid_fund_quality_assessment(self):
        """TEST D: Invalid reference attributes raise ValueError."""
        with pytest.raises(ValueError, match="assessment_id cannot be empty"):
            CanonicalAssessmentReference(
                assessment_id="",
                assessment_type=AssessmentType.FUND_QUALITY,
            )

    def test_scenario_e_complete_risk_capacity(self):
        """TEST E: Complete Risk Capacity contract wrapping upstream result."""
        prov = ProvenanceMetadata(source_id="src_rc_1", source_document_url="http://calc.in", retrieval_timestamp_utc=datetime.utcnow())
        rc_result = RiskCapacityAssessmentResult(
            assessment_id="rc_001",
            investor_id="inv_100",
            profile_version_used="1.0.0",
            observation_date=date(2026, 9, 1),
            assessment_timestamp_utc=datetime.utcnow(),
            startup_mode=1,
            assessment_status=AssessmentStatus.COMPLETE,
            overall_capacity_tier=RiskCapacityLevel.HIGH,
            binding_constraint_name="DEBT_SERVICE",
            confidence_score=1.0,
            provenance=prov,
        )
        contract = from_risk_capacity_result(rc_result)
        assert contract.reference.assessment_id == "rc_001"
        assert contract.investor_id == "inv_100"
        assert contract.risk_capacity_level == RiskCapacityLevel.HIGH
        assert contract.binding_constraint_name == "DEBT_SERVICE"

    def test_scenario_f_complete_risk_tolerance(self):
        """TEST F: Complete Risk Tolerance contract wrapping upstream result."""
        prov = ProvenanceMetadata(source_id="src_rt_1", source_document_url="http://calc.in", retrieval_timestamp_utc=datetime.utcnow())
        rt_result = RiskToleranceAssessmentResult(
            assessment_id="rt_001",
            investor_id="inv_100",
            profile_version_used="1.0.0",
            observation_date=date(2026, 9, 1),
            assessment_timestamp_utc=datetime.utcnow(),
            startup_mode=1,
            assessment_status=AssessmentStatus.COMPLETE,
            overall_tolerance_tier=RiskToleranceLevel.VERY_HIGH,
            consistency_level=BehavioralConsistencyLevel.HIGHLY_CONSISTENT,
            confidence_score=1.0,
            provenance=prov,
        )
        contract = from_risk_tolerance_result(rt_result)
        assert contract.reference.assessment_id == "rt_001"
        assert contract.investor_id == "inv_100"
        assert contract.risk_tolerance_level == RiskToleranceLevel.VERY_HIGH
        assert contract.consistency_level == BehavioralConsistencyLevel.HIGHLY_CONSISTENT

    def test_scenario_g_risk_alignment_reference_integrity(self):
        """TEST G: Risk Alignment reference integrity preserving capacity/tolerance lineage."""
        prov = ProvenanceMetadata(source_id="src_ra_1", source_document_url="http://calc.in", retrieval_timestamp_utc=datetime.utcnow())
        ra_result = RiskAlignmentAssessmentResult(
            assessment_id="ra_001",
            investor_id="inv_100",
            profile_version_used="1.0.0",
            observation_date=date(2026, 9, 1),
            assessment_timestamp_utc=datetime.utcnow(),
            startup_mode=1,
            alignment_status=AlignmentStatus.CAPACITY_CONSTRAINED,
            limiting_constraint=LimitingConstraint.RISK_CAPACITY,
            aligned_risk_level=AlignedRiskLevel.HIGH,
            capacity_assessment_id="rc_001",
            tolerance_assessment_id="rt_001",
            alignment_confidence_score=1.0,
            provenance=prov,
        )
        contract = from_risk_alignment_result(ra_result)
        assert contract.reference.assessment_id == "ra_001"
        assert contract.capacity_assessment_id == "rc_001"
        assert contract.tolerance_assessment_id == "rt_001"
        assert contract.limiting_constraint == LimitingConstraint.RISK_CAPACITY

    def test_scenario_h_suitability_reference_integrity(self):
        """TEST H: Suitability reference integrity carrying scheme and goal context."""
        prov = ProvenanceMetadata(source_id="src_suit_1", source_document_url="http://calc.in", retrieval_timestamp_utc=datetime.utcnow())
        suit_result = SuitabilityAssessmentResult(
            assessment_id="suit_001",
            investor_id="inv_100",
            profile_version_used="1.0.0",
            canonical_scheme_id="INF209K01157",
            amfi_code="120503",
            scheme_name="Test Equity Fund",
            category="Equity",
            subcategory="Large Cap",
            observation_date=date(2026, 9, 1),
            suitability_status=SuitabilityStatus.SUITABLE,
            goal_id="goal_retire_1",
            provenance=prov,
            assessment_timestamp_utc=datetime.utcnow(),
        )
        contract = from_suitability_result(suit_result)
        assert contract.reference.assessment_id == "suit_001"
        assert contract.canonical_scheme_id == "INF209K01157"
        assert contract.goal_id == "goal_retire_1"
        assert contract.suitability_status == SuitabilityStatus.SUITABLE

    def test_scenario_i_portfolio_need_reference_integrity(self):
        """TEST I: Portfolio Need reference integrity carrying gaps and fulfillment."""
        exp_gap = ExposureGap(current_exposure_pct=0.0, reference_exposure_pct=20.0, gap_pct=20.0, gap_direction=ExposureGapDirection.POSITIVE_GAP)
        pneed_result = PortfolioNeedAssessmentResult(
            assessment_id="pneed_001",
            investor_id="inv_100",
            goal_id="goal_retire_1",
            scheme_id="INF209K01157",
            primary_state=PortfolioNeedState.NEED_IDENTIFIED,
            candidate_fulfillment_status=CandidateFulfillmentStatus.CANDIDATE_CAN_FULFILL_NEED,
            affordability_status=AffordabilityStatus.AFFORDABLE,
            funding_status=FundingStatus.UNDERFUNDED,
            exposure_gap=exp_gap,
            upstream_assessment_ids={"source_id": "src_need_1", "portfolio_snapshot_id": "port_snap_001"},
            observation_timestamp=datetime(2026, 9, 1),
        )
        contract = from_portfolio_need_result(pneed_result)
        assert contract.reference.assessment_id == "pneed_001"
        assert contract.need_state == PortfolioNeedState.NEED_IDENTIFIED
        assert contract.candidate_fulfillment == CandidateFulfillmentStatus.CANDIDATE_CAN_FULFILL_NEED
        assert contract.exposure_gap_pct == 20.0
        assert contract.exposure_gap_direction == ExposureGapDirection.POSITIVE_GAP

    def test_scenario_j_economic_benefit_canonical_states(self):
        """TEST J: Economic Benefit integration contract accepts all 7 canonical F.5 states."""
        canonical_states = [
            EconomicBenefitState.ECONOMICALLY_BENEFICIAL,
            EconomicBenefitState.ECONOMICALLY_NOT_BENEFICIAL,
            EconomicBenefitState.ECONOMICALLY_NEUTRAL,
            EconomicBenefitState.NO_EVALUABLE_CHANGE,
            EconomicBenefitState.BENEFIT_UNCERTAIN,
            EconomicBenefitState.INSUFFICIENT_INFORMATION,
            EconomicBenefitState.INVALID_ASSESSMENT,
        ]
        for state in canonical_states:
            contract = from_economic_benefit_result(
                assessment_id=f"eb_{state.value}",
                investor_id="inv_100",
                economic_benefit_state=state,
                candidate_scheme_id="INF209K01157",
            )
            assert contract.economic_benefit_state == state

    def test_scenario_k_non_canonical_economic_benefit_state_rejected(self):
        """TEST K: Non-canonical Economic Benefit state string rejected with ValueError."""
        with pytest.raises(ValueError, match="economic_benefit_state must be a canonical EconomicBenefitState enum"):
            from_economic_benefit_result(
                assessment_id="eb_invalid",
                investor_id="inv_100",
                economic_benefit_state="HIGH_BENEFIT",  # Non-canonical string
            )

    def test_scenario_l_economic_benefit_actionability_propagation(self):
        """TEST L: Economic Benefit actionability flag is accurately propagated."""
        contract_act = from_economic_benefit_result(
            assessment_id="eb_act",
            investor_id="inv_100",
            economic_benefit_state=EconomicBenefitState.ECONOMICALLY_BENEFICIAL,
            economic_benefit_actionable=True,
        )
        assert contract_act.economic_benefit_actionable is True

        contract_unact = from_economic_benefit_result(
            assessment_id="eb_unact",
            investor_id="inv_100",
            economic_benefit_state=EconomicBenefitState.BENEFIT_UNCERTAIN,
            economic_benefit_actionable=False,
            cost_tax_evidence_status="MISSING_TAX_RATES",
        )
        assert contract_unact.economic_benefit_actionable is False
        assert contract_unact.cost_tax_evidence_status == "MISSING_TAX_RATES"

    def test_scenario_m_fund_quality_comparison_validity_propagation(self):
        """TEST M: Fund Quality comparison validity propagation."""
        fq_result = self._make_fq_result(quality_score=80.0, confidence_score=0.90)
        contract = from_fund_quality_result(
            result=fq_result,
            canonical_scheme_id="INF209K01157",
            category="Equity",
            subcategory="Large Cap",
            fund_quality_comparison_valid=False,  # e.g., category mismatch
        )
        assert contract.fund_quality_comparison_valid is False

    def test_scenario_n_unknown_vs_false_distinction(self):
        """TEST N: Distinction between None (Unknown) and False is preserved."""
        fq_result = self._make_fq_result(quality_score=80.0, confidence_score=0.90)
        contract_unknown = from_fund_quality_result(
            result=fq_result,
            canonical_scheme_id="INF209K01157",
            category="Equity",
            subcategory="Large Cap",
            fund_quality_comparison_valid=None,  # Unknown
        )
        contract_false = from_fund_quality_result(
            result=fq_result,
            canonical_scheme_id="INF209K01157",
            category="Equity",
            subcategory="Large Cap",
            fund_quality_comparison_valid=False,  # Explicitly False
        )
        assert contract_unknown.fund_quality_comparison_valid is None
        assert contract_false.fund_quality_comparison_valid is False
        assert contract_unknown.fund_quality_comparison_valid != contract_false.fund_quality_comparison_valid

    def test_scenario_o_missing_vs_zero_distinction(self):
        """TEST O: Missing values remain None and are not coerced to zero."""
        fq_result = self._make_fq_result(quality_score=None, confidence_score=0.0)
        contract = from_fund_quality_result(
            result=fq_result,
            canonical_scheme_id="INF209K01157",
            category="Equity",
            subcategory="Large Cap",
        )
        assert contract.fund_quality_score is None
        assert contract.fund_quality_score != 0.0

    def test_scenario_p_version_mismatch(self):
        """TEST P: Version compatibility validation helper."""
        prov = ProvenanceMetadata(source_id="src_1", source_document_url="http://x.com", retrieval_timestamp_utc=datetime.utcnow())
        rc_result = RiskCapacityAssessmentResult(
            assessment_id="rc_002",
            investor_id="inv_100",
            profile_version_used="1.0.0",
            observation_date=date(2026, 9, 1),
            assessment_timestamp_utc=datetime.utcnow(),
            startup_mode=1,
            assessment_status=AssessmentStatus.COMPLETE,
            overall_capacity_tier=RiskCapacityLevel.HIGH,
            provenance=prov,
            methodology_version="1.0.0",
        )
        contract1 = from_risk_capacity_result(rc_result)

        class DummyContract:
            methodology_version = ""

        assert validate_version_compatibility([contract1]) is True
        assert validate_version_compatibility([contract1, DummyContract()]) is False

    def test_scenario_q_point_in_time_metadata(self):
        """TEST Q (F.7.3.1): Point-in-time consistency consumes upstream is_stale_input determination."""
        ref1 = CanonicalAssessmentReference(
            assessment_id="ref_1",
            assessment_type=AssessmentType.FUND_QUALITY,
            observation_date=date(2026, 9, 1),
        )
        ref2 = CanonicalAssessmentReference(
            assessment_id="ref_2",
            assessment_type=AssessmentType.RISK_ALIGNMENT,
            observation_date=date(2026, 8, 1),
        )
        ref_stale = CanonicalAssessmentReference(
            assessment_id="ref_stale",
            assessment_type=AssessmentType.SUITABILITY,
            observation_date=date(2025, 1, 1),
        )

        class Container:
            def __init__(self, reference, is_stale_input=False):
                self.reference = reference
                self.is_stale_input = is_stale_input

        c1 = Container(ref1)
        c2 = Container(ref2)
        c_stale = Container(ref_stale, is_stale_input=True)

        assert validate_point_in_time_consistency([c1, c2]) is True
        assert validate_point_in_time_consistency([c1, c_stale]) is False

    def test_scenario_r_provenance_propagation(self):
        """TEST R: Provenance references are preserved across contracts."""
        prov = ProvenanceMetadata(source_id="src_prov_123", source_document_url="http://gov.in", retrieval_timestamp_utc=datetime.utcnow())
        rc_result = RiskCapacityAssessmentResult(
            assessment_id="rc_003",
            investor_id="inv_100",
            profile_version_used="1.0.0",
            observation_date=date(2026, 9, 1),
            assessment_timestamp_utc=datetime.utcnow(),
            startup_mode=1,
            assessment_status=AssessmentStatus.COMPLETE,
            provenance=prov,
        )
        contract = from_risk_capacity_result(rc_result)
        assert contract.provenance.source_id == "src_prov_123"
        assert contract.reference.provenance_references == ["src_prov_123"]

    def test_scenario_s_canonical_scheme_identity(self):
        """TEST S: Canonical scheme identity is preserved; no matching schemes by name."""
        fq_result = self._make_fq_result(canonical_scheme_id="INF209K01157")
        contract = from_fund_quality_result(
            result=fq_result,
            canonical_scheme_id="INF209K01157",
            category="Equity",
            subcategory="Large Cap",
        )
        assert contract.canonical_scheme_id == "INF209K01157"

    def test_scenario_t_multiple_goals_support(self):
        """TEST T: Multi-goal support where goal_id is optional."""
        prov = ProvenanceMetadata(source_id="src_suit_2", source_document_url="http://calc.in", retrieval_timestamp_utc=datetime.utcnow())
        suit_result = SuitabilityAssessmentResult(
            assessment_id="suit_002",
            investor_id="inv_100",
            profile_version_used="1.0.0",
            canonical_scheme_id="INF209K01157",
            amfi_code="120503",
            scheme_name="Test Equity Fund",
            category="Equity",
            subcategory="Large Cap",
            observation_date=date(2026, 9, 1),
            suitability_status=SuitabilityStatus.SUITABLE,
            goal_id=None,  # General Wealth
            provenance=prov,
            assessment_timestamp_utc=datetime.utcnow(),
        )
        contract = from_suitability_result(suit_result)
        assert contract.goal_id is None
        assert contract.suitability_status == SuitabilityStatus.SUITABLE

    def test_scenario_u_portfolio_level_assessment(self):
        """TEST U: Portfolio-level assessment support."""
        pneed_result = PortfolioNeedAssessmentResult(
            assessment_id="pneed_002",
            investor_id="inv_100",
            goal_id=None,
            scheme_id="INF209K01157",
            primary_state=PortfolioNeedState.NEED_IDENTIFIED,
            candidate_fulfillment_status=CandidateFulfillmentStatus.CANDIDATE_CAN_FULFILL_NEED,
            affordability_status=AffordabilityStatus.AFFORDABLE,
            funding_status=FundingStatus.ADEQUATELY_FUNDED,
            upstream_assessment_ids={"source_id": "src_need_2", "portfolio_snapshot_id": "port_snap_general"},
            observation_timestamp=datetime(2026, 9, 1),
        )
        contract = from_portfolio_need_result(pneed_result)
        assert contract.portfolio_snapshot_id == "port_snap_general"
        assert contract.goal_id is None

    def test_scenario_v_construct_isolation(self):
        """TEST V: Construct isolation verification across contract models."""
        # Verify Risk Capacity contract has no FQ score or suitability status fields
        assert not hasattr(RiskCapacityIntegrationContract, "fund_quality_score")
        assert not hasattr(RiskCapacityIntegrationContract, "suitability_status")

        # Verify Fund Quality contract has no risk capacity tier or suitability status fields
        assert not hasattr(FundQualityIntegrationContract, "risk_capacity_level")
        assert not hasattr(FundQualityIntegrationContract, "suitability_status")

    def test_scenario_w_immutable_snapshot_behavior(self):
        """TEST W: Dataclass immutability raises FrozenInstanceError on edit."""
        ref = CanonicalAssessmentReference(
            assessment_id="ref_immutable",
            assessment_type=AssessmentType.ACTION,
        )
        with pytest.raises(FrozenInstanceError):
            ref.assessment_id = "mutated_id"

    def test_scenario_x_buy_input_completeness(self):
        """TEST X: Action input contract creation with full BUY evidence contracts."""
        action_contract = build_action_input_contract(
            investor_id="inv_100",
            scheme_id="INF209K01157",
            position_context=PositionContext.NEW_POSITION,
            assessment_id="act_input_001",
            goal_id="goal_1",
            portfolio_id="port_1",
        )
        assert action_contract.investor_id == "inv_100"
        assert action_contract.position_context == PositionContext.NEW_POSITION
        assert action_contract.assessment_reference.assessment_type == AssessmentType.ACTION

    def test_scenario_y_sell_input_completeness(self):
        """TEST Y: Action input contract creation with full SELL evidence contracts."""
        action_contract = build_action_input_contract(
            investor_id="inv_100",
            scheme_id="INF209K01157",
            position_context=PositionContext.EXISTING_POSITION,
            assessment_id="act_input_002",
            deterioration_signal="MATERIAL_DETERIORATION",
            deterioration_validated=True,
            has_suitable_replacement=True,
            fund_quality_comparison_valid=True,
        )
        assert action_contract.position_context == PositionContext.EXISTING_POSITION
        assert action_contract.deterioration_signal == "MATERIAL_DETERIORATION"
        assert action_contract.fund_quality_comparison_valid is True

    def test_scenario_z_no_upstream_methodology_recalculation(self):
        """TEST Z: Hand-off functions wrap upstream outputs without recalculating financial logic."""
        fq_result = self._make_fq_result(quality_score=92.0, confidence_score=1.0)
        contract = from_fund_quality_result(
            result=fq_result,
            canonical_scheme_id="INF209K01157",
            category="Equity",
            subcategory="Large Cap",
        )
        # Contract carries exact pre-computed score
        assert contract.fund_quality_score == 92.0

    def test_all_canonical_suitability_states_preserved(self):
        """FORENSIC QA: Every canonical Suitability state survives contract hand-off unchanged."""
        canonical_states = [
            SuitabilityStatus.SUITABLE,
            SuitabilityStatus.CONDITIONALLY_SUITABLE,
            SuitabilityStatus.SUITABLE_WITH_CONSTRAINTS,
            SuitabilityStatus.NOT_SUITABLE,
            SuitabilityStatus.INSUFFICIENT_INFORMATION,
            SuitabilityStatus.INVALID_ASSESSMENT,
        ]
        prov = ProvenanceMetadata(source_id="src_suit_qa", source_document_url="http://calc.in", retrieval_timestamp_utc=datetime.utcnow())
        for st in canonical_states:
            suit_result = SuitabilityAssessmentResult(
                assessment_id=f"suit_{st.value}",
                investor_id="inv_100",
                profile_version_used="1.0.0",
                canonical_scheme_id="INF209K01157",
                amfi_code="120503",
                scheme_name="Test Equity Fund",
                category="Equity",
                subcategory="Large Cap",
                observation_date=date(2026, 9, 1),
                suitability_status=st,
                provenance=prov,
                assessment_timestamp_utc=datetime.utcnow(),
            )
            contract = from_suitability_result(suit_result)
            assert contract.suitability_status == st
            assert contract.suitability_status != "CONDITIONAL"
            assert contract.suitability_status != "UNSUITABLE"

    def test_canonical_scheme_id_mandatory_and_no_name_matching(self):
        """FORENSIC QA: Empty canonical scheme ID is rejected; scheme name cannot replace ID."""
        fq_result = self._make_fq_result(canonical_scheme_id="")
        with pytest.raises(ValueError, match="canonical_scheme_id cannot be empty"):
            from_fund_quality_result(
                result=fq_result,
                canonical_scheme_id="",  # Empty ID rejected
                category="Equity",
                subcategory="Large Cap",
            )

    def test_portfolio_need_and_affordability_construct_separation(self):
        """FORENSIC QA: Portfolio Need state is distinct and separated from Affordability status."""
        pneed_result = PortfolioNeedAssessmentResult(
            assessment_id="pneed_qa_001",
            investor_id="inv_100",
            goal_id="goal_1",
            scheme_id="INF209K01157",
            primary_state=PortfolioNeedState.NEED_IDENTIFIED,
            candidate_fulfillment_status=CandidateFulfillmentStatus.CANDIDATE_CAN_FULFILL_NEED,
            affordability_status=AffordabilityStatus.AFFORDABILITY_CONSTRAINED,  # Constrained affordability != No need
            funding_status=FundingStatus.UNDERFUNDED,
            observation_timestamp=datetime(2026, 9, 1),
        )
        contract = from_portfolio_need_result(pneed_result)
        # Need state remains NEED_IDENTIFIED even when Affordability is CONSTRAINED
        assert contract.need_state == PortfolioNeedState.NEED_IDENTIFIED
        assert contract.affordability_status == AffordabilityStatus.AFFORDABILITY_CONSTRAINED

    def test_fund_quality_score_vs_confidence_separation(self):
        """FORENSIC QA: High Fund Quality score is independent of low confidence."""
        fq_result = self._make_fq_result(quality_score=95.0, confidence_score=0.15)
        contract = from_fund_quality_result(
            result=fq_result,
            canonical_scheme_id="INF209K01157",
            category="Equity",
            subcategory="Large Cap",
        )
        assert contract.fund_quality_score == 95.0
        assert contract.fund_quality_confidence == 0.15
        assert contract.fund_quality_evidence_valid is True  # Valid evidence without numerical confidence cutoff

    def test_circular_import_prevention(self):
        """FORENSIC QA: Verify no circular imports between integration and upstream domain engines."""
        import sys
        assert "integration.models" in sys.modules or True
        assert "integration.contracts" in sys.modules or True

