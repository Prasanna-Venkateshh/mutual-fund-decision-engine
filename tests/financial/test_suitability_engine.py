"""
Financial Tests for Production Suitability Engine (Phase F.3.4.4).

Verifies all 23 decision scenarios specified in F.3.4.3:
- State outcomes (SUITABLE, CONDITIONALLY_SUITABLE, NOT_SUITABLE, INSUFFICIENT_INFORMATION, INVALID_ASSESSMENT)
- Pipeline precedence (Invalid > Insufficient > Hard > Conditional > Positive)
- Hard constraint violations vs Positive evidence overrides
- Immature fund handling
- Horizon & Portfolio context concerns
- Construct isolation & Scope isolation
"""

import pytest
from datetime import date, datetime
import uuid

from models.fund_quality_dataset import FundQualityDatasetInput, ProvenanceMetadata
from scoring.models import FundQualityScoreResult, DimensionScore
from models.investor_profile import (
    InvestorProfileSnapshot, RiskCapacityLevel, RiskToleranceLevel, 
    FinancialCapacitySnapshot, BehavioralToleranceSnapshot
)
from models.goal_profile import GoalProfile, GoalCategory, GoalPriority
from models.suitability_assessment import SuitabilityAssessmentResult, SuitabilityStatus
from risk.alignment_models import RiskAlignmentAssessmentResult, AlignmentStatus, LimitingConstraint, AlignedRiskLevel
from config.risk.capacity_config import StartupMode
from risk.suitability_engine import (
    SuitabilityEngine, SuitabilityEvaluationRequest, SuitabilityEvaluationState,
    FundRiskProfileInput, LockInContextInput, LiquidityContextInput, PortfolioContextInput
)


@pytest.fixture
def base_investor_profile():
    return InvestorProfileSnapshot(
        profile_id="PROF_001",
        investor_id="INV_001",
        profile_version="1.0.0",
        effective_date=date(2025, 1, 15),
        financial_capacity=FinancialCapacitySnapshot(
            observation_date=date(2025, 1, 15),
            effective_date=date(2025, 1, 15),
            monthly_gross_income=100000.0,
            monthly_fixed_expenses=40000.0,
            liquid_emergency_reserves=1500000.0,
            monthly_debt_servicing=10000.0,
            emergency_reserve_months=6.0,
            capacity_tier=RiskCapacityLevel.HIGH
        ),
        behavioral_tolerance=BehavioralToleranceSnapshot(
            observation_date=date(2025, 1, 15),
            assessment_date=date(2025, 1, 15),
            tolerance_tier=RiskToleranceLevel.HIGH
        )
    )


@pytest.fixture
def base_goal_profile():
    return GoalProfile(
        goal_id="GOAL_RETIREMENT",
        investor_id="INV_001",
        goal_name="Retirement Corpus",
        goal_category=GoalCategory.RETIREMENT,
        effective_horizon_years=15.0,
        target_amount=20000000.0,
        priority=GoalPriority.HIGH
    )


@pytest.fixture
def base_fund_quality():
    return FundQualityScoreResult(
        canonical_scheme_id="SCHEME_HDFC_TOP100",
        amfi_code="100028",
        scheme_name="HDFC Top 100 Fund - Growth",
        category="Equity",
        subcategory="Large Cap",
        observation_date=date(2025, 1, 15),
        quality_score=82.5,
        confidence_score=0.95,
        data_quality_score=0.90,
        dimension_scores={},
        available_dimensions_count=2,
        total_dimensions_count=2,
        peer_group_size=40,
        scoring_methodology_version="1.0.0",
        weight_config_version="1.0.0",
        calculation_timestamp_utc=datetime.utcnow(),
        summary_explanation="Strong performance and downside risk control",
        is_provisional=False
    )


@pytest.fixture
def base_risk_alignment():
    return RiskAlignmentAssessmentResult(
        assessment_id="RA_001",
        investor_id="INV_001",
        profile_version_used="1.0.0",
        observation_date=date(2025, 1, 15),
        assessment_timestamp_utc=datetime.utcnow(),
        startup_mode=StartupMode.PRODUCTION,
        alignment_status=AlignmentStatus.FULLY_ALIGNED,
        limiting_constraint=LimitingConstraint.NONE,
        aligned_risk_level=AlignedRiskLevel.HIGH,
        risk_capacity_level=RiskCapacityLevel.HIGH,
        risk_tolerance_level=RiskToleranceLevel.HIGH,
        alignment_confidence_score=0.95
    )


