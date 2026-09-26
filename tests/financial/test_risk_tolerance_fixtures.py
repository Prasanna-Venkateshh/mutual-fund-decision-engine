"""
Independent Mathematical Test Fixtures for Risk Tolerance Engine (Phase F.3.2).

INDEPENDENT EXPECTED-VALUE FIXTURES:
These expected values are hardcoded / independently computed using pure arithmetic
(outside of production code) to verify mathematical correctness.
Tagged explicitly as SYNTHETIC_TEST_DATA.
"""

from datetime import date
import math
import pytest

from config.risk.tolerance_config import create_test_config
from models.investor_profile import BehavioralToleranceSnapshot, RiskToleranceLevel
from risk.capacity_models import AssessmentStatus
from risk.tolerance_engine import RiskToleranceEngine
from risk.tolerance_models import BehavioralConsistencyLevel


class TestRiskToleranceIndependentFixtures:

    def test_independent_mathematical_fixture_1_very_high_tolerance(self):
        """
        Independent Math Verification Fixture 1 (Very High Tolerance):
        
        Inputs:
          Loss Reaction = "BUY_MORE" (weight = 1.0)
          Stagnation Comfort = "COMFORTABLE_WAITING" (weight = 1.0)
          Historical Drawdown = "BUY_AGGRESSIVELY" (weight = 1.0)
          Volatility Preference = "HIGH_VOLATILITY" (weight = 1.0)
          
        Independent Arithmetic Calculations:
          1. Normalized Signals:
             - loss_reaction = 1.0
             - stagnation_comfort = 1.0
             - historical_drawdown = 1.0
             - volatility_preference = 1.0
             
          2. Raw Score = (1.0 + 1.0 + 1.0 + 1.0) / 4 = 1.0000
          
          3. Consistency:
             - Sample StdDev across [1.0, 1.0, 1.0, 1.0] = 0.0000
             - Consistency Score = 1.0000
             - Level = HIGHLY_CONSISTENT
             
          4. Ordinal Tier Mapping:
             - Score 1.00 >= 0.80 -> VERY_HIGH
             
          5. Assessment Status = COMPLETE
          6. Confidence Score = 1.0 - 0.0 - 0.0 = 1.0000
        """
        cfg = create_test_config()
        engine = RiskToleranceEngine(cfg)

        snapshot = BehavioralToleranceSnapshot(
            observation_date=date(2026, 9, 10),
            assessment_date=date(2026, 9, 10),
            loss_reaction_choice="BUY_MORE",
            stagnation_comfort_choice="INCREASE_EQUITY",
            historical_drawdown_action="INVESTED_MORE",
            volatility_preference="ACCEPT_HIGH_VOLATILITY",
        )


        res = engine.assess_tolerance(
            snapshot,
            investor_id="SYNTHETIC_TEST_DATA_VERY_HIGH",
        )

        assert res.assessment_status == AssessmentStatus.COMPLETE
        assert pytest.approx(res.raw_tolerance_score, abs=1e-5) == 1.0000
        assert res.overall_tolerance_tier == RiskToleranceLevel.VERY_HIGH
        assert res.consistency_level == BehavioralConsistencyLevel.HIGHLY_CONSISTENT
        assert pytest.approx(res.behavioral_consistency_score, abs=1e-5) == 1.0000
        assert pytest.approx(res.confidence_score, abs=1e-5) == 1.0000
        assert "STRONG_LOSS_ACCEPTANCE" in res.explanation_tokens
        assert "HIGH_VOLATILITY_TOLERANCE" in res.explanation_tokens
        assert res.output_tag == "SYNTHETIC_TEST_DATA"

    def test_independent_mathematical_fixture_2_very_low_tolerance(self):
        """
        Independent Math Verification Fixture 2 (Very Low Tolerance):
        
        Inputs:
          Loss Reaction = "SELL_ALL" (weight = 0.0)
          Stagnation Comfort = "EXIT" (weight = 0.0)
          Historical Drawdown = "PANIC_SOLD" (weight = 0.0)
          Volatility Preference = "AVOID_VOLATILITY" (weight = 0.0)
          
        Independent Arithmetic Calculations:
          1. Normalized Signals: all 0.0
          2. Raw Score = 0.0000
          3. Consistency: Sample StdDev = 0.0000 -> HIGHLY_CONSISTENT
          4. Ordinal Tier Mapping: Score 0.00 < 0.20 -> VERY_LOW
          5. Assessment Status = COMPLETE
          6. Confidence Score = 1.0000
        """
        cfg = create_test_config()
        engine = RiskToleranceEngine(cfg)

        snapshot = BehavioralToleranceSnapshot(
            observation_date=date(2026, 9, 10),
            assessment_date=date(2026, 9, 10),
            loss_reaction_choice="SELL_ALL",
            stagnation_comfort_choice="EXIT",
            historical_drawdown_action="PANIC_SOLD",
            volatility_preference="AVOID_VOLATILITY",
        )

        res = engine.assess_tolerance(
            snapshot,
            investor_id="SYNTHETIC_TEST_DATA_VERY_LOW",
        )

        assert res.assessment_status == AssessmentStatus.COMPLETE
        assert pytest.approx(res.raw_tolerance_score, abs=1e-5) == 0.0000
        assert res.overall_tolerance_tier == RiskToleranceLevel.VERY_LOW
        assert res.consistency_level == BehavioralConsistencyLevel.HIGHLY_CONSISTENT
        assert "LOW_LOSS_ACCEPTANCE" in res.explanation_tokens
        assert "LOW_VOLATILITY_TOLERANCE" in res.explanation_tokens

    def test_independent_mathematical_fixture_3_inconsistent_responses(self):
        """
        Independent Math Verification Fixture 3 (Material Inconsistency):
        
        Inputs:
          Loss Reaction = "BUY_MORE" (weight = 1.0)
          Stagnation Comfort = "EXIT" (weight = 0.0)
          Historical Drawdown = "INVESTED_MORE" (weight = 1.0)
          Volatility Preference = "AVOID_VOLATILITY" (weight = 0.0)
          
        Independent Arithmetic Calculations:
          1. Normalized Signals: [1.0, 0.0, 1.0, 0.0]
          2. Mean = (1.0 + 0.0 + 1.0 + 0.0) / 4 = 0.5000
          3. Variance = [(1.0-0.5)^2 + (0.0-0.5)^2 + (1.0-0.5)^2 + (0.0-0.5)^2] / 3
                      = [0.25 + 0.25 + 0.25 + 0.25] / 3 = 1.0 / 3 = 0.333333
          4. Sample StdDev = sqrt(1.0/3) = 0.57735
          5. Inconsistency Thresholds:
             StdDev 0.57735 >= 0.40 -> MATERIALLY_INCONSISTENT
          6. Consistency Score = 1.0 - 0.57735 = 0.42265
          7. Ordinal Tier Mapping: Score 0.5000 -> MODERATE
          8. Confidence Score:
             Base 1.0 - Missing 0.0 - Inconsistency (0.20 * 2 = 0.40) = 0.6000
        """
        cfg = create_test_config()
        engine = RiskToleranceEngine(cfg)

        snapshot = BehavioralToleranceSnapshot(
            observation_date=date(2026, 9, 10),
            assessment_date=date(2026, 9, 10),
            loss_reaction_choice="BUY_MORE",
            stagnation_comfort_choice="EXIT",
            historical_drawdown_action="INVESTED_MORE",
            volatility_preference="AVOID_VOLATILITY",
        )

        res = engine.assess_tolerance(
            snapshot,
            investor_id="SYNTHETIC_TEST_DATA_INCONSISTENT",
        )

        assert res.assessment_status == AssessmentStatus.COMPLETE
        assert pytest.approx(res.raw_tolerance_score, abs=1e-5) == 0.5000
        assert res.overall_tolerance_tier == RiskToleranceLevel.MODERATE
        assert res.consistency_level == BehavioralConsistencyLevel.MATERIALLY_INCONSISTENT
        expected_stddev = math.sqrt(1.0 / 3.0)
        assert pytest.approx(res.behavioral_consistency_score, abs=1e-4) == (1.0 - expected_stddev)
        assert pytest.approx(res.confidence_score, abs=1e-4) == 0.6000
        assert "INCONSISTENT_BEHAVIORAL_RESPONSES" in res.explanation_tokens

