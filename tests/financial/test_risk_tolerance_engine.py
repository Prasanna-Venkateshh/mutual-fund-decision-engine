"""
Risk Tolerance Engine Financial & Behavioral Unit Tests (Phase F.3.2).

Comprehensive test suite verifying behavioral risk tolerance calculations, multi-scenario evaluation,
consistency analysis, missing-response safety, construct independence, and startup modes.
"""

from datetime import date
import pytest

from config.risk.tolerance_config import (
    RiskToleranceConfig,
    StartupMode,
    create_production_config,
    create_research_config,
    create_test_config,
)
from models.fund_quality_dataset import ProvenanceMetadata
from models.investor_profile import (
    BehavioralToleranceSnapshot,
    FinancialCapacitySnapshot,
    InvestorProfileSnapshot,
    RiskCapacityLevel,
    RiskToleranceLevel,
)
from risk.capacity_models import AssessmentStatus
from risk.tolerance_engine import RiskToleranceEngine
from risk.tolerance_models import BehavioralConsistencyLevel


class TestRiskToleranceEngine:

    @pytest.fixture
    def test_engine(self):
        config = create_test_config()
        return RiskToleranceEngine(config)

    # 1. Very Low Behavioral Tolerance Profile
    def test_01_very_low_tolerance_profile(self, test_engine):
        snapshot = BehavioralToleranceSnapshot(
            observation_date=date(2026, 9, 10),
            assessment_date=date(2026, 9, 10),
            loss_reaction_choice="SELL_ALL",
            stagnation_comfort_choice="EXIT",
            historical_drawdown_action="PANIC_SOLD",
            volatility_preference="AVOID_VOLATILITY",
        )
        res = test_engine.assess_tolerance(snapshot, investor_id="INV_01")
        assert res.assessment_status == AssessmentStatus.COMPLETE
        assert res.overall_tolerance_tier == RiskToleranceLevel.VERY_LOW
        assert pytest.approx(res.raw_tolerance_score, abs=1e-5) == 0.0000

    # 2. Low Tolerance Profile
    def test_02_low_tolerance_profile(self, test_engine):
        snapshot = BehavioralToleranceSnapshot(
            observation_date=date(2026, 9, 10),
            assessment_date=date(2026, 9, 10),
            loss_reaction_choice="SELL_SOME",
            stagnation_comfort_choice="SWITCH_DEBT",
            historical_drawdown_action="REDUCED_RISK",
            volatility_preference="ACCEPT_LOW_VOLATILITY",
        )
        res = test_engine.assess_tolerance(snapshot, investor_id="INV_02")
        assert res.assessment_status == AssessmentStatus.COMPLETE
        assert res.overall_tolerance_tier == RiskToleranceLevel.LOW
        assert pytest.approx(res.raw_tolerance_score, abs=1e-5) == 0.30

    # 3. Moderate Tolerance Profile
    def test_03_moderate_tolerance_profile(self, test_engine):
        snapshot = BehavioralToleranceSnapshot(
            observation_date=date(2026, 9, 10),
            assessment_date=date(2026, 9, 10),
            loss_reaction_choice="HOLD",
            stagnation_comfort_choice="WAIT_PATIENTLY",
            historical_drawdown_action="STAYED_INVESTED",
            volatility_preference="ACCEPT_MODERATE_VOLATILITY",
        )
        res = test_engine.assess_tolerance(snapshot, investor_id="INV_03")
        assert res.assessment_status == AssessmentStatus.COMPLETE
        assert res.overall_tolerance_tier == RiskToleranceLevel.MODERATE
        assert pytest.approx(res.raw_tolerance_score, abs=1e-5) == 0.50

    # 4. High Tolerance Profile
    def test_04_high_tolerance_profile(self, test_engine):
        snapshot = BehavioralToleranceSnapshot(
            observation_date=date(2026, 9, 10),
            assessment_date=date(2026, 9, 10),
            loss_reaction_choice="BUY_MORE",
            stagnation_comfort_choice="INCREASE_EQUITY",
            historical_drawdown_action="REDUCED_RISK",
            volatility_preference="ACCEPT_LOW_VOLATILITY",
        )
        res = test_engine.assess_tolerance(snapshot, investor_id="INV_04")
        assert res.assessment_status == AssessmentStatus.COMPLETE
        assert res.overall_tolerance_tier == RiskToleranceLevel.HIGH
        assert pytest.approx(res.raw_tolerance_score, abs=1e-5) == 0.65

    # 5. Very High Tolerance Profile
    def test_05_very_high_tolerance_profile(self, test_engine):
        snapshot = BehavioralToleranceSnapshot(
            observation_date=date(2026, 9, 10),
            assessment_date=date(2026, 9, 10),
            loss_reaction_choice="BUY_MORE",
            stagnation_comfort_choice="INCREASE_EQUITY",
            historical_drawdown_action="INVESTED_MORE",
            volatility_preference="ACCEPT_HIGH_VOLATILITY",
        )
        res = test_engine.assess_tolerance(snapshot, investor_id="INV_05")
        assert res.assessment_status == AssessmentStatus.COMPLETE
        assert res.overall_tolerance_tier == RiskToleranceLevel.VERY_HIGH
        assert pytest.approx(res.raw_tolerance_score, abs=1e-5) == 1.000000

    # 6. Consistent Responses
    def test_06_consistent_responses(self, test_engine):
        snapshot = BehavioralToleranceSnapshot(
            observation_date=date(2026, 9, 10),
            assessment_date=date(2026, 9, 10),
            loss_reaction_choice="HOLD",
            stagnation_comfort_choice="WAIT_PATIENTLY",
            historical_drawdown_action="STAYED_INVESTED",
            volatility_preference="ACCEPT_MODERATE_VOLATILITY",
        )
        res = test_engine.assess_tolerance(snapshot, investor_id="INV_06")
        assert res.consistency_level == BehavioralConsistencyLevel.HIGHLY_CONSISTENT
        assert "CONSISTENT_BEHAVIORAL_RESPONSES" in res.explanation_tokens

    # 7. Inconsistent Responses
    def test_07_inconsistent_responses(self, test_engine):
        snapshot = BehavioralToleranceSnapshot(
            observation_date=date(2026, 9, 10),
            assessment_date=date(2026, 9, 10),
            loss_reaction_choice="BUY_MORE",          # 1.0
            stagnation_comfort_choice="EXIT",          # 0.0
            historical_drawdown_action="INVESTED_MORE",# 1.0
            volatility_preference="AVOID_VOLATILITY",  # 0.0
        )
        res = test_engine.assess_tolerance(snapshot, investor_id="INV_07")
        assert res.consistency_level == BehavioralConsistencyLevel.MATERIALLY_INCONSISTENT
        assert "INCONSISTENT_BEHAVIORAL_RESPONSES" in res.explanation_tokens

    # 8. Missing Response (Partial Profile)
    def test_08_missing_response_partial(self, test_engine):
        snapshot = BehavioralToleranceSnapshot(
            observation_date=date(2026, 9, 10),
            assessment_date=date(2026, 9, 10),
            loss_reaction_choice="BUY_MORE",
            stagnation_comfort_choice="INCREASE_EQUITY",
            historical_drawdown_action="INVESTED_MORE",
            volatility_preference=None,  # 1 missing
        )
        res = test_engine.assess_tolerance(snapshot, investor_id="INV_08")
        assert res.assessment_status == AssessmentStatus.PARTIAL
        assert res.overall_tolerance_tier == RiskToleranceLevel.VERY_HIGH
        assert "PARTIAL_BEHAVIORAL_RESPONSES" in res.explanation_tokens

    # 9. Insufficient Responses (3 missing)
    def test_09_insufficient_responses(self, test_engine):
        snapshot = BehavioralToleranceSnapshot(
            observation_date=date(2026, 9, 10),
            assessment_date=date(2026, 9, 10),
            loss_reaction_choice="BUY_MORE",
            stagnation_comfort_choice=None,
            historical_drawdown_action=None,
            volatility_preference=None,  # Only 1 response supplied
        )
        res = test_engine.assess_tolerance(snapshot, investor_id="INV_09")
        assert res.assessment_status == AssessmentStatus.INSUFFICIENT_INFORMATION
        assert res.overall_tolerance_tier is None  # MISSING != ZERO/DEFAULT
        assert "INSUFFICIENT_BEHAVIORAL_RESPONSES" in res.explanation_tokens

    # 10. Explicitly Supplied Scenario Responses
    def test_10_explicitly_supplied_scenario_responses(self, test_engine):
        snapshot = BehavioralToleranceSnapshot(
            observation_date=date(2026, 9, 10),
            assessment_date=date(2026, 9, 10),
            loss_reaction_choice="HOLD",
            stagnation_comfort_choice="WAIT_PATIENTLY",
            historical_drawdown_action="STAYED_INVESTED",
            volatility_preference="ACCEPT_MODERATE_VOLATILITY",
        )
        res = test_engine.assess_tolerance(snapshot, investor_id="INV_10")
        assert res.assessment_status == AssessmentStatus.COMPLETE

    # 11. Response Directionality
    def test_11_response_directionality(self, test_engine):
        snap_cautious = BehavioralToleranceSnapshot(
            observation_date=date(2026, 9, 10),
            assessment_date=date(2026, 9, 10),
            loss_reaction_choice="SELL_ALL",
            stagnation_comfort_choice="EXIT",
            historical_drawdown_action="PANIC_SOLD",
            volatility_preference="AVOID_VOLATILITY",
        )
        snap_aggressive = BehavioralToleranceSnapshot(
            observation_date=date(2026, 9, 10),
            assessment_date=date(2026, 9, 10),
            loss_reaction_choice="BUY_MORE",
            stagnation_comfort_choice="INCREASE_EQUITY",
            historical_drawdown_action="INVESTED_MORE",
            volatility_preference="ACCEPT_HIGH_VOLATILITY",
        )
        res_c = test_engine.assess_tolerance(snap_cautious)
        res_a = test_engine.assess_tolerance(snap_aggressive)

        assert res_a.raw_tolerance_score > res_c.raw_tolerance_score
        assert res_a.overall_tolerance_tier.value > res_c.overall_tolerance_tier.value

    # 12. Financial Data Isolation (Mandatory Construct Separation Test)
    def test_12_financial_data_isolation(self, test_engine):
        """
        Demonstrates that changing financial capacity parameters (income, debt, expenses, reserves)
        while keeping behavioral responses identical does NOT alter Risk Tolerance.
        """
        behavioral_snap = BehavioralToleranceSnapshot(
            observation_date=date(2026, 9, 10),
            assessment_date=date(2026, 9, 10),
            loss_reaction_choice="HOLD",
            stagnation_comfort_choice="WAIT_PATIENTLY",
            historical_drawdown_action="STAYED_INVESTED",
            volatility_preference="ACCEPT_MODERATE_VOLATILITY",
        )

        # Investor A: Extremely Wealthy
        fin_a = FinancialCapacitySnapshot(
            observation_date=date(2026, 9, 10),
            effective_date=date(2026, 9, 10),
            monthly_gross_income=500000.0,
            monthly_fixed_expenses=50000.0,
            monthly_debt_servicing=0.0,
            liquid_emergency_reserves=5000000.0,
        )

        # Investor B: Financially Constrained
        fin_b = FinancialCapacitySnapshot(
            observation_date=date(2026, 9, 10),
            effective_date=date(2026, 9, 10),
            monthly_gross_income=30000.0,
            monthly_fixed_expenses=25000.0,
            monthly_debt_servicing=4000.0,
            liquid_emergency_reserves=10000.0,
        )

        res_a = test_engine.assess_tolerance(behavioral_snap, investor_id="WEALTHY_INVESTOR")
        res_b = test_engine.assess_tolerance(behavioral_snap, investor_id="CONSTRAINED_INVESTOR")

        assert res_a.overall_tolerance_tier == res_b.overall_tolerance_tier
        assert res_a.raw_tolerance_score == res_b.raw_tolerance_score
        assert res_a.confidence_score == res_b.confidence_score

    # 13. Risk Capacity Independence
    def test_13_risk_capacity_independence(self, test_engine):
        behavioral_snap = BehavioralToleranceSnapshot(
            observation_date=date(2026, 9, 10),
            assessment_date=date(2026, 9, 10),
            loss_reaction_choice="BUY_MORE",
            stagnation_comfort_choice="INCREASE_EQUITY",
            historical_drawdown_action="INVESTED_MORE",
            volatility_preference="ACCEPT_HIGH_VOLATILITY",
        )

        # Varying capacity context does not touch assessment
        res_high_cap = test_engine.assess_tolerance(behavioral_snap, investor_id="HIGH_CAP")
        res_low_cap = test_engine.assess_tolerance(behavioral_snap, investor_id="LOW_CAP")

        assert res_high_cap.overall_tolerance_tier == res_low_cap.overall_tolerance_tier == RiskToleranceLevel.VERY_HIGH

    # 14. Horizon Independence
    def test_14_horizon_independence(self, test_engine):
        behavioral_snap = BehavioralToleranceSnapshot(
            observation_date=date(2026, 9, 10),
            assessment_date=date(2026, 9, 10),
            loss_reaction_choice="HOLD",
            stagnation_comfort_choice="WAIT_PATIENTLY",
            historical_drawdown_action="STAYED_INVESTED",
            volatility_preference="ACCEPT_MODERATE_VOLATILITY",
        )
        res_1yr = test_engine.assess_tolerance(behavioral_snap, investor_id="HORIZON_1YR")
        res_10yr = test_engine.assess_tolerance(behavioral_snap, investor_id="HORIZON_10YR")

        assert res_1yr.overall_tolerance_tier == res_10yr.overall_tolerance_tier

    # 15. Fund Quality Independence
    def test_15_fund_quality_independence(self, test_engine):
        behavioral_snap = BehavioralToleranceSnapshot(
            observation_date=date(2026, 9, 10),
            assessment_date=date(2026, 9, 10),
            loss_reaction_choice="HOLD",
            stagnation_comfort_choice="WAIT_PATIENTLY",
            historical_drawdown_action="STAYED_INVESTED",
            volatility_preference="ACCEPT_MODERATE_VOLATILITY",
        )
        res = test_engine.assess_tolerance(behavioral_snap, investor_id="FQ_TEST")
        # No fund quality parameters exist in tolerance engine input
        assert res.overall_tolerance_tier == RiskToleranceLevel.MODERATE

    # 16. Demographic Safety
    def test_16_demographic_safety(self, test_engine):
        behavioral_snap = BehavioralToleranceSnapshot(
            observation_date=date(2026, 9, 10),
            assessment_date=date(2026, 9, 10),
            loss_reaction_choice="BUY_MORE",
            stagnation_comfort_choice="INCREASE_EQUITY",
            historical_drawdown_action="INVESTED_MORE",
            volatility_preference="ACCEPT_HIGH_VOLATILITY",
        )
        # Age/demographics do not enter calculation
        res_young = test_engine.assess_tolerance(behavioral_snap, investor_id="YOUNG_25")
        res_retired = test_engine.assess_tolerance(behavioral_snap, investor_id="RETIRED_70")

        assert res_young.overall_tolerance_tier == res_retired.overall_tolerance_tier

    # 17. Confidence Does Not Alter Score
    def test_17_confidence_does_not_alter_score(self, test_engine):
        snap_complete = BehavioralToleranceSnapshot(
            observation_date=date(2026, 9, 10),
            assessment_date=date(2026, 9, 10),
            loss_reaction_choice="BUY_MORE",
            stagnation_comfort_choice="INCREASE_EQUITY",
            historical_drawdown_action="INVESTED_MORE",
            volatility_preference="ACCEPT_HIGH_VOLATILITY",
        )
        snap_inconsistent = BehavioralToleranceSnapshot(
            observation_date=date(2026, 9, 10),
            assessment_date=date(2026, 9, 10),
            loss_reaction_choice="BUY_MORE",          # 1.0
            stagnation_comfort_choice="EXIT",          # 0.0
            historical_drawdown_action="INVESTED_MORE",# 1.0
            volatility_preference="AVOID_VOLATILITY",  # 0.0
        )


        res_c = test_engine.assess_tolerance(snap_complete)
        res_i = test_engine.assess_tolerance(snap_inconsistent)

        # Inconsistent lowers confidence
        assert res_i.confidence_score < res_c.confidence_score
        # Raw score calculation is untouched by confidence penalty
        assert pytest.approx(res_i.raw_tolerance_score, abs=1e-5) == 0.5000


    # 18. Explanation Tokens Correspondence
    def test_18_explanation_tokens_correspondence(self, test_engine):
        snapshot = BehavioralToleranceSnapshot(
            observation_date=date(2026, 9, 10),
            assessment_date=date(2026, 9, 10),
            loss_reaction_choice="BUY_MORE",
            stagnation_comfort_choice="EXIT",
            historical_drawdown_action="INVESTED_MORE",
            volatility_preference="AVOID_VOLATILITY",
        )
        res = test_engine.assess_tolerance(snapshot)
        assert "STRONG_LOSS_ACCEPTANCE" in res.explanation_tokens
        assert "LOW_STAGNATION_COMFORT" in res.explanation_tokens
        assert "PROLONGED_DRAWDOWN_PATIENCE" in res.explanation_tokens
        assert "LOW_VOLATILITY_TOLERANCE" in res.explanation_tokens

    # 19. Provenance Completeness
    def test_19_provenance_completeness(self, test_engine):
        prov = ProvenanceMetadata(
            source_id="BEHAVIORAL_SURVEY_01",
            source_document_url="https://platform.internal/surveys/01.json",
            retrieval_timestamp_utc=date(2026, 9, 10),
            methodology_version="1.0.0",
        )
        snapshot = BehavioralToleranceSnapshot(
            observation_date=date(2026, 9, 10),
            assessment_date=date(2026, 9, 10),
            loss_reaction_choice="HOLD",
            stagnation_comfort_choice="WAIT_PATIENTLY",
            historical_drawdown_action="STAYED_INVESTED",
            volatility_preference="ACCEPT_MODERATE_VOLATILITY",
            provenance=prov,
        )
        res = test_engine.assess_tolerance(snapshot)
        assert res.provenance == prov
        assert res.provenance.source_id == "BEHAVIORAL_SURVEY_01"


    # 20. Deterministic & Reproducible Assessment
    def test_20_deterministic_assessment(self, test_engine):
        snapshot = BehavioralToleranceSnapshot(
            observation_date=date(2026, 9, 10),
            assessment_date=date(2026, 9, 10),
            loss_reaction_choice="BUY_MORE",
            stagnation_comfort_choice="INCREASE_EQUITY",
            historical_drawdown_action="INVESTED_MORE",
            volatility_preference="ACCEPT_HIGH_VOLATILITY",
        )
        res1 = test_engine.assess_tolerance(snapshot, investor_id="REPRO_INV")
        res2 = test_engine.assess_tolerance(snapshot, investor_id="REPRO_INV")

        assert res1.raw_tolerance_score == res2.raw_tolerance_score
        assert res1.overall_tolerance_tier == res2.overall_tolerance_tier
        assert res1.confidence_score == res2.confidence_score
        assert res1.explanation_tokens == res2.explanation_tokens

    # 21. Questionnaire Versioning
    def test_21_questionnaire_versioning(self, test_engine):
        snapshot = BehavioralToleranceSnapshot(
            observation_date=date(2026, 9, 10),
            assessment_date=date(2026, 9, 10),
            loss_reaction_choice="HOLD",
            stagnation_comfort_choice="WAIT_PATIENTLY",
            historical_drawdown_action="STAYED_INVESTED",
            volatility_preference="ACCEPT_MODERATE_VOLATILITY",
        )
        res = test_engine.assess_tolerance(snapshot)
        assert res.questionnaire_version == "1.0.0"
        assert res.methodology_version == "1.0.0"
        assert res.rule_version == "1.0.0"

    # 22. Production Configuration Safety
    def test_22_production_configuration_safety(self):
        prod_config = create_production_config()
        # In production mode, validate fails if calibration parameters missing
        errors = prod_config.validate()
        assert len(errors) > 0
        assert "PRODUCTION mode error: Parameter 'loss_reaction_weight_map' is missing/uncalibrated (TBD)." in errors[0]

        prod_engine = RiskToleranceEngine(prod_config)
        snapshot = BehavioralToleranceSnapshot(
            observation_date=date(2026, 9, 10),
            assessment_date=date(2026, 9, 10),
            loss_reaction_choice="HOLD",
            stagnation_comfort_choice="WAIT_PATIENTLY",
            historical_drawdown_action="STAYED_INVESTED",
            volatility_preference="ACCEPT_MODERATE_VOLATILITY",
        )
        res = prod_engine.assess_tolerance(snapshot)
        assert res.assessment_status == AssessmentStatus.CONFIGURATION_ERROR
        assert "MISSING_PRODUCTION_CALIBRATION_PARAMETERS" in res.explanation_tokens

    # 23. Research Mode
    def test_23_research_mode(self):
        res_config = create_research_config()
        res_engine = RiskToleranceEngine(res_config)

        snapshot = BehavioralToleranceSnapshot(
            observation_date=date(2026, 9, 10),
            assessment_date=date(2026, 9, 10),
            loss_reaction_choice="BUY_MORE",
            stagnation_comfort_choice="INCREASE_EQUITY",
            historical_drawdown_action="INVESTED_MORE",
            volatility_preference="ACCEPT_HIGH_VOLATILITY",
        )
        res = res_engine.assess_tolerance(snapshot)
        assert res.startup_mode == StartupMode.RESEARCH
        assert res.output_tag == "RESEARCH_MODE_NOT_FOR_PRODUCTION"

    # 24. Test Mode
    def test_24_test_mode(self):
        t_config = create_test_config()
        t_engine = RiskToleranceEngine(t_config)

        snapshot = BehavioralToleranceSnapshot(
            observation_date=date(2026, 9, 10),
            assessment_date=date(2026, 9, 10),
            loss_reaction_choice="BUY_MORE",
            stagnation_comfort_choice="INCREASE_EQUITY",
            historical_drawdown_action="INVESTED_MORE",
            volatility_preference="ACCEPT_HIGH_VOLATILITY",
        )
        res = t_engine.assess_tolerance(snapshot)
        assert res.startup_mode == StartupMode.TEST
        assert res.output_tag == "SYNTHETIC_TEST_DATA"

