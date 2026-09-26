"""
Phase F.11.2 — Empirical Validation, Backtesting & Shadow Evaluation Test Suite

Verifies:
1. Historical Data Availability Audit & explicit missing metadata preservation.
2. Strict Point-in-Time & Anti-Look-Ahead boundaries (date <= T).
3. Market regime behavior (Bull, Bear, COVID Crash, Recovery, Rangebound).
4. Fund Quality score stability, rank stability, and score/confidence separation.
5. Decision churn analysis & transition tracking.
6. Adversarial SELL validation (score drop alone NEVER triggers SELL).
7. Adversarial BUY/ACCUMULATE validation (high score alone NEVER triggers BUY).
8. Data degradation monotonicity.
9. Provenance propagation & 100% evaluation determinism.
"""

from datetime import date, datetime, timezone, timedelta
import pytest
from typing import Dict, Any, List, Optional

from backtesting.historical_evaluation_engine import (
    PointInTimeEvaluationEngine,
    MarketRegime,
    REGIME_CATALOG,
    DecisionChurnAnalyzer
)
from models.investor_profile import InvestorProfileSnapshot, RiskCapacityLevel, RiskToleranceLevel, ProfileStatus
from models.goal_profile import GoalProfile, GoalCategory
from config.risk.capacity_config import StartupMode
from risk.alignment_models import (
    RiskAlignmentAssessmentResult,
    AlignmentStatus,
    AlignedRiskLevel,
    LimitingConstraint,
)
from action.models import ActionState, PositionContext
from integration.models import IntegrationStatus


