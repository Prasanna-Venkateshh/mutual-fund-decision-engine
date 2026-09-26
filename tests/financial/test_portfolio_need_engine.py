"""
Unit tests for Portfolio Need Engine (Phase F.4.4 / F.4.4.1 Audit).

Tests deterministic decision logic and governance invariants strictly according to:
- docs/phase_f4_portfolio_need_specification.md
- docs/phase_f4_3_portfolio_need_decision_logic_specification.md
- docs/phase_f4_3_1_portfolio_need_governance_correction.md
- docs/phase_f4_3_2_candidate_fulfillment_semantic_governance_correction.md
"""

import pytest
from datetime import datetime, date, timezone

from portfolio.need_models import (
    GoalFundingSnapshot,
    PortfolioExposureSnapshot,
    AllocationContext,
    ExposureGap,
    AffordabilityContext,
    PortfolioLookThroughContext,
    FundCandidateContext,
    MultiGoalContext,
    GeneralWealthContext,
    PortfolioNeedState,
    CandidateFulfillmentStatus,
    AffordabilityStatus,
    ExposureGapDirection,
    FundingStatus,
)
from portfolio.need_engine import PortfolioNeedEngine
from models.suitability_assessment import SuitabilityAssessmentResult, SuitabilityStatus


@pytest.fixture
def engine():
    return PortfolioNeedEngine()


