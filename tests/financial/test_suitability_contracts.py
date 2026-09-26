"""
Phase F.2 Data Contracts & Investor Profile Persistence Test Suite.

Tests:
1. Valid FinancialCapacitySnapshot construction & field preservation.
2. Missing financial inputs representation (Missing != 0).
3. Valid BehavioralToleranceSnapshot construction & field preservation.
4. Missing behavioral responses representation.
5. InvestorProfileSnapshot versioning and profile immutability.
6. Multiple GoalProfile objects for same investor.
7. GoalProfile without target amount (is_target_amount_known=False).
8. GoalProfile without target date (is_target_date_known=False).
9. General wealth profile without goals.
10. Valid SuitabilityAssessmentResult construction.
11. Missing/unknown suitability output fields.
12. Provenance & methodology version preservation.
13. Invalid values rejected by contract validation (negative income, invalid confidence bounds, etc.).
14. SQLite persistence, query retrieval, and serialization round-trip.
15. Verification that no financial risk calculations occur inside contracts.
"""

from datetime import date, datetime, timezone
import sqlite3
import pytest

from models.fund_quality_dataset import ProvenanceMetadata
from models.investor_profile import (
    FinancialCapacitySnapshot,
    BehavioralToleranceSnapshot,
    InvestorProfileSnapshot,
    RiskCapacityLevel,
    RiskToleranceLevel,
    ProfileStatus
)
from models.goal_profile import GoalProfile, GoalCategory, GoalPriority
from models.suitability_assessment import SuitabilityAssessmentResult, SuitabilityStatus
from data.repositories.suitability_repository import SuitabilityRepository


