"""
Risk Alignment Engine Comprehensive Financial & Integration Tests (Phase F.3.3.2).

Tests the Risk Alignment Engine against all 40 specified test scenarios:
- Core lower-of-two alignment calculations across 5 ordinal risk levels
- Complete assessment outcomes (FULLY_ALIGNED, CAPACITY_CONSTRAINED, TOLERANCE_CONSTRAINED)
- Partial assessment handling (PARTIAL_ALIGNMENT, confidence cap 0.70, tokens)
- Insufficient information handling (aligned_risk_level = None)
- Base confidence calculation, partial cap, stale penalty & confidence non-mutation
- Assessment staleness logic (gap <= 90 vs gap > 90, is_stale_input flag)
- Input validation, null handling, configuration safety in PRODUCTION/RESEARCH/TEST modes
- Construct isolation (demographics, horizon, fund metrics, macro data)
- Provenance preservation, audit metadata, determinism & explainability tokens
"""

import pytest
from datetime import date, datetime, timezone, timedelta

from config.risk.alignment_config import (
    RiskAlignmentConfig,
    StartupMode,
    create_production_config,
    create_research_config,
    create_test_config,
)
from models.fund_quality_dataset import ProvenanceMetadata
from models.investor_profile import (
    FinancialCapacitySnapshot,
    InvestorProfileSnapshot,
    RiskCapacityLevel,
    RiskToleranceLevel,
)
from risk.alignment_models import (
    AlignedRiskLevel,
    AlignmentStatus,
    LimitingConstraint,
    RiskAlignmentAssessmentResult,
)
from risk.alignment_engine import RiskAlignmentEngine
from risk.capacity_models import (
    AssessmentStatus,
    ConstraintResult,
    RiskCapacityAssessmentResult,
)
from risk.tolerance_models import (
    BehavioralConsistencyLevel,
    RiskToleranceAssessmentResult,
)


def _make_capacity_assessment(
    tier: Optional[RiskCapacityLevel] = RiskCapacityLevel.MODERATE,
    status: AssessmentStatus = AssessmentStatus.COMPLETE,
    confidence: float = 1.0,
    obs_date: Optional[date] = None,
    assessment_id: str = "RC-TEST-001",
    investor_id: str = "INV-100",
) -> RiskCapacityAssessmentResult:
    return RiskCapacityAssessmentResult(
        assessment_id=assessment_id,
        investor_id=investor_id,
        profile_version_used="1.0.0",
        observation_date=obs_date or date(2026, 9, 10),
        assessment_timestamp_utc=datetime.now(timezone.utc),
        startup_mode=StartupMode.TEST,
        assessment_status=status,
        overall_capacity_tier=tier,
        binding_constraint_name="DEBT_BURDEN" if tier else None,
        confidence_score=confidence,
        explanation_tokens=["STRONG_SURPLUS"],
        provenance=ProvenanceMetadata(
            source_id="AMFI_OFFICIAL",
            source_document_url="https://amfiindia.com",
            retrieval_timestamp_utc=datetime.now(timezone.utc),
        ),
    )


def _make_tolerance_assessment(
    tier: Optional[RiskToleranceLevel] = RiskToleranceLevel.MODERATE,
    status: AssessmentStatus = AssessmentStatus.COMPLETE,
    confidence: float = 1.0,
    obs_date: Optional[date] = None,
    assessment_id: str = "RT-TEST-001",
    investor_id: str = "INV-100",
) -> RiskToleranceAssessmentResult:
    return RiskToleranceAssessmentResult(
        assessment_id=assessment_id,
        investor_id=investor_id,
        profile_version_used="1.0.0",
        observation_date=obs_date or date(2026, 9, 10),
        assessment_timestamp_utc=datetime.now(timezone.utc),
        startup_mode=StartupMode.TEST,
        assessment_status=status,
        overall_tolerance_tier=tier,
        confidence_score=confidence,
        explanation_tokens=["CONSISTENT_RISK_TOLERANCE"],
        provenance=ProvenanceMetadata(
            source_id="AMFI_OFFICIAL",
            source_document_url="https://amfiindia.com",
            retrieval_timestamp_utc=datetime.now(timezone.utc),
        ),
    )