@pytest.fixture
def sample_goal():
    return GoalFundingSnapshot(
        goal_id="goal_101",
        investor_id="inv_001",
        target_amount=1000000.0,
        current_corpus=600000.0,
        funding_status=FundingStatus.UNDERFUNDED,
        observation_date=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_portfolio():
    return PortfolioExposureSnapshot(
        portfolio_snapshot_id="ps_001",
        investor_id="inv_001",
        holding_ids=["h1", "h2"],
        canonical_scheme_ids=["scheme_a", "scheme_b"],
        observation_date=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_allocation_positive():
    return AllocationContext(
        exposure_gap=ExposureGap(
            current_exposure_pct=0.20,
            reference_exposure_pct=0.40,
            gap_pct=0.20,
            gap_direction=ExposureGapDirection.POSITIVE_GAP,
            observation_date=datetime.now(timezone.utc),
        )
    )


@pytest.fixture
def sample_allocation_negative():
    return AllocationContext(
        exposure_gap=ExposureGap(
            current_exposure_pct=0.50,
            reference_exposure_pct=0.30,
            gap_pct=-0.20,
            gap_direction=ExposureGapDirection.NEGATIVE_GAP,
            observation_date=datetime.now(timezone.utc),
        )
    )


@pytest.fixture
def sample_allocation_balanced():
    return AllocationContext(
        exposure_gap=ExposureGap(
            current_exposure_pct=0.30,
            reference_exposure_pct=0.30,
            gap_pct=0.0,
            gap_direction=ExposureGapDirection.BALANCED_EXPOSURE,
            observation_date=datetime.now(timezone.utc),
        )
    )


@pytest.fixture
def suitable_result():
    return SuitabilityAssessmentResult(
        assessment_id="suit_001",
        investor_id="inv_001",
        profile_version_used="v1",
        canonical_scheme_id="scheme_cand",
        amfi_code="123456",
        scheme_name="Candidate Scheme",
        category="Equity",
        subcategory="Large Cap",
        observation_date=date.today(),
        suitability_status=SuitabilityStatus.SUITABLE,
        suitability_confidence_score=0.90,
        assessment_timestamp_utc=datetime.now(timezone.utc),
        methodology_version="F.3.4.4",
        rule_version="1.0.0",
    )


@pytest.fixture
def unsuitable_result():
    return SuitabilityAssessmentResult(
        assessment_id="suit_002",
        investor_id="inv_001",
        profile_version_used="v1",
        canonical_scheme_id="scheme_cand",
        amfi_code="123456",
        scheme_name="Candidate Scheme",
        category="Equity",
        subcategory="Small Cap",
        observation_date=date.today(),
        suitability_status=SuitabilityStatus.NOT_SUITABLE,
        suitability_confidence_score=0.90,
        assessment_timestamp_utc=datetime.now(timezone.utc),
        methodology_version="F.3.4.4",
        rule_version="1.0.0",
    )


# --- PRIMARY STATES (1-5) ---

def test_01_positive_gap_yields_need_identified(engine, sample_goal, sample_portfolio, sample_allocation_positive):
    res = engine.evaluate_need(
        investor_id="inv_001",
        goal_snapshot=sample_goal,
        portfolio_snapshot=sample_portfolio,
        allocation_context=sample_allocation_positive,
    )
    assert res.primary_state == PortfolioNeedState.NEED_IDENTIFIED
    assert "ALLOCATION_GAP_PRESENT" in res.contextual_flags


def test_02_negative_gap_yields_excess_exposure(engine, sample_goal, sample_portfolio, sample_allocation_negative):
    res = engine.evaluate_need(
        investor_id="inv_001",
        goal_snapshot=sample_goal,
        portfolio_snapshot=sample_portfolio,
        allocation_context=sample_allocation_negative,
    )
    assert res.primary_state == PortfolioNeedState.EXCESS_EXPOSURE


def test_03_balanced_exposure_yields_no_material_need(engine, sample_goal, sample_portfolio, sample_allocation_balanced):
    res = engine.evaluate_need(
        investor_id="inv_001",
        goal_snapshot=sample_goal,
        portfolio_snapshot=sample_portfolio,
        allocation_context=sample_allocation_balanced,
    )
    assert res.primary_state == PortfolioNeedState.NO_MATERIAL_NEED


def test_04_missing_mandatory_inputs_yields_insufficient_information(engine):
    res = engine.evaluate_need(investor_id="inv_001")
    assert res.primary_state == PortfolioNeedState.INSUFFICIENT_INFORMATION


def test_05_invalid_input_yields_invalid_assessment(engine, sample_goal):
    res = engine.evaluate_need(investor_id="", goal_snapshot=sample_goal)
    assert res.primary_state == PortfolioNeedState.INVALID_ASSESSMENT


# --- CANDIDATE FULFILLMENT (6-10) ---

def test_06_suitable_and_capable_candidate_can_fulfill(engine, sample_goal, sample_portfolio, sample_allocation_positive, suitable_result):
    cand = FundCandidateContext(
        canonical_scheme_id="scheme_cand",
        suitability_result=suitable_result,
        is_capable_of_fulfilling_need=True,
    )
    res = engine.evaluate_need(
        investor_id="inv_001",
        goal_snapshot=sample_goal,
        portfolio_snapshot=sample_portfolio,
        allocation_context=sample_allocation_positive,
        candidate_context=cand,
    )
    assert res.primary_state == PortfolioNeedState.NEED_IDENTIFIED
    assert res.candidate_fulfillment_status == CandidateFulfillmentStatus.CANDIDATE_CAN_FULFILL_NEED


def test_07_unsuitable_candidate_cannot_fulfill(engine, sample_goal, sample_portfolio, sample_allocation_positive, unsuitable_result):
    cand = FundCandidateContext(
        canonical_scheme_id="scheme_cand",
        suitability_result=unsuitable_result,
        is_capable_of_fulfilling_need=True,
    )
    res = engine.evaluate_need(
        investor_id="inv_001",
        goal_snapshot=sample_goal,
        portfolio_snapshot=sample_portfolio,
        allocation_context=sample_allocation_positive,
        candidate_context=cand,
    )
    assert res.primary_state == PortfolioNeedState.NEED_IDENTIFIED
    assert res.candidate_fulfillment_status == CandidateFulfillmentStatus.CANDIDATE_CANNOT_FULFILL_NEED
    assert "CANDIDATE_UNSUITABLE" in res.contextual_flags


def test_08_suitable_wrong_asset_class_cannot_fulfill(engine, sample_goal, sample_portfolio, sample_allocation_positive, suitable_result):
    cand = FundCandidateContext(
        canonical_scheme_id="scheme_cand",
        suitability_result=suitable_result,
        is_capable_of_fulfilling_need=False,
    )
    res = engine.evaluate_need(
        investor_id="inv_001",
        goal_snapshot=sample_goal,
        portfolio_snapshot=sample_portfolio,
        allocation_context=sample_allocation_positive,
        candidate_context=cand,
    )
    assert res.primary_state == PortfolioNeedState.NEED_IDENTIFIED
    assert res.candidate_fulfillment_status == CandidateFulfillmentStatus.CANDIDATE_CANNOT_FULFILL_NEED
    assert "CANDIDATE_NOT_CAPABLE_OF_FULFILLING_NEED" in res.contextual_flags


def test_09_unknown_capability_yields_fulfillment_unknown(engine, sample_goal, sample_portfolio, sample_allocation_positive, suitable_result):
    cand = FundCandidateContext(
        canonical_scheme_id="scheme_cand",
        suitability_result=suitable_result,
        is_capable_of_fulfilling_need=None,
    )
    res = engine.evaluate_need(
        investor_id="inv_001",
        goal_snapshot=sample_goal,
        portfolio_snapshot=sample_portfolio,
        allocation_context=sample_allocation_positive,
        candidate_context=cand,
    )
    assert res.candidate_fulfillment_status == CandidateFulfillmentStatus.CANDIDATE_FULFILLMENT_UNKNOWN


def test_10_unknown_capability_never_defaults_to_capable(engine, sample_goal, sample_portfolio, sample_allocation_positive):
    cand = FundCandidateContext(
        canonical_scheme_id="scheme_cand",
        is_capable_of_fulfilling_need=None,
    )
    res = engine.evaluate_need(
        investor_id="inv_001",
        goal_snapshot=sample_goal,
        portfolio_snapshot=sample_portfolio,
        allocation_context=sample_allocation_positive,
        candidate_context=cand,
    )
    assert res.candidate_fulfillment_status != CandidateFulfillmentStatus.CANDIDATE_CAN_FULFILL_NEED


# --- AFFORDABILITY (11-12) ---

def test_11_need_and_affordability_constrained(engine, sample_goal, sample_portfolio, sample_allocation_positive):
    aff = AffordabilityContext(affordability_status=AffordabilityStatus.AFFORDABILITY_CONSTRAINED)
    res = engine.evaluate_need(
        investor_id="inv_001",
        goal_snapshot=sample_goal,
        portfolio_snapshot=sample_portfolio,
        allocation_context=sample_allocation_positive,
        affordability_context=aff,
    )
    assert res.primary_state == PortfolioNeedState.NEED_IDENTIFIED
    assert res.affordability_status == AffordabilityStatus.AFFORDABILITY_CONSTRAINED
    assert "AFFORDABILITY_CONSTRAINED" in res.contextual_flags


def test_12_need_and_affordability_unknown(engine, sample_goal, sample_portfolio, sample_allocation_positive):
    aff = AffordabilityContext(affordability_status=AffordabilityStatus.AFFORDABILITY_STATUS_UNKNOWN)
    res = engine.evaluate_need(
        investor_id="inv_001",
        goal_snapshot=sample_goal,
        portfolio_snapshot=sample_portfolio,
        allocation_context=sample_allocation_positive,
        affordability_context=aff,
    )
    assert res.primary_state == PortfolioNeedState.NEED_IDENTIFIED
    assert res.affordability_status == AffordabilityStatus.AFFORDABILITY_STATUS_UNKNOWN
    assert "AFFORDABILITY_STATUS_UNKNOWN" in res.contextual_flags


# --- CONCENTRATION & OVERLAP (13-15) ---

def test_13_balanced_plus_concentration_never_excess_exposure(engine, sample_goal, sample_portfolio, sample_allocation_balanced):
    look = PortfolioLookThroughContext(is_category_overexposed=True)
    res = engine.evaluate_need(
        investor_id="inv_001",
        goal_snapshot=sample_goal,
        portfolio_snapshot=sample_portfolio,
        allocation_context=sample_allocation_balanced,
        look_through_context=look,
    )
    assert res.primary_state == PortfolioNeedState.NO_MATERIAL_NEED
    assert res.primary_state != PortfolioNeedState.EXCESS_EXPOSURE
    assert "CATEGORY_OVEREXPOSED" in res.contextual_flags


def test_14_positive_gap_plus_concentration_remains_need_identified(engine, sample_goal, sample_portfolio, sample_allocation_positive):
    look = PortfolioLookThroughContext(is_category_overexposed=True)
    res = engine.evaluate_need(
        investor_id="inv_001",
        goal_snapshot=sample_goal,
        portfolio_snapshot=sample_portfolio,
        allocation_context=sample_allocation_positive,
        look_through_context=look,
    )
    assert res.primary_state == PortfolioNeedState.NEED_IDENTIFIED
    assert "CATEGORY_OVEREXPOSED" in res.contextual_flags


def test_15_negative_gap_plus_concentration_yields_excess_exposure(engine, sample_goal, sample_portfolio, sample_allocation_negative):
    look = PortfolioLookThroughContext(is_category_overexposed=True)
    res = engine.evaluate_need(
        investor_id="inv_001",
        goal_snapshot=sample_goal,
        portfolio_snapshot=sample_portfolio,
        allocation_context=sample_allocation_negative,
        look_through_context=look,
    )
    assert res.primary_state == PortfolioNeedState.EXCESS_EXPOSURE


# --- SEPARATION INVARIANTS (16-25) ---

def test_16_high_fund_quality_cannot_create_need(engine, sample_goal, sample_portfolio, sample_allocation_balanced):
    cand = FundCandidateContext(
        canonical_scheme_id="scheme_high_q",
        fund_quality_assessment_id="fq_99",
    )
    res = engine.evaluate_need(
        investor_id="inv_001",
        goal_snapshot=sample_goal,
        portfolio_snapshot=sample_portfolio,
        allocation_context=sample_allocation_balanced,
        candidate_context=cand,
    )
    assert res.primary_state == PortfolioNeedState.NO_MATERIAL_NEED


def test_17_low_fund_quality_cannot_independently_create_need(engine, sample_goal, sample_portfolio, sample_allocation_balanced):
    cand = FundCandidateContext(
        canonical_scheme_id="scheme_low_q",
        fund_quality_assessment_id="fq_10",
    )
    res = engine.evaluate_need(
        investor_id="inv_001",
        goal_snapshot=sample_goal,
        portfolio_snapshot=sample_portfolio,
        allocation_context=sample_allocation_balanced,
        candidate_context=cand,
    )
    assert res.primary_state == PortfolioNeedState.NO_MATERIAL_NEED


def test_18_suitability_cannot_erase_underlying_need(engine, sample_goal, sample_portfolio, sample_allocation_positive, unsuitable_result):
    cand = FundCandidateContext(
        canonical_scheme_id="scheme_cand",
        suitability_result=unsuitable_result,
        is_capable_of_fulfilling_need=True,
    )
    res = engine.evaluate_need(
        investor_id="inv_001",
        goal_snapshot=sample_goal,
        portfolio_snapshot=sample_portfolio,
        allocation_context=sample_allocation_positive,
        candidate_context=cand,
    )
    assert res.primary_state == PortfolioNeedState.NEED_IDENTIFIED
    assert res.primary_state != PortfolioNeedState.NO_MATERIAL_NEED


def test_19_candidate_inability_cannot_erase_underlying_need(engine, sample_goal, sample_portfolio, sample_allocation_positive, suitable_result):
    cand = FundCandidateContext(
        canonical_scheme_id="scheme_cand",
        suitability_result=suitable_result,
        is_capable_of_fulfilling_need=False,
    )
    res = engine.evaluate_need(
        investor_id="inv_001",
        goal_snapshot=sample_goal,
        portfolio_snapshot=sample_portfolio,
        allocation_context=sample_allocation_positive,
        candidate_context=cand,
    )
    assert res.primary_state == PortfolioNeedState.NEED_IDENTIFIED


def test_20_candidate_fulfillment_cannot_create_buy_action(engine, sample_goal, sample_portfolio, sample_allocation_positive, suitable_result):
    cand = FundCandidateContext(
        canonical_scheme_id="scheme_cand",
        suitability_result=suitable_result,
        is_capable_of_fulfilling_need=True,
    )
    res = engine.evaluate_need(
        investor_id="inv_001",
        goal_snapshot=sample_goal,
        portfolio_snapshot=sample_portfolio,
        allocation_context=sample_allocation_positive,
        candidate_context=cand,
    )
    assert not hasattr(res, "action")
    assert not hasattr(res, "recommendation")
    assert "BUY" not in str(res.primary_state)


def test_21_portfolio_need_cannot_create_action_enum(engine, sample_goal, sample_portfolio, sample_allocation_negative):
    res = engine.evaluate_need(
        investor_id="inv_001",
        goal_snapshot=sample_goal,
        portfolio_snapshot=sample_portfolio,
        allocation_context=sample_allocation_negative,
    )
    assert res.primary_state == PortfolioNeedState.EXCESS_EXPOSURE
    assert "SELL" not in res.primary_state.value
    assert "REBALANCE" not in res.primary_state.value


def test_22_confidence_does_not_silently_change_need_state(engine, sample_goal, sample_portfolio):
    alloc_low_conf = AllocationContext(
        exposure_gap=ExposureGap(
            gap_direction=ExposureGapDirection.POSITIVE_GAP,
        )
    )
    look_low_conf = PortfolioLookThroughContext(look_through_confidence=0.3)
    res = engine.evaluate_need(
        investor_id="inv_001",
        goal_snapshot=sample_goal,
        portfolio_snapshot=sample_portfolio,
        allocation_context=alloc_low_conf,
        look_through_context=look_low_conf,
    )
    assert res.primary_state == PortfolioNeedState.NEED_IDENTIFIED
    assert res.confidence_score < 1.0


def test_23_funding_status_and_allocation_status_remain_separate(engine, sample_portfolio, sample_allocation_balanced):
    goal_underfunded = GoalFundingSnapshot(
        goal_id="goal_101",
        investor_id="inv_001",
        target_amount=1000000.0,
        current_corpus=100000.0,
        funding_status=FundingStatus.UNDERFUNDED,
    )
    res = engine.evaluate_need(
        investor_id="inv_001",
        goal_snapshot=goal_underfunded,
        portfolio_snapshot=sample_portfolio,
        allocation_context=sample_allocation_balanced,
    )
    assert res.funding_status == FundingStatus.UNDERFUNDED
    assert res.allocation_status == ExposureGapDirection.BALANCED_EXPOSURE
    assert res.primary_state == PortfolioNeedState.NO_MATERIAL_NEED


def test_24_general_wealth_alone_cannot_manufacture_need(engine, sample_portfolio):
    gw = GeneralWealthContext(is_general_wealth=True)
    alloc_balanced = AllocationContext(
        exposure_gap=ExposureGap(
            gap_direction=ExposureGapDirection.BALANCED_EXPOSURE,
        )
    )
    res = engine.evaluate_need(
        investor_id="inv_001",
        portfolio_snapshot=sample_portfolio,
        allocation_context=alloc_balanced,
        general_wealth_context=gw,
    )
    assert res.primary_state == PortfolioNeedState.NO_MATERIAL_NEED


def test_25_multiple_goals_do_not_double_count_exposure(engine, sample_portfolio, sample_allocation_balanced):
    g1 = GoalFundingSnapshot(goal_id="g1", investor_id="inv_001", funding_status=FundingStatus.UNDERFUNDED)
    g2 = GoalFundingSnapshot(goal_id="g2", investor_id="inv_001", funding_status=FundingStatus.UNDERFUNDED)
    mg = MultiGoalContext(goal_snapshots=[g1, g2])
    res = engine.evaluate_need(
        investor_id="inv_001",
        goal_snapshot=g1,
        portfolio_snapshot=sample_portfolio,
        allocation_context=sample_allocation_balanced,
        multi_goal_context=mg,
    )
    assert res.primary_state == PortfolioNeedState.NO_MATERIAL_NEED


# --- PROVENANCE & EXPLAINABILITY (26-30) ---

def test_26_assessment_contains_required_provenance(engine, sample_goal, sample_portfolio, sample_allocation_positive, suitable_result):
    cand = FundCandidateContext(
        canonical_scheme_id="scheme_cand",
        suitability_result=suitable_result,
        suitability_assessment_id="suit_001",
        fund_quality_assessment_id="fq_001",
    )
    res = engine.evaluate_need(
        investor_id="inv_001",
        goal_snapshot=sample_goal,
        portfolio_snapshot=sample_portfolio,
        allocation_context=sample_allocation_positive,
        candidate_context=cand,
    )
    assert res.assessment_id.startswith("pnd_inv_001_")
    assert res.investor_id == "inv_001"
    assert res.goal_id == "goal_101"
    assert res.scheme_id == "scheme_cand"
    assert res.upstream_assessment_ids.get("suitability") == "suit_001"
    assert res.upstream_assessment_ids.get("fund_quality") == "fq_001"
    assert res.observation_timestamp is not None


def test_27_explanation_corresponds_to_actual_decision_inputs(engine, sample_goal, sample_portfolio, sample_allocation_positive):
    res = engine.evaluate_need(
        investor_id="inv_001",
        goal_snapshot=sample_goal,
        portfolio_snapshot=sample_portfolio,
        allocation_context=sample_allocation_positive,
    )
    assert "positive allocation gap" in res.explanation
    assert "does not constitute a transaction recommendation" in res.explanation


def test_28_candidate_fulfillment_rationale_distinguishable_from_suitability(engine, sample_goal, sample_portfolio, sample_allocation_positive, suitable_result):
    cand = FundCandidateContext(
        canonical_scheme_id="scheme_cand",
        suitability_result=suitable_result,
        is_capable_of_fulfilling_need=False,
    )
    res = engine.evaluate_need(
        investor_id="inv_001",
        goal_snapshot=sample_goal,
        portfolio_snapshot=sample_portfolio,
        allocation_context=sample_allocation_positive,
        candidate_context=cand,
    )
    assert res.candidate_fulfillment_status == CandidateFulfillmentStatus.CANDIDATE_CANNOT_FULFILL_NEED
    assert "CANDIDATE_NOT_CAPABLE_OF_FULFILLING_NEED" in res.contextual_flags
    assert "CANDIDATE_UNSUITABLE" not in res.contextual_flags


def test_29_derived_calculations_labelled_as_platform_calculated(engine, sample_goal, sample_portfolio, sample_allocation_positive):
    res = engine.evaluate_need(
        investor_id="inv_001",
        goal_snapshot=sample_goal,
        portfolio_snapshot=sample_portfolio,
        allocation_context=sample_allocation_positive,
    )
    assert "[platform-calculated]" in res.explanation


def test_30_methodology_and_rule_versions_preserved(engine, sample_goal, sample_portfolio, sample_allocation_positive):
    res = engine.evaluate_need(
        investor_id="inv_001",
        goal_snapshot=sample_goal,
        portfolio_snapshot=sample_portfolio,
        allocation_context=sample_allocation_positive,
    )
    assert res.methodology_version == "F.4.4-PROVISIONAL"
    assert res.rule_version == "1.0.0"


# --- ADDITIONAL RECONCILIATION BASELINE TESTS (31-33) ---

def test_31_multi_goal_unresolvable_returns_insufficient_information(engine, sample_portfolio):
    # Goal without snapshot or allocation context returns INSUFFICIENT_INFORMATION
    res = engine.evaluate_need(
        investor_id="inv_001",
        portfolio_snapshot=sample_portfolio,
    )
    assert res.primary_state == PortfolioNeedState.INSUFFICIENT_INFORMATION


def test_32_general_wealth_with_positive_exposure_gap_yields_need_identified(engine, sample_portfolio, sample_allocation_positive):
    gw = GeneralWealthContext(is_general_wealth=True)
    res = engine.evaluate_need(
        investor_id="inv_001",
        portfolio_snapshot=sample_portfolio,
        allocation_context=sample_allocation_positive,
        general_wealth_context=gw,
    )
    assert res.primary_state == PortfolioNeedState.NEED_IDENTIFIED
    assert res.goal_id is None


def test_33_provenance_preserves_affordability_upstream_assessment_id(engine, sample_goal, sample_portfolio, sample_allocation_positive):
    aff = AffordabilityContext(
        affordability_status=AffordabilityStatus.AFFORDABLE,
        upstream_assessment_id="aff_999",
    )
    res = engine.evaluate_need(
        investor_id="inv_001",
        goal_snapshot=sample_goal,
        portfolio_snapshot=sample_portfolio,
        allocation_context=sample_allocation_positive,
        affordability_context=aff,
    )
    assert res.upstream_assessment_ids.get("affordability") == "aff_999"