class TestSuitabilityContracts:
    """Test suite for Phase F.2 data contracts and persistence repository."""

    @pytest.fixture
    def db_conn(self):
        conn = sqlite3.connect(":memory:")
        yield conn
        conn.close()

    @pytest.fixture
    def mock_provenance(self):
        return ProvenanceMetadata(
            source_id="USER_DECLARED",
            source_document_url="app://user/profile",
            retrieval_timestamp_utc=datetime.now(timezone.utc),
            methodology_version="1.0.0"
        )

    def test_01_valid_financial_capacity_snapshot(self, mock_provenance):
        fc = FinancialCapacitySnapshot(
            observation_date=date(2023, 1, 1),
            effective_date=date(2023, 1, 1),
            monthly_gross_income=150000.0,
            monthly_fixed_expenses=50000.0,
            monthly_debt_servicing=20000.0,
            liquid_emergency_reserves=300000.0,
            emergency_reserve_months=6.0,
            savings_ratio=0.53,
            sustainable_monthly_capacity=80000.0,
            capacity_tier=RiskCapacityLevel.HIGH,
            confidence_score=0.95,
            provenance=mock_provenance
        )
        assert fc.monthly_gross_income == 150000.0
        assert fc.capacity_tier == RiskCapacityLevel.HIGH
        assert fc.confidence_score == 0.95

    def test_02_missing_financial_inputs_representation(self):
        # Missing values must remain None (Missing != 0)
        fc_missing = FinancialCapacitySnapshot(
            observation_date=date(2023, 1, 1),
            effective_date=date(2023, 1, 1),
            monthly_gross_income=100000.0,
            monthly_fixed_expenses=None,  # Missing
            monthly_debt_servicing=None,  # Missing
            liquid_emergency_reserves=None  # Missing
        )
        assert fc_missing.monthly_fixed_expenses is None
        assert fc_missing.monthly_debt_servicing is None
        assert fc_missing.liquid_emergency_reserves is None

    def test_03_valid_behavioral_tolerance_snapshot(self, mock_provenance):
        bt = BehavioralToleranceSnapshot(
            observation_date=date(2023, 1, 1),
            assessment_date=date(2023, 1, 1),
            loss_reaction_choice="HOLD_AND_WAIT",
            stagnation_comfort_choice="ACCEPT_VOLATILITY",
            tolerance_tier=RiskToleranceLevel.MODERATE,
            behavioral_consistency_score=0.85,
            confidence_score=0.90,
            provenance=mock_provenance
        )
        assert bt.loss_reaction_choice == "HOLD_AND_WAIT"
        assert bt.tolerance_tier == RiskToleranceLevel.MODERATE

    def test_04_missing_behavioral_responses(self):
        bt_missing = BehavioralToleranceSnapshot(
            observation_date=date(2023, 1, 1),
            assessment_date=date(2023, 1, 1),
            loss_reaction_choice=None,  # Unanswered
            tolerance_tier=None
        )
        assert bt_missing.loss_reaction_choice is None
        assert bt_missing.tolerance_tier is None

    def test_05_investor_profile_snapshot_versioning_and_immutability(self, mock_provenance):
        profile = InvestorProfileSnapshot(
            profile_id="prof_001_v1",
            investor_id="inv_123",
            profile_version="1.0.0",
            effective_date=date(2023, 1, 1),
            status=ProfileStatus.ACTIVE,
            profiling_tier_completed=2,
            confidence_score=0.90,
            provenance=mock_provenance
        )
        assert profile.profile_id == "prof_001_v1"
        assert profile.profile_version == "1.0.0"

        # Dataclass is frozen (immutable)
        with pytest.raises(AttributeError):
            profile.status = ProfileStatus.STALE  # type: ignore

    def test_06_multiple_goal_profiles_for_same_investor(self):
        g1 = GoalProfile(
            goal_id="goal_edu_01",
            investor_id="inv_123",
            goal_name="Child Education",
            goal_category=GoalCategory.EDUCATION,
            target_date=date(2028, 6, 1),
            effective_horizon_years=5.0,
            target_amount=2000000.0,
            priority=GoalPriority.HIGH
        )
        g2 = GoalProfile(
            goal_id="goal_ret_01",
            investor_id="inv_123",
            goal_name="Retirement Corpus",
            goal_category=GoalCategory.RETIREMENT,
            target_date=date(2043, 1, 1),
            effective_horizon_years=20.0,
            target_amount=15000000.0,
            priority=GoalPriority.CRITICAL
        )
        assert g1.investor_id == g2.investor_id
        assert g1.goal_id != g2.goal_id
        assert g1.effective_horizon_years == 5.0
        assert g2.effective_horizon_years == 20.0

    def test_07_goal_profile_without_target_amount(self):
        g_noamt = GoalProfile(
            goal_id="goal_wealth_01",
            investor_id="inv_123",
            goal_name="Long Term Wealth",
            goal_category=GoalCategory.WEALTH_CREATION,
            target_date=date(2033, 1, 1),
            effective_horizon_years=10.0,
            target_amount=None,
            is_target_amount_known=False
        )
        assert g_noamt.target_amount is None
        assert g_noamt.is_target_amount_known is False

    def test_08_goal_profile_without_target_date(self):
        g_nodate = GoalProfile(
            goal_id="goal_flex_01",
            investor_id="inv_123",
            goal_name="Flexible Future Goal",
            goal_category=GoalCategory.OTHER,
            target_date=None,
            effective_horizon_years=None,
            is_target_date_known=False
        )
        assert g_nodate.target_date is None
        assert g_nodate.is_target_date_known is False

    def test_09_general_wealth_profile_without_goals(self):
        g_gw = GoalProfile(
            goal_id="goal_gen_wealth",
            investor_id="inv_456",
            goal_name="Surplus Capital Creation",
            goal_category=GoalCategory.GENERAL_WEALTH,
            is_general_wealth=True,
            target_amount=None,
            is_target_amount_known=False,
            is_target_date_known=False
        )
        assert g_gw.is_general_wealth is True
        assert g_gw.goal_category == GoalCategory.GENERAL_WEALTH

    def test_10_valid_suitability_assessment_result(self, mock_provenance):
        res = SuitabilityAssessmentResult(
            assessment_id="eval_999",
            investor_id="inv_123",
            profile_version_used="1.0.0",
            canonical_scheme_id="SCHEME_LARGE_CAP_01",
            amfi_code="100001",
            scheme_name="Test Large Cap Direct Growth",
            category="Equity",
            subcategory="Large Cap",
            observation_date=date(2023, 1, 1),
            suitability_status=SuitabilityStatus.SUITABLE,
            effective_risk_alignment="HIGH_RISK",
            suitability_confidence_score=0.92,
            summary_explanation="Suitable for long-term equity growth objective.",
            provenance=mock_provenance
        )
        assert res.assessment_id == "eval_999"
        assert res.suitability_status == SuitabilityStatus.SUITABLE

    def test_11_missing_unknown_suitability_output_fields(self):
        res_partial = SuitabilityAssessmentResult(
            assessment_id="eval_888",
            investor_id="inv_789",
            profile_version_used="1.0.0",
            canonical_scheme_id="SCHEME_DEBT_01",
            amfi_code="200001",
            scheme_name="Test Liquid Fund",
            category="Debt",
            subcategory="Liquid",
            observation_date=date(2023, 1, 1),
            suitability_status=SuitabilityStatus.INSUFFICIENT_INFORMATION,
            effective_risk_alignment=None,  # Unknown
            suitability_confidence_score=0.40,
            constraints_applied=["MISSING_INCOME_DATA"]
        )
        assert res_partial.effective_risk_alignment is None
        assert "MISSING_INCOME_DATA" in res_partial.constraints_applied

    def test_12_provenance_and_version_preservation(self, mock_provenance):
        res = SuitabilityAssessmentResult(
            assessment_id="eval_777",
            investor_id="inv_123",
            profile_version_used="2.1.0",
            canonical_scheme_id="SCH_1",
            amfi_code="101",
            scheme_name="Scheme",
            category="Equity",
            subcategory="Flexi Cap",
            observation_date=date(2023, 1, 1),
            suitability_status=SuitabilityStatus.SUITABLE,
            provenance=mock_provenance,
            methodology_version="1.0.0",
            rule_version="1.0.0"
        )
        assert res.methodology_version == "1.0.0"
        assert res.rule_version == "1.0.0"
        assert res.provenance.source_id == "USER_DECLARED"

    def test_13_invalid_values_rejected_by_contract_validation(self):
        # Invalid confidence score > 1.0
        with pytest.raises(ValueError, match="confidence_score"):
            FinancialCapacitySnapshot(
                observation_date=date(2023, 1, 1),
                effective_date=date(2023, 1, 1),
                confidence_score=1.5
            )

        # Invalid negative income
        with pytest.raises(ValueError, match="monthly_gross_income"):
            FinancialCapacitySnapshot(
                observation_date=date(2023, 1, 1),
                effective_date=date(2023, 1, 1),
                monthly_gross_income=-50000.0
            )

        # Invalid profiling tier completed
        with pytest.raises(ValueError, match="profiling_tier_completed"):
            InvestorProfileSnapshot(
                profile_id="p1",
                investor_id="inv1",
                profile_version="1.0",
                effective_date=date(2023, 1, 1),
                profiling_tier_completed=5  # Invalid tier
            )

        # Invalid negative target amount
        with pytest.raises(ValueError, match="target_amount"):
            GoalProfile(
                goal_id="g1",
                investor_id="inv1",
                goal_name="Goal",
                goal_category=GoalCategory.HOUSING,
                target_amount=-1000.0
            )

    def test_14_sqlite_persistence_roundtrip(self, db_conn, mock_provenance):
        repo = SuitabilityRepository(db_conn)

        fc = FinancialCapacitySnapshot(
            observation_date=date(2023, 1, 1),
            effective_date=date(2023, 1, 1),
            monthly_gross_income=120000.0,
            capacity_tier=RiskCapacityLevel.MODERATE
        )
        bt = BehavioralToleranceSnapshot(
            observation_date=date(2023, 1, 1),
            assessment_date=date(2023, 1, 1),
            loss_reaction_choice="HOLD_AND_WAIT",
            tolerance_tier=RiskToleranceLevel.MODERATE
        )
        profile = InvestorProfileSnapshot(
            profile_id="p_inv123_v1",
            investor_id="inv_123",
            profile_version="1.0.0",
            effective_date=date(2023, 1, 1),
            financial_capacity=fc,
            behavioral_tolerance=bt,
            overall_effective_risk_alignment=RiskCapacityLevel.MODERATE,
            status=ProfileStatus.ACTIVE,
            provenance=mock_provenance
        )

        goal = GoalProfile(
            goal_id="g_ret_123",
            investor_id="inv_123",
            goal_name="Retirement",
            goal_category=GoalCategory.RETIREMENT,
            target_date=date(2040, 1, 1),
            effective_horizon_years=17.0,
            target_amount=10000000.0
        )

        res = SuitabilityAssessmentResult(
            assessment_id="eval_101",
            investor_id="inv_123",
            profile_version_used="1.0.0",
            canonical_scheme_id="SCH_100",
            amfi_code="100",
            scheme_name="Large Cap Scheme",
            category="Equity",
            subcategory="Large Cap",
            observation_date=date(2023, 1, 1),
            suitability_status=SuitabilityStatus.SUITABLE
        )

        # Save to SQLite
        repo.save_profile_snapshot(profile)
        repo.save_goal_profile(goal)
        repo.save_assessment_result(res)

        # Retrieve and verify roundtrip equivalence
        loaded_profile = repo.get_profile_snapshot("inv_123", "1.0.0")
        assert loaded_profile is not None
        assert loaded_profile.profile_id == "p_inv123_v1"
        assert loaded_profile.financial_capacity.monthly_gross_income == 120000.0

        loaded_goals = repo.get_goal_profiles_for_investor("inv_123")
        assert len(loaded_goals) == 1
        assert loaded_goals[0].goal_name == "Retirement"
        assert loaded_goals[0].target_amount == 10000000.0

        loaded_res = repo.get_assessment_result("eval_101")
        assert loaded_res is not None
        assert loaded_res.suitability_status == SuitabilityStatus.SUITABLE

    def test_15_contracts_contain_no_provisional_calculation_rules(self):
        """
        Verifies that Phase F.2 dataclass contracts contain NO hardcoded financial calculation logic
        or active threshold enforcement (e.g. debt > 60%, reserve < 3 months, lower-of-two rule).
        """
        fc = FinancialCapacitySnapshot(
            observation_date=date(2023, 1, 1),
            effective_date=date(2023, 1, 1),
            monthly_gross_income=100000.0,
            monthly_debt_servicing=70000.0,  # 70% debt servicing ratio
            liquid_emergency_reserves=10000.0  # Under 1 month reserve
        )
        # Contract accepts raw values without altering or enforcing capacity caps
        assert fc.monthly_debt_servicing == 70000.0
        assert fc.capacity_tier is None  # Tier is NOT auto-computed by contract