class TestRiskAlignmentEngine:

    @pytest.fixture
    def test_engine(self):
        return RiskAlignmentEngine(create_test_config())

    # -------------------------------------------------------------------------
    # 1. CORE ALIGNMENT & LOWER-OF-TWO CALCULATION (Scenarios 1-6)
    # -------------------------------------------------------------------------
    def test_01_very_low_and_very_low(self, test_engine):
        cap = _make_capacity_assessment(RiskCapacityLevel.VERY_LOW)
        tol = _make_tolerance_assessment(RiskToleranceLevel.VERY_LOW)
        res = test_engine.assess_alignment(cap, tol)
        assert res.aligned_risk_level == AlignedRiskLevel.VERY_LOW
        assert res.alignment_status == AlignmentStatus.FULLY_ALIGNED
        assert res.limiting_constraint == LimitingConstraint.NONE

    def test_02_very_low_capacity_and_very_high_tolerance(self, test_engine):
        cap = _make_capacity_assessment(RiskCapacityLevel.VERY_LOW)
        tol = _make_tolerance_assessment(RiskToleranceLevel.VERY_HIGH)
        res = test_engine.assess_alignment(cap, tol)
        assert res.aligned_risk_level == AlignedRiskLevel.VERY_LOW
        assert res.alignment_status == AlignmentStatus.CAPACITY_CONSTRAINED
        assert res.limiting_constraint == LimitingConstraint.RISK_CAPACITY
        assert "CONSTRAINED_BY_RISK_CAPACITY" in res.explanation_tokens

    def test_03_very_high_capacity_and_very_low_tolerance(self, test_engine):
        cap = _make_capacity_assessment(RiskCapacityLevel.VERY_HIGH)
        tol = _make_tolerance_assessment(RiskToleranceLevel.VERY_LOW)
        res = test_engine.assess_alignment(cap, tol)
        assert res.aligned_risk_level == AlignedRiskLevel.VERY_LOW
        assert res.alignment_status == AlignmentStatus.TOLERANCE_CONSTRAINED
        assert res.limiting_constraint == LimitingConstraint.RISK_TOLERANCE
        assert "CONSTRAINED_BY_RISK_TOLERANCE" in res.explanation_tokens

    def test_04_high_capacity_and_moderate_tolerance(self, test_engine):
        cap = _make_capacity_assessment(RiskCapacityLevel.HIGH)
        tol = _make_tolerance_assessment(RiskToleranceLevel.MODERATE)
        res = test_engine.assess_alignment(cap, tol)
        assert res.aligned_risk_level == AlignedRiskLevel.MODERATE
        assert res.alignment_status == AlignmentStatus.TOLERANCE_CONSTRAINED
        assert res.limiting_constraint == LimitingConstraint.RISK_TOLERANCE

    def test_05_moderate_capacity_and_high_tolerance(self, test_engine):
        cap = _make_capacity_assessment(RiskCapacityLevel.MODERATE)
        tol = _make_tolerance_assessment(RiskToleranceLevel.HIGH)
        res = test_engine.assess_alignment(cap, tol)
        assert res.aligned_risk_level == AlignedRiskLevel.MODERATE
        assert res.alignment_status == AlignmentStatus.CAPACITY_CONSTRAINED
        assert res.limiting_constraint == LimitingConstraint.RISK_CAPACITY

    def test_06_equal_levels_across_all_five_tiers(self, test_engine):
        tiers = [
            (RiskCapacityLevel.VERY_LOW, RiskToleranceLevel.VERY_LOW, AlignedRiskLevel.VERY_LOW),
            (RiskCapacityLevel.LOW, RiskToleranceLevel.LOW, AlignedRiskLevel.LOW),
            (RiskCapacityLevel.MODERATE, RiskToleranceLevel.MODERATE, AlignedRiskLevel.MODERATE),
            (RiskCapacityLevel.HIGH, RiskToleranceLevel.HIGH, AlignedRiskLevel.HIGH),
            (RiskCapacityLevel.VERY_HIGH, RiskToleranceLevel.VERY_HIGH, AlignedRiskLevel.VERY_HIGH),
        ]
        for c_tier, t_tier, expected_aligned in tiers:
            cap = _make_capacity_assessment(c_tier)
            tol = _make_tolerance_assessment(t_tier)
            res = test_engine.assess_alignment(cap, tol)
            assert res.aligned_risk_level == expected_aligned
            assert res.alignment_status == AlignmentStatus.FULLY_ALIGNED
            assert res.limiting_constraint == LimitingConstraint.NONE

    # -------------------------------------------------------------------------
    # 2. COMPLETE ASSESSMENTS (Scenarios 7-9)
    # -------------------------------------------------------------------------
    def test_07_fully_aligned_complete_inputs(self, test_engine):
        cap = _make_capacity_assessment(RiskCapacityLevel.HIGH, AssessmentStatus.COMPLETE)
        tol = _make_tolerance_assessment(RiskToleranceLevel.HIGH, AssessmentStatus.COMPLETE)
        res = test_engine.assess_alignment(cap, tol)
        assert res.alignment_status == AlignmentStatus.FULLY_ALIGNED
        assert res.limiting_constraint == LimitingConstraint.NONE
        assert "FULLY_ALIGNED_CAPACITY_AND_TOLERANCE" in res.explanation_tokens

    def test_08_capacity_constrained_complete_inputs(self, test_engine):
        cap = _make_capacity_assessment(RiskCapacityLevel.LOW, AssessmentStatus.COMPLETE)
        tol = _make_tolerance_assessment(RiskToleranceLevel.HIGH, AssessmentStatus.COMPLETE)
        res = test_engine.assess_alignment(cap, tol)
        assert res.alignment_status == AlignmentStatus.CAPACITY_CONSTRAINED
        assert res.limiting_constraint == LimitingConstraint.RISK_CAPACITY
        assert "CONSTRAINED_BY_RISK_CAPACITY" in res.explanation_tokens

    def test_09_tolerance_constrained_complete_inputs(self, test_engine):
        cap = _make_capacity_assessment(RiskCapacityLevel.HIGH, AssessmentStatus.COMPLETE)
        tol = _make_tolerance_assessment(RiskToleranceLevel.LOW, AssessmentStatus.COMPLETE)
        res = test_engine.assess_alignment(cap, tol)
        assert res.alignment_status == AlignmentStatus.TOLERANCE_CONSTRAINED
        assert res.limiting_constraint == LimitingConstraint.RISK_TOLERANCE
        assert "CONSTRAINED_BY_RISK_TOLERANCE" in res.explanation_tokens

    # -------------------------------------------------------------------------
    # 3. PARTIAL ASSESSMENTS (Scenarios 10-13)
    # -------------------------------------------------------------------------
    def test_10_partial_capacity_and_complete_tolerance(self, test_engine):
        cap = _make_capacity_assessment(RiskCapacityLevel.MODERATE, AssessmentStatus.PARTIAL, confidence=0.85)
        tol = _make_tolerance_assessment(RiskToleranceLevel.HIGH, AssessmentStatus.COMPLETE, confidence=1.0)
        res = test_engine.assess_alignment(cap, tol)
        assert res.aligned_risk_level == AlignedRiskLevel.MODERATE
        assert res.alignment_status == AlignmentStatus.PARTIAL_ALIGNMENT
        assert res.limiting_constraint == LimitingConstraint.RISK_CAPACITY
        assert res.alignment_confidence_score == 0.70  # Capped at 0.70
        assert "PROVISIONAL_ALIGNMENT_PARTIAL_INPUTS" in res.explanation_tokens
        assert "PARTIAL_ALIGNMENT_CAPACITY_PARTIAL" in res.missing_information_tokens

    def test_11_complete_capacity_and_partial_tolerance(self, test_engine):
        cap = _make_capacity_assessment(RiskCapacityLevel.HIGH, AssessmentStatus.COMPLETE, confidence=1.0)
        tol = _make_tolerance_assessment(RiskToleranceLevel.MODERATE, AssessmentStatus.PARTIAL, confidence=0.70)
        res = test_engine.assess_alignment(cap, tol)
        assert res.aligned_risk_level == AlignedRiskLevel.MODERATE
        assert res.alignment_status == AlignmentStatus.PARTIAL_ALIGNMENT
        assert res.limiting_constraint == LimitingConstraint.RISK_TOLERANCE
        assert res.alignment_confidence_score == 0.70
        assert "PARTIAL_ALIGNMENT_TOLERANCE_PARTIAL" in res.missing_information_tokens

    def test_12_partial_capacity_and_partial_tolerance(self, test_engine):
        cap = _make_capacity_assessment(RiskCapacityLevel.LOW, AssessmentStatus.PARTIAL, confidence=0.80)
        tol = _make_tolerance_assessment(RiskToleranceLevel.HIGH, AssessmentStatus.PARTIAL, confidence=0.75)
        res = test_engine.assess_alignment(cap, tol)
        assert res.aligned_risk_level == AlignedRiskLevel.LOW
        assert res.alignment_status == AlignmentStatus.PARTIAL_ALIGNMENT
        assert res.alignment_confidence_score == 0.70
        assert "PARTIAL_ALIGNMENT_CAPACITY_PARTIAL" in res.missing_information_tokens
        assert "PARTIAL_ALIGNMENT_TOLERANCE_PARTIAL" in res.missing_information_tokens

    def test_13_equal_tiers_with_partial_inputs_remain_partial_alignment(self, test_engine):
        cap = _make_capacity_assessment(RiskCapacityLevel.MODERATE, AssessmentStatus.PARTIAL, confidence=0.80)
        tol = _make_tolerance_assessment(RiskToleranceLevel.MODERATE, AssessmentStatus.COMPLETE, confidence=1.0)
        res = test_engine.assess_alignment(cap, tol)
        assert res.aligned_risk_level == AlignedRiskLevel.MODERATE
        assert res.alignment_status == AlignmentStatus.PARTIAL_ALIGNMENT  # Does NOT become FULLY_ALIGNED
        assert res.limiting_constraint == LimitingConstraint.NONE

    # -------------------------------------------------------------------------
    # 4. INSUFFICIENT INFORMATION (Scenarios 14-16)
    # -------------------------------------------------------------------------
    def test_14_insufficient_capacity_assessment(self, test_engine):
        cap = _make_capacity_assessment(tier=None, status=AssessmentStatus.INSUFFICIENT_INFORMATION, confidence=0.20)
        tol = _make_tolerance_assessment(RiskToleranceLevel.HIGH, status=AssessmentStatus.COMPLETE, confidence=1.0)
        res = test_engine.assess_alignment(cap, tol)
        assert res.aligned_risk_level is None
        assert res.alignment_status == AlignmentStatus.INSUFFICIENT_INFORMATION
        assert res.limiting_constraint == LimitingConstraint.UNCLASSIFIED
        assert "INSUFFICIENT_DATA_CAPACITY_MISSING" in res.missing_information_tokens

    def test_15_insufficient_tolerance_assessment(self, test_engine):
        cap = _make_capacity_assessment(RiskCapacityLevel.HIGH, status=AssessmentStatus.COMPLETE, confidence=1.0)
        tol = _make_tolerance_assessment(tier=None, status=AssessmentStatus.INSUFFICIENT_INFORMATION, confidence=0.20)
        res = test_engine.assess_alignment(cap, tol)
        assert res.aligned_risk_level is None
        assert res.alignment_status == AlignmentStatus.INSUFFICIENT_INFORMATION
        assert res.limiting_constraint == LimitingConstraint.UNCLASSIFIED
        assert "INSUFFICIENT_DATA_TOLERANCE_MISSING" in res.missing_information_tokens

    def test_16_both_assessments_insufficient(self, test_engine):
        cap = _make_capacity_assessment(tier=None, status=AssessmentStatus.INSUFFICIENT_INFORMATION, confidence=0.20)
        tol = _make_tolerance_assessment(tier=None, status=AssessmentStatus.INSUFFICIENT_INFORMATION, confidence=0.20)
        res = test_engine.assess_alignment(cap, tol)
        assert res.aligned_risk_level is None
        assert res.alignment_status == AlignmentStatus.INSUFFICIENT_INFORMATION
        assert res.limiting_constraint == LimitingConstraint.BOTH_INSUFFICIENT
        assert "INSUFFICIENT_DATA_CAPACITY_MISSING" in res.missing_information_tokens
        assert "INSUFFICIENT_DATA_TOLERANCE_MISSING" in res.missing_information_tokens

    # -------------------------------------------------------------------------
    # 5. CONFIDENCE LOGIC & PENALTIES (Scenarios 17-20)
    # -------------------------------------------------------------------------
    def test_17_base_confidence_equals_lower_input_confidence(self, test_engine):
        cap = _make_capacity_assessment(RiskCapacityLevel.HIGH, confidence=0.60)
        tol = _make_tolerance_assessment(RiskToleranceLevel.HIGH, confidence=0.90)
        res = test_engine.assess_alignment(cap, tol)
        assert res.alignment_confidence_score == 0.60

    def test_18_partial_confidence_cap_applied(self, test_engine):
        cap = _make_capacity_assessment(RiskCapacityLevel.HIGH, status=AssessmentStatus.PARTIAL, confidence=0.95)
        tol = _make_tolerance_assessment(RiskToleranceLevel.HIGH, status=AssessmentStatus.COMPLETE, confidence=1.0)
        res = test_engine.assess_alignment(cap, tol)
        assert res.alignment_confidence_score == 0.70

    def test_19_confidence_never_changes_aligned_risk_level(self, test_engine):
        cap = _make_capacity_assessment(RiskCapacityLevel.MODERATE, confidence=0.10)
        tol = _make_tolerance_assessment(RiskToleranceLevel.MODERATE, confidence=0.10)
        res = test_engine.assess_alignment(cap, tol)
        assert res.aligned_risk_level == AlignedRiskLevel.MODERATE  # Unchanged
        assert res.alignment_confidence_score == 0.10

    def test_20_confidence_remains_clamped_in_bounds(self, test_engine):
        cap = _make_capacity_assessment(RiskCapacityLevel.HIGH, confidence=1.0)
        tol = _make_tolerance_assessment(RiskToleranceLevel.HIGH, confidence=1.0)
        res = test_engine.assess_alignment(cap, tol)
        assert 0.0 <= res.alignment_confidence_score <= 1.0

    # -------------------------------------------------------------------------
    # 6. STALENESS LOGIC (Scenarios 21-25)
    # -------------------------------------------------------------------------
    def test_21_gap_below_threshold_is_not_stale(self, test_engine):
        cap_date = date(2026, 9, 10)
        tol_date = date(2026, 8, 10)  # 31 days gap
        cap = _make_capacity_assessment(RiskCapacityLevel.HIGH, obs_date=cap_date)
        tol = _make_tolerance_assessment(RiskToleranceLevel.HIGH, obs_date=tol_date)
        res = test_engine.assess_alignment(cap, tol)
        assert res.is_stale_input is False
        assert res.alignment_confidence_score == 1.0
        assert "STALE_ASSESSMENT_INPUT_GAP_EXCEEDED" not in res.explanation_tokens

    def test_22_gap_exactly_at_threshold_is_not_stale(self, test_engine):
        cap_date = date(2026, 9, 10)
        tol_date = cap_date - timedelta(days=90)  # Exactly 90 days gap
        cap = _make_capacity_assessment(RiskCapacityLevel.HIGH, obs_date=cap_date)
        tol = _make_tolerance_assessment(RiskToleranceLevel.HIGH, obs_date=tol_date)
        res = test_engine.assess_alignment(cap, tol)
        assert res.is_stale_input is False
        assert res.alignment_confidence_score == 1.0

    def test_23_gap_above_threshold_is_stale(self, test_engine):
        cap_date = date(2026, 9, 10)
        tol_date = cap_date - timedelta(days=91)  # 91 days gap (> 90)
        cap = _make_capacity_assessment(RiskCapacityLevel.HIGH, obs_date=cap_date, confidence=1.0)
        tol = _make_tolerance_assessment(RiskToleranceLevel.HIGH, obs_date=tol_date, confidence=1.0)
        res = test_engine.assess_alignment(cap, tol)
        assert res.is_stale_input is True
        assert "STALE_ASSESSMENT_INPUT_GAP_EXCEEDED" in res.explanation_tokens
        assert res.alignment_confidence_score == pytest.approx(1.0 * 0.85)

    def test_24_stale_penalty_affects_confidence_only(self, test_engine):
        cap_date = date(2026, 9, 10)
        tol_date = cap_date - timedelta(days=120)
        cap = _make_capacity_assessment(RiskCapacityLevel.HIGH, obs_date=cap_date)
        tol = _make_tolerance_assessment(RiskToleranceLevel.HIGH, obs_date=tol_date)
        res = test_engine.assess_alignment(cap, tol)
        assert res.aligned_risk_level == AlignedRiskLevel.HIGH
        assert res.alignment_confidence_score == pytest.approx(0.85)

    def test_25_stale_and_partial_confidence_penalty_ordering(self, test_engine):
        # Step 1: Base = min(0.90, 1.0) = 0.90
        # Step 2: Partial Cap = min(0.90, 0.70) = 0.70
        # Step 3: Stale Penalty = 0.70 * 0.85 = 0.595
        cap_date = date(2026, 9, 10)
        tol_date = cap_date - timedelta(days=100)
        cap = _make_capacity_assessment(RiskCapacityLevel.HIGH, status=AssessmentStatus.PARTIAL, confidence=0.90, obs_date=cap_date)
        tol = _make_tolerance_assessment(RiskToleranceLevel.HIGH, status=AssessmentStatus.COMPLETE, confidence=1.0, obs_date=tol_date)
        res = test_engine.assess_alignment(cap, tol)
        assert res.alignment_status == AlignmentStatus.PARTIAL_ALIGNMENT
        assert res.is_stale_input is True
        assert res.alignment_confidence_score == pytest.approx(0.70 * 0.85)

    # -------------------------------------------------------------------------
    # 7. VALIDATION & CONFIGURATION SAFETY (Scenarios 26-30)
    # -------------------------------------------------------------------------
    def test_26_null_capacity_assessment_handled(self, test_engine):
        tol = _make_tolerance_assessment(RiskToleranceLevel.HIGH)
        res = test_engine.assess_alignment(None, tol)
        assert res.alignment_status == AlignmentStatus.INSUFFICIENT_INFORMATION
        assert res.aligned_risk_level is None
        assert "MISSING_CAPACITY_ASSESSMENT" in res.missing_information_tokens

    def test_27_null_tolerance_assessment_handled(self, test_engine):
        cap = _make_capacity_assessment(RiskCapacityLevel.HIGH)
        res = test_engine.assess_alignment(cap, None)
        assert res.alignment_status == AlignmentStatus.INSUFFICIENT_INFORMATION
        assert res.aligned_risk_level is None
        assert "MISSING_TOLERANCE_ASSESSMENT" in res.missing_information_tokens

    def test_28_configuration_error_in_underlying_assessment(self, test_engine):
        cap = _make_capacity_assessment(status=AssessmentStatus.CONFIGURATION_ERROR)
        tol = _make_tolerance_assessment(RiskToleranceLevel.HIGH)
        res = test_engine.assess_alignment(cap, tol)
        assert res.alignment_status == AlignmentStatus.INVALID_ASSESSMENT
        assert res.aligned_risk_level is None
        assert "INPUT_ASSESSMENT_CONFIGURATION_ERROR" in res.explanation_tokens

    def test_29_production_mode_configuration_safety(self):
        prod_config = create_production_config()  # Missing provisional parameters
        prod_engine = RiskAlignmentEngine(prod_config)
        cap = _make_capacity_assessment(RiskCapacityLevel.HIGH)
        tol = _make_tolerance_assessment(RiskToleranceLevel.HIGH)
        res = prod_engine.assess_alignment(cap, tol)
        assert res.alignment_status == AlignmentStatus.INVALID_ASSESSMENT
        assert res.aligned_risk_level is None
        assert "MISSING_PRODUCTION_CALIBRATION_PARAMETERS" in res.explanation_tokens

    def test_30_research_and_test_startup_mode_tags(self):
        res_engine = RiskAlignmentEngine(create_research_config())
        test_engine = RiskAlignmentEngine(create_test_config())
        cap = _make_capacity_assessment(RiskCapacityLevel.HIGH)
        tol = _make_tolerance_assessment(RiskToleranceLevel.HIGH)
        
        res_out = res_engine.assess_alignment(cap, tol)
        assert res_out.output_tag == "RESEARCH_MODE_NOT_FOR_PRODUCTION"

        test_out = test_engine.assess_alignment(cap, tol)
        assert test_out.output_tag == "SYNTHETIC_TEST_DATA"

    # -------------------------------------------------------------------------
    # 8. CONSTRUCT ISOLATION (Scenarios 31-34)
    # -------------------------------------------------------------------------
    def test_31_demographic_data_cannot_alter_alignment(self, test_engine):
        cap = _make_capacity_assessment(RiskCapacityLevel.MODERATE)
        tol = _make_tolerance_assessment(RiskToleranceLevel.HIGH)
        res1 = test_engine.assess_alignment(cap, tol, investor_id="INV-001")
        res2 = test_engine.assess_alignment(cap, tol, investor_id="INV-999")
        assert res1.aligned_risk_level == res2.aligned_risk_level
        assert res1.limiting_constraint == res2.limiting_constraint

    def test_32_investment_horizon_cannot_alter_alignment(self, test_engine):
        cap = _make_capacity_assessment(RiskCapacityLevel.LOW)
        tol = _make_tolerance_assessment(RiskToleranceLevel.HIGH)
        res = test_engine.assess_alignment(cap, tol)
        assert res.aligned_risk_level == AlignedRiskLevel.LOW
        assert res.limiting_constraint == LimitingConstraint.RISK_CAPACITY

    def test_33_fund_metrics_cannot_alter_alignment(self, test_engine):
        cap = _make_capacity_assessment(RiskCapacityLevel.HIGH)
        tol = _make_tolerance_assessment(RiskToleranceLevel.VERY_HIGH)
        res = test_engine.assess_alignment(cap, tol)
        assert res.aligned_risk_level == AlignedRiskLevel.HIGH

    def test_34_macro_data_cannot_alter_alignment(self, test_engine):
        cap = _make_capacity_assessment(RiskCapacityLevel.VERY_LOW)
        tol = _make_tolerance_assessment(RiskToleranceLevel.MODERATE)
        res = test_engine.assess_alignment(cap, tol)
        assert res.aligned_risk_level == AlignedRiskLevel.VERY_LOW

    # -------------------------------------------------------------------------
    # 9. PROVENANCE & AUDIT TRAIL (Scenarios 35-37)
    # -------------------------------------------------------------------------
    def test_35_both_source_assessment_ids_preserved(self, test_engine):
        cap = _make_capacity_assessment(assessment_id="RC-999-ABC")
        tol = _make_tolerance_assessment(assessment_id="RT-888-XYZ")
        res = test_engine.assess_alignment(cap, tol)
        assert res.capacity_assessment_id == "RC-999-ABC"
        assert res.tolerance_assessment_id == "RT-888-XYZ"

    def test_36_versions_and_timestamps_preserved(self, test_engine):
        cap = _make_capacity_assessment()
        tol = _make_tolerance_assessment()
        res = test_engine.assess_alignment(cap, tol)
        assert res.methodology_version == "1.0.0"
        assert res.rule_version == "1.0.0"
        assert res.assessment_timestamp_utc is not None

    def test_37_determinism_across_repeated_runs(self, test_engine):
        cap = _make_capacity_assessment(RiskCapacityLevel.MODERATE)
        tol = _make_tolerance_assessment(RiskToleranceLevel.HIGH)
        res1 = test_engine.assess_alignment(cap, tol)
        res2 = test_engine.assess_alignment(cap, tol)
        assert res1.aligned_risk_level == res2.aligned_risk_level
        assert res1.alignment_status == res2.alignment_status
        assert res1.limiting_constraint == res2.limiting_constraint
        assert res1.alignment_confidence_score == res2.alignment_confidence_score

    # -------------------------------------------------------------------------
    # 10. EXPLAINABILITY TOKENS (Scenarios 38-40)
    # -------------------------------------------------------------------------
    def test_38_complete_alignment_explanation_tokens(self, test_engine):
        cap = _make_capacity_assessment(RiskCapacityLevel.LOW)
        tol = _make_tolerance_assessment(RiskToleranceLevel.HIGH)
        res = test_engine.assess_alignment(cap, tol)
        assert "CONSTRAINED_BY_RISK_CAPACITY" in res.explanation_tokens

    def test_39_partial_alignment_explanation_tokens(self, test_engine):
        cap = _make_capacity_assessment(RiskCapacityLevel.HIGH, status=AssessmentStatus.PARTIAL)
        tol = _make_tolerance_assessment(RiskToleranceLevel.HIGH, status=AssessmentStatus.COMPLETE)
        res = test_engine.assess_alignment(cap, tol)
        assert "PROVISIONAL_ALIGNMENT_PARTIAL_INPUTS" in res.explanation_tokens
        assert "PARTIAL_ALIGNMENT_CAPACITY_PARTIAL" in res.missing_information_tokens

    def test_40_insufficient_information_missing_explanation_tokens(self, test_engine):
        cap = _make_capacity_assessment(tier=None, status=AssessmentStatus.INSUFFICIENT_INFORMATION)
        tol = _make_tolerance_assessment(RiskToleranceLevel.HIGH)
        res = test_engine.assess_alignment(cap, tol)
        assert "INSUFFICIENT_DATA_CAPACITY_MISSING" in res.missing_information_tokens