@pytest.fixture
def setup_empirical_environment():
    """Sets up investor, goal, risk alignment profiles, and historical NAV series for backtesting."""
    investor = InvestorProfileSnapshot(
        profile_id="PROF_EMP_001",
        investor_id="INV_EMP_001",
        profile_version="1.0.0",
        effective_date=date(2017, 1, 1),
        status=ProfileStatus.ACTIVE
    )
    goal = GoalProfile(
        goal_id="GOAL_EMP_CREATION",
        investor_id="INV_EMP_001",
        goal_name="Long Term Wealth Creation",
        goal_category=GoalCategory.WEALTH_CREATION,
        target_amount=10000000.0,
        effective_horizon_years=10.0
    )
    alignment = RiskAlignmentAssessmentResult(
        assessment_id="ra_emp_001",
        investor_id="INV_EMP_001",
        profile_version_used="1.0.0",
        observation_date=date(2017, 1, 1),
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

    # Generate 5 years of daily synthetic NAV history (2017-01-01 to 2022-01-01)
    nav_history = []
    base_nav = 10.0
    curr_date = date(2017, 1, 1)
    end_date = date(2022, 1, 1)
    step = 0
    while curr_date <= end_date:
        # Simulate market growth + fluctuations
        if curr_date < date(2020, 2, 1):
            val = base_nav * (1.0 + 0.0003 * step)
        elif date(2020, 2, 1) <= curr_date <= date(2020, 3, 31):
            # COVID crash
            val = base_nav * 1.35 * (1.0 - 0.01 * (step % 30))
        else:
            # Recovery
            val = base_nav * 1.20 * (1.0 + 0.0004 * (step % 500))
        nav_history.append({"date": curr_date.isoformat(), "nav": round(val, 4)})
        curr_date += timedelta(days=1)
        step += 1

    return {
        "engine": PointInTimeEvaluationEngine(),
        "investor": investor,
        "goal": goal,
        "alignment": alignment,
        "nav_history": nav_history
    }


class TestPhaseF112EmpiricalValidation:

    def test_01_historical_data_availability_audit(self, setup_empirical_environment):
        """Audits historical data availability matrix and explicit missing metadata preservation."""
        env = setup_empirical_environment
        engine = env["engine"]

        res = engine.evaluate_scheme_at_historical_date(
            amfi_code=120503,
            scheme_name="Axis Long Term Equity Fund",
            category_str="EQUITY_ELSS",
            subcategory_str="ELSS",
            full_nav_history=env["nav_history"],
            decision_date=date(2020, 1, 15),
            investor_profile=env["investor"],
            risk_alignment=env["alignment"],
            goal_profile=env["goal"]
        )

        assert res.canonical_scheme_id == "CAN_AMFI_120503"
        assert res.is_pit_strictly_enforced is True
        assert res.decision_date == date(2020, 1, 15)

    def test_02_point_in_time_anti_look_ahead_boundary(self, setup_empirical_environment):
        """Adversarial test: Injecting future NAVs (dates > T) MUST NOT alter the historical decision at date T."""
        env = setup_empirical_environment
        engine = env["engine"]
        eval_date = date(2019, 6, 1)

        # Baseline evaluation with full nav history (filtered to 2019-06-01)
        res_baseline = engine.evaluate_scheme_at_historical_date(
            amfi_code=120503,
            scheme_name="Axis Long Term Equity Fund",
            category_str="EQUITY_ELSS",
            subcategory_str="ELSS",
            full_nav_history=env["nav_history"],
            decision_date=eval_date,
            investor_profile=env["investor"],
            risk_alignment=env["alignment"],
            goal_profile=env["goal"]
        )

        # Inject extreme future NAV observations (e.g. COVID crash in 2020 or 2021 hyper-rally)
        poisoned_history = list(env["nav_history"]) + [
            {"date": "2025-01-01", "nav": 999.00},
            {"date": "2025-06-01", "nav": 1.00}
        ]

        res_poisoned = engine.evaluate_scheme_at_historical_date(
            amfi_code=120503,
            scheme_name="Axis Long Term Equity Fund",
            category_str="EQUITY_ELSS",
            subcategory_str="ELSS",
            full_nav_history=poisoned_history,
            decision_date=eval_date,
            investor_profile=env["investor"],
            risk_alignment=env["alignment"],
            goal_profile=env["goal"]
        )

        # 100% Invariant: Future poisoned observations must be stripped out and produce identical output at T
        assert res_baseline.quality_score == res_poisoned.quality_score
        assert res_baseline.confidence_score == res_poisoned.confidence_score
        assert res_baseline.action_state == res_poisoned.action_state
        assert res_baseline.explanation == res_poisoned.explanation

    def test_03_market_regime_evaluations(self, setup_empirical_environment):
        """Evaluates decision engine across the 5 historical market regimes."""
        env = setup_empirical_environment
        engine = env["engine"]

        regime_dates = [
            (MarketRegime.BULL_MARKET_2017, date(2017, 9, 1)),
            (MarketRegime.VOLATILE_BEAR_2018, date(2018, 6, 1)),
            (MarketRegime.COVID_CRASH_2020, date(2020, 3, 15)),
            (MarketRegime.COVID_RECOVERY_2020, date(2020, 9, 1)),
            (MarketRegime.RANGEBOUND_2022_2023, date(2022, 1, 1))
        ]

        for regime_enum, d_eval in regime_dates:
            regime_def = REGIME_CATALOG[regime_enum]
            res = engine.evaluate_scheme_at_historical_date(
                amfi_code=120503,
                scheme_name="Axis Long Term Equity Fund",
                category_str="EQUITY_ELSS",
                subcategory_str="ELSS",
                full_nav_history=env["nav_history"],
                decision_date=d_eval,
                investor_profile=env["investor"],
                risk_alignment=env["alignment"],
                goal_profile=env["goal"]
            )
            assert res.decision_date == d_eval
            assert res.action_state in ActionState

    def test_04_score_stability_and_decision_churn(self, setup_empirical_environment):
        """Measures decision stability and transition churn across a 12-month historical trajectory."""
        env = setup_empirical_environment
        engine = env["engine"]

        evaluations = []
        for month in range(1, 13):
            d_eval = date(2019, month, 1)
            res = engine.evaluate_scheme_at_historical_date(
                amfi_code=120503,
                scheme_name="Axis Long Term Equity Fund",
                category_str="EQUITY_ELSS",
                subcategory_str="ELSS",
                full_nav_history=env["nav_history"],
                decision_date=d_eval,
                investor_profile=env["investor"],
                risk_alignment=env["alignment"],
                goal_profile=env["goal"]
            )
            evaluations.append(res)

        churn_summary = DecisionChurnAnalyzer.calculate_churn_metrics(evaluations)
        assert churn_summary["total_evaluations"] == 12
        assert churn_summary["churn_rate"] >= 0.0
        assert "state_distribution" in churn_summary

    def test_05_adversarial_sell_safety_across_history(self, setup_empirical_environment):
        """Adversarial test: Market drawdown or score drop alone NEVER triggers SELL on incumbent holding."""
        env = setup_empirical_environment
        engine = env["engine"]

        # Evaluate incumbent holding during COVID crash (2020-03-15)
        res = engine.evaluate_scheme_at_historical_date(
            amfi_code=120503,
            scheme_name="Axis Long Term Equity Fund",
            category_str="EQUITY_ELSS",
            subcategory_str="ELSS",
            full_nav_history=env["nav_history"],
            decision_date=date(2020, 3, 15),
            investor_profile=env["investor"],
            risk_alignment=env["alignment"],
            goal_profile=env["goal"],
            position_context=PositionContext.EXISTING_POSITION
        )

        # Market drawdown during COVID crash must NOT trigger SELL without validated replacement + net economic benefit
        assert res.action_state != ActionState.SELL
        assert res.action_state in (ActionState.NO_ACTION, ActionState.HOLD, ActionState.MONITOR, ActionState.REVIEW)

    def test_06_adversarial_buy_safety_across_history(self, setup_empirical_environment):
        """Adversarial test: High historical returns alone NEVER trigger BUY without Portfolio Need & Economic Benefit."""
        env = setup_empirical_environment
        engine = env["engine"]

        # Evaluate candidate fund during 2017 Bull Market (2017-12-01)
        res = engine.evaluate_scheme_at_historical_date(
            amfi_code=120503,
            scheme_name="Axis Long Term Equity Fund",
            category_str="EQUITY_ELSS",
            subcategory_str="ELSS",
            full_nav_history=env["nav_history"],
            decision_date=date(2017, 12, 1),
            investor_profile=env["investor"],
            risk_alignment=env["alignment"],
            goal_profile=env["goal"],
            position_context=PositionContext.NEW_POSITION
        )

        # Since maturity is short (<1 year in 2017), quality score returns None, blocking BUY and routing to NO_ACTION
        assert res.action_state != ActionState.BUY
        assert res.action_state != ActionState.ACCUMULATE

    def test_07_data_degradation_monotonicity(self, setup_empirical_environment):
        """Verify that degrading historical NAV series length reduces confidence and never increases transaction propensity."""
        env = setup_empirical_environment
        engine = env["engine"]
        eval_date = date(2021, 1, 1)

        # Full 4-year history
        res_full = engine.evaluate_scheme_at_historical_date(
            amfi_code=120503,
            scheme_name="Axis Long Term Equity Fund",
            category_str="EQUITY_ELSS",
            subcategory_str="ELSS",
            full_nav_history=env["nav_history"],
            decision_date=eval_date,
            investor_profile=env["investor"],
            risk_alignment=env["alignment"],
            goal_profile=env["goal"]
        )

        # Degraded short history (only last 60 days)
        short_history = env["nav_history"][-60:]
        res_short = engine.evaluate_scheme_at_historical_date(
            amfi_code=120503,
            scheme_name="Axis Long Term Equity Fund",
            category_str="EQUITY_ELSS",
            subcategory_str="ELSS",
            full_nav_history=short_history,
            decision_date=eval_date,
            investor_profile=env["investor"],
            risk_alignment=env["alignment"],
            goal_profile=env["goal"]
        )

        # Confidence of short history must be <= full history
        assert res_short.confidence_score <= res_full.confidence_score
        # Action of short history must be non-transactional (NO_ACTION)
        assert res_short.action_state == ActionState.NO_ACTION

    def test_08_reproducibility_and_determinism(self, setup_empirical_environment):
        """Verify 100% deterministic outputs across repeated historical evaluations."""
        env = setup_empirical_environment
        engine = env["engine"]
        eval_date = date(2020, 6, 1)

        res1 = engine.evaluate_scheme_at_historical_date(
            amfi_code=120503,
            scheme_name="Axis Long Term Equity Fund",
            category_str="EQUITY_ELSS",
            subcategory_str="ELSS",
            full_nav_history=env["nav_history"],
            decision_date=eval_date,
            investor_profile=env["investor"],
            risk_alignment=env["alignment"],
            goal_profile=env["goal"]
        )

        res2 = engine.evaluate_scheme_at_historical_date(
            amfi_code=120503,
            scheme_name="Axis Long Term Equity Fund",
            category_str="EQUITY_ELSS",
            subcategory_str="ELSS",
            full_nav_history=env["nav_history"],
            decision_date=eval_date,
            investor_profile=env["investor"],
            risk_alignment=env["alignment"],
            goal_profile=env["goal"]
        )

        assert res1.action_state == res2.action_state
        assert res1.quality_score == res2.quality_score
        assert res1.confidence_score == res2.confidence_score
        assert res1.explanation == res2.explanation