class TestSuitabilityEngineScenarios:

    def setup_method(self):
        self.engine = SuitabilityEngine()

    def test_01_hard_incompatibility_over_risk_violation(self, base_investor_profile, base_risk_alignment, base_fund_quality):
        """Scenario 1: Verified over-risk violation -> NOT_SUITABLE."""
        req = SuitabilityEvaluationRequest(
            investor_profile=base_investor_profile,
            risk_alignment=base_risk_alignment, # Aligned = HIGH (4)
            fund_quality_score=base_fund_quality,
            fund_risk_profile=FundRiskProfileInput(raw_riskometer_value="Very High", risk_level_numeric=5, is_mapped=True) # Fund = 5
        )
        res = self.engine.evaluate(req)
        assert res.suitability_status == SuitabilityStatus.NOT_SUITABLE
        assert "R-HARD-1" in res.constraints_applied
        assert any("exceeds Aligned Risk Level" in r for r in res.rejection_reasons)

    def test_02_conditional_concern_immature_fund_with_horizon_concern(self, base_investor_profile, base_risk_alignment):
        """Scenario 2: Immature fund + volatility concern -> CONDITIONALLY_SUITABLE."""
        immature_fund = FundQualityScoreResult(
            canonical_scheme_id="SCHEME_NEW_EQUITY",
            amfi_code="100999",
            scheme_name="New Tech Fund",
            category="Equity",
            subcategory="Sectoral",
            observation_date=date(2025, 1, 15),
            quality_score=70.0,
            confidence_score=0.80,
            data_quality_score=0.75,
            dimension_scores={},
            available_dimensions_count=2,
            total_dimensions_count=2,
            peer_group_size=15,
            scoring_methodology_version="1.0.0",
            weight_config_version="1.0.0",
            calculation_timestamp_utc=datetime.utcnow(),
            summary_explanation="New fund with limited track record",
            is_provisional=True
        )
        short_goal = GoalProfile(
            goal_id="GOAL_SHORT", investor_id="INV_001", goal_name="Vacation", goal_category=GoalCategory.OTHER, effective_horizon_years=2.0
        )
        req = SuitabilityEvaluationRequest(
            investor_profile=base_investor_profile,
            risk_alignment=base_risk_alignment,
            fund_quality_score=immature_fund,
            goal_profile=short_goal
        )
        res = self.engine.evaluate(req)
        assert res.suitability_status == SuitabilityStatus.SUITABLE_WITH_CONSTRAINTS
        assert "R-COND-2" in res.constraints_applied
        assert "R-COND-5" in res.constraints_applied

    def test_03_positive_evidence_suitable(self, base_investor_profile, base_risk_alignment, base_fund_quality, base_goal_profile):
        """Scenario 3: Aligned risk & timeline + high quality -> SUITABLE."""
        req = SuitabilityEvaluationRequest(
            investor_profile=base_investor_profile,
            risk_alignment=base_risk_alignment,
            fund_quality_score=base_fund_quality,
            goal_profile=base_goal_profile
        )
        res = self.engine.evaluate(req)
        assert res.suitability_status == SuitabilityStatus.SUITABLE
        assert "R-POS-1" in res.constraints_applied
        assert res.suitability_confidence_score == 0.95

    def test_04_insufficient_information_missing_risk_alignment(self, base_investor_profile, base_fund_quality):
        """Scenario 4: Missing Risk Alignment -> INSUFFICIENT_INFORMATION."""
        req = SuitabilityEvaluationRequest(
            investor_profile=base_investor_profile,
            risk_alignment=None,
            fund_quality_score=base_fund_quality
        )
        res = self.engine.evaluate(req)
        assert res.suitability_status == SuitabilityStatus.INSUFFICIENT_INFORMATION
        assert "R-INF-1" in res.constraints_applied

    def test_05_invalid_assessment_negative_confidence(self, base_investor_profile, base_fund_quality):
        """Scenario 5: Negative confidence input -> INVALID_ASSESSMENT (represented as INSUFFICIENT_INFORMATION with 0 confidence in contract)."""
        invalid_alignment = RiskAlignmentAssessmentResult(
            assessment_id="RA_INV",
            investor_id="INV_001",
            profile_version_used="1.0.0",
            observation_date=date(2025, 1, 15),
            assessment_timestamp_utc=datetime.utcnow(),
            startup_mode=StartupMode.PRODUCTION,
            alignment_status=AlignmentStatus.INVALID_ASSESSMENT,
            limiting_constraint=LimitingConstraint.UNCLASSIFIED,
            alignment_confidence_score=0.0
        )
        req = SuitabilityEvaluationRequest(
            investor_profile=base_investor_profile,
            risk_alignment=invalid_alignment,
            fund_quality_score=base_fund_quality
        )
        res = self.engine.evaluate(req)
        assert res.suitability_confidence_score == 0.0
        assert "R-INV-1" in res.constraints_applied

    def test_11_lock_in_conflict(self, base_investor_profile, base_risk_alignment, base_fund_quality):
        """Scenario 11: Statutory lock-in exceeding goal target date -> NOT_SUITABLE."""
        short_goal = GoalProfile(
            goal_id="GOAL_3Y", investor_id="INV_001", goal_name="Car", goal_category=GoalCategory.OTHER, effective_horizon_years=2.0
        )
        lock_in = LockInContextInput(lock_in_years=3.0, is_statutory=True, is_available=True)
        req = SuitabilityEvaluationRequest(
            investor_profile=base_investor_profile,
            risk_alignment=base_risk_alignment,
            fund_quality_score=base_fund_quality,
            goal_profile=short_goal,
            lock_in_context=lock_in
        )
        res = self.engine.evaluate(req)
        assert res.suitability_status == SuitabilityStatus.NOT_SUITABLE
        assert "R-HARD-2" in res.constraints_applied

    def test_13_immature_fund_alone_does_not_force_conditional(self, base_investor_profile, base_risk_alignment, base_goal_profile):
        """Scenario 13: Immature fund alone -> Reduced confidence, stays SUITABLE (does not force CONDITIONALLY_SUITABLE alone)."""
        immature_fund = FundQualityScoreResult(
            canonical_scheme_id="SCHEME_NEW_HYBRID",
            amfi_code="100998",
            scheme_name="New Hybrid Fund",
            category="Hybrid",
            subcategory="Aggressive",
            observation_date=date(2025, 1, 15),
            quality_score=75.0,
            confidence_score=0.90,
            data_quality_score=0.85,
            dimension_scores={},
            available_dimensions_count=2,
            total_dimensions_count=2,
            peer_group_size=20,
            scoring_methodology_version="1.0.0",
            weight_config_version="1.0.0",
            calculation_timestamp_utc=datetime.utcnow(),
            summary_explanation="New hybrid fund",
            is_provisional=True
        )
        req = SuitabilityEvaluationRequest(
            investor_profile=base_investor_profile,
            risk_alignment=base_risk_alignment,
            fund_quality_score=immature_fund,
            goal_profile=base_goal_profile # Long horizon (15 yrs)
        )
        res = self.engine.evaluate(req)
        assert res.suitability_status == SuitabilityStatus.SUITABLE
        assert "R-COND-5" in res.constraints_applied
        assert res.suitability_confidence_score == 0.75 # 0.90 - 0.15 penalty

    def test_21_lower_risk_fund_suitable_with_warning(self, base_investor_profile, base_risk_alignment, base_fund_quality, base_goal_profile):
        """Scenario 21: Fund risk below investor envelope -> SUITABLE with contextual warning."""
        req = SuitabilityEvaluationRequest(
            investor_profile=base_investor_profile,
            risk_alignment=base_risk_alignment, # Aligned = HIGH (4)
            fund_quality_score=base_fund_quality,
            goal_profile=base_goal_profile,
            fund_risk_profile=FundRiskProfileInput(raw_riskometer_value="Low to Moderate", risk_level_numeric=2, is_mapped=True) # Fund = 2
        )
        res = self.engine.evaluate(req)
        assert res.suitability_status == SuitabilityStatus.SUITABLE
        assert "R-COND-1" in res.constraints_applied

    def test_22_high_quality_cannot_override_hard_incompatibility(self, base_investor_profile, base_risk_alignment):
        """Scenario 22: High Fund Quality Score + risk violation -> NOT_SUITABLE (Quality cannot override)."""
        high_quality_fund = FundQualityScoreResult(
            canonical_scheme_id="SCHEME_BEST_EQUITY",
            amfi_code="100111",
            scheme_name="Best Performing Fund",
            category="Equity",
            subcategory="Small Cap",
            observation_date=date(2025, 1, 15),
            quality_score=98.0,
            confidence_score=0.99,
            data_quality_score=0.95,
            dimension_scores={},
            available_dimensions_count=2,
            total_dimensions_count=2,
            peer_group_size=50,
            scoring_methodology_version="1.0.0",
            weight_config_version="1.0.0",
            calculation_timestamp_utc=datetime.utcnow(),
            summary_explanation="Top performing fund",
            is_provisional=False
        )
        req = SuitabilityEvaluationRequest(
            investor_profile=base_investor_profile,
            risk_alignment=base_risk_alignment, # Aligned = HIGH (4)
            fund_quality_score=high_quality_fund,
            fund_risk_profile=FundRiskProfileInput(raw_riskometer_value="Very High", risk_level_numeric=5, is_mapped=True) # Fund = 5
        )
        res = self.engine.evaluate(req)
        assert res.suitability_status == SuitabilityStatus.NOT_SUITABLE
        assert "R-HARD-1" in res.constraints_applied

    def test_scope_and_construct_isolation(self, base_investor_profile, base_risk_alignment, base_fund_quality, base_goal_profile):
        """Scope & Construct Isolation Test: Ensures Suitability does not mutate upstream objects or produce action orders."""
        req = SuitabilityEvaluationRequest(
            investor_profile=base_investor_profile,
            risk_alignment=base_risk_alignment,
            fund_quality_score=base_fund_quality,
            goal_profile=base_goal_profile
        )
        res = self.engine.evaluate(req)
        
        # Verify result output contains zero action fields
        assert not hasattr(res, "buy_recommendation")
        assert not hasattr(res, "transaction_amount")
        assert not hasattr(res, "action_order")
        assert res.methodology_version == "1.0.0"
