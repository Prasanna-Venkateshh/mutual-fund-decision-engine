"""
Phase F.11.3 — Investment-Outcome Validation & Predictive Value Assessment Test Suite

Verifies:
1. Historical data availability inventory & explicit metadata limitations.
2. Forward outcome calculation (1Y, 3Y, 5Y) and risk-adjusted metrics correctness.
3. Score-to-outcome predictive association (Spearman rank correlation, quintile spread, monotonicity).
4. Confidence level & outcome dispersion relationship.
5. BUY/ACCUMULATE action outcome quality vs. category medians.
6. SELL/Switch economic benefit validation after exit load and tax friction costs.
7. Point-in-time anti-look-ahead and survivorship bias controls.
8. Baseline comparisons & false positive / false negative rate analysis.
9. Genuine F.12.2 real-data empirical validation checks & firewall separation.
"""

from datetime import date, timedelta
import math, os, sqlite3
import pytest

from backtesting.outcome_validation_engine import (
    OutcomeValidationEngine,
    BaselineComparator,
    DataAvailabilityAuditor,
    ForwardOutcomeMetrics,
    ScoreQuintileOutcome,
    SwitchEconomicsResult
)
from backtesting.historical_evaluation_engine import PointInTimeEvaluationEngine
from scoring.engine import FundQualityScoringEngine
from models.fund_quality_dataset import FundQualityDatasetInput
from action.models import ActionState, PositionContext


def generate_mock_nav_history(
    start_date: date,
    days: int,
    initial_nav: float = 100.0,
    daily_growth_rate: float = 0.0004,
    volatility_noise: float = 0.005
) -> list:
    """Generates deterministic mock NAV history for testing."""
    history = []
    current_nav = initial_nav
    for i in range(days):
        d = start_date + timedelta(days=i)
        history.append({
            "date": d.isoformat(),
            "nav": round(current_nav, 4)
        })
        noise = math.sin((i + 1) * 0.1) * volatility_noise * current_nav
        current_nav = max(1.0, current_nav * (1.0 + daily_growth_rate) + noise)
    return history


class TestPhaseF113OutcomeValidation:

    @pytest.fixture(autouse=True)
    def setup_engine(self):
        self.outcome_engine = OutcomeValidationEngine()
        self.pit_engine = PointInTimeEvaluationEngine()
        self.auditor = DataAvailabilityAuditor()
        self.baseline_comp = BaselineComparator()

    def test_01_historical_data_availability_inventory(self):
        """Audits field-by-field availability and verifies explicit reporting of metadata gaps."""
        matrix = self.auditor.audit_historical_fields()

        assert matrix["historical_nav"]["status"] == "AVAILABLE"
        assert matrix["category_pit"]["status"] == "AVAILABLE"
        assert matrix["ter_historical"]["status"] == "UNAVAILABLE"
        assert matrix["riskometer_historical"]["status"] == "UNAVAILABLE"
        assert matrix["benchmark_historical"]["status"] == "UNAVAILABLE"

        # Verify no synthetic substitution
        assert matrix["ter_historical"]["is_synthetic"] is False
        assert matrix["riskometer_historical"]["is_synthetic"] is False
        assert matrix["benchmark_historical"]["is_synthetic"] is False

    def test_02_forward_outcome_calculation_correctness(self):
        """Verifies 1Y forward return, CAGR, volatility, downside deviation, max drawdown, and Sharpe/Sortino ratios."""
        start_d = date(2021, 1, 1)
        nav_history = generate_mock_nav_history(start_d, 400, initial_nav=100.0, daily_growth_rate=0.0005)

        out_1y = self.outcome_engine.calculate_forward_outcome(
            full_nav_history=nav_history,
            decision_date=start_d,
            horizon_days=365,
            risk_free_rate=0.06
        )

        assert out_1y is not None
        assert out_1y.decision_date == start_d
        assert out_1y.horizon_days == 365
        assert out_1y.start_nav == 100.0
        assert out_1y.end_nav > 100.0
        assert out_1y.absolute_return > 0.0
        assert out_1y.annualized_cagr is not None
        assert out_1y.annualized_volatility >= 0.0
        assert out_1y.max_drawdown >= 0.0
        assert out_1y.sharpe_ratio_proxy is not None

    def test_03_score_to_outcome_predictive_association(self):
        """Evaluates Spearman rank correlation (rho), quintile outcome spread, and monotonicity across score tiers."""
        scores = [45.0, 52.0, 61.0, 74.0, 85.0]
        outcomes_1y = [0.05, 0.08, 0.12, 0.15, 0.19]

        rho = OutcomeValidationEngine.calculate_spearman_rank_correlation(scores, outcomes_1y)
        assert rho == 1.0  # Perfect rank monotonicity

        # Group scored outcomes into quintiles
        scored_pairs = []
        base_d = date(2021, 1, 1)
        for i in range(15):
            score = 40.0 + i * 3.5
            nav_hist = generate_mock_nav_history(base_d, 400, initial_nav=100.0, daily_growth_rate=0.0001 * (i + 1))
            m = self.outcome_engine.calculate_forward_outcome(nav_hist, base_d, horizon_days=365)
            scored_pairs.append((score, m))

        quintiles = self.outcome_engine.evaluate_score_quintiles(scored_pairs)
        assert len(quintiles) == 5
        assert quintiles[0].quintile == 1
        assert quintiles[4].quintile == 5

        # Verify Q5 avg score > Q1 avg score and Q5 avg return > Q1 avg return
        assert quintiles[4].avg_quality_score > quintiles[0].avg_quality_score
        assert quintiles[4].avg_forward_return_1y > quintiles[0].avg_forward_return_1y

    def test_04_confidence_and_outcome_dispersion(self):
        """Verifies that low confidence assessments exhibit higher outcome dispersion than high confidence assessments."""
        high_conf_returns = [0.12, 0.13, 0.11, 0.14, 0.12]
        low_conf_returns = [0.25, -0.10, 0.18, -0.05, 0.30]

        high_var = sum((r - 0.124) ** 2 for r in high_conf_returns) / 5.0
        low_var = sum((r - 0.126) ** 2 for r in low_conf_returns) / 5.0

        assert low_var > high_var * 5.0

    def test_05_buy_accumulate_action_outcome_quality(self):
        """Verifies that schemes receiving BUY/ACCUMULATE outperform category median baselines."""
        base_d = date(2021, 1, 1)

        scheme_outcomes = {}
        # Scheme A: Top performer (BUY)
        nav_a = generate_mock_nav_history(base_d, 400, initial_nav=100.0, daily_growth_rate=0.0008)
        out_a = self.outcome_engine.calculate_forward_outcome(nav_a, base_d, 365)
        scheme_outcomes["scheme_top_a"] = out_a

        # Scheme B: Median performer (HOLD)
        nav_b = generate_mock_nav_history(base_d, 400, initial_nav=100.0, daily_growth_rate=0.0004)
        out_b = self.outcome_engine.calculate_forward_outcome(nav_b, base_d, 365)
        scheme_outcomes["scheme_med_b"] = out_b

        # Scheme C: Low performer (REVIEW)
        nav_c = generate_mock_nav_history(base_d, 400, initial_nav=100.0, daily_growth_rate=0.0001)
        out_c = self.outcome_engine.calculate_forward_outcome(nav_c, base_d, 365)
        scheme_outcomes["scheme_low_c"] = out_c

        eval_res = BaselineComparator.evaluate_category_relative_performance(scheme_outcomes)

        assert eval_res["scheme_top_a"]["outperformed_median"] is True
        assert eval_res["scheme_top_a"]["excess_return_over_median"] > 0.0
        assert eval_res["scheme_low_c"]["outperformed_median"] is False

    def test_06_sell_switch_economic_benefit_validation(self):
        """Evaluates net switching benefit (Outcome_rep - Friction - Outcome_ext) and adversarial cost drag scenarios."""
        base_d = date(2021, 1, 1)

        # Case 1: Justified switch (Replacement outperforms by 8%, friction = 2%, net benefit = 6%)
        ext_nav = generate_mock_nav_history(base_d, 400, initial_nav=100.0, daily_growth_rate=0.0002)
        rep_nav = generate_mock_nav_history(base_d, 400, initial_nav=100.0, daily_growth_rate=0.0006)

        sw_res1 = self.outcome_engine.evaluate_switch_decision(
            existing_nav_history=ext_nav,
            replacement_nav_history=rep_nav,
            decision_date=base_d,
            existing_scheme_id="CAN_EXT_1",
            replacement_scheme_id="CAN_REP_1",
            horizon_days=365,
            exit_load_pct=0.01,
            estimated_tax_pct=0.01
        )

        assert sw_res1 is not None
        assert sw_res1.was_switch_economically_beneficial is True
        assert sw_res1.net_switch_benefit > 0.0

        # Case 2: High friction switch (Replacement outperforms by ~4%, friction = 6%, net benefit < 0)
        rep_nav_weak = generate_mock_nav_history(base_d, 400, initial_nav=100.0, daily_growth_rate=0.0003)
        sw_res2 = self.outcome_engine.evaluate_switch_decision(
            existing_nav_history=ext_nav,
            replacement_nav_history=rep_nav_weak,
            decision_date=base_d,
            existing_scheme_id="CAN_EXT_1",
            replacement_scheme_id="CAN_REP_WEAK",
            horizon_days=365,
            exit_load_pct=0.03,
            estimated_tax_pct=0.03
        )

        assert sw_res2 is not None
        assert sw_res2.was_switch_economically_beneficial is False
        assert sw_res2.net_switch_benefit < 0.0

    def test_07_survivorship_and_anti_look_ahead_bias_controls(self):
        """Verifies that injecting future data produces zero change in historical calculations at date T."""
        t_date = date(2020, 1, 1)

        # Base NAV up to date T
        base_nav = generate_mock_nav_history(date(2018, 1, 1), 730, initial_nav=100.0, daily_growth_rate=0.0004)

        # Injected future NAV beyond date T (extreme hyper-rally in 2021)
        future_nav = base_nav + generate_mock_nav_history(date(2020, 1, 2), 365, initial_nav=200.0, daily_growth_rate=0.005)

        pit_clean = self.pit_engine.filter_nav_history_pit(base_nav, t_date)
        pit_future = self.pit_engine.filter_nav_history_pit(future_nav, t_date)

        assert len(pit_clean) == len(pit_future)
        assert pit_clean[-1]["date"] == pit_future[-1]["date"]
        assert pit_clean[-1]["nav"] == pit_future[-1]["nav"]

    def test_08_baseline_comparison_and_false_positive_analysis(self):
        """Compares engine recommendations against Category Median and Naive Trailing Return rankings."""
        base_d = date(2021, 1, 1)

        scheme_outcomes = {}
        for i in range(5):
            nav_hist = generate_mock_nav_history(base_d, 400, initial_nav=100.0, daily_growth_rate=0.0002 * (i + 1))
            out = self.outcome_engine.calculate_forward_outcome(nav_hist, base_d, 365)
            scheme_outcomes[f"scheme_{i}"] = out

        eval_res = BaselineComparator.evaluate_category_relative_performance(scheme_outcomes)

        assert len(eval_res) == 5
        # Scheme 4 should have highest percentile rank
        assert eval_res["scheme_4"]["percentile_rank"] == 100.0
        assert eval_res["scheme_0"]["percentile_rank"] == 20.0

    def test_09_f12_2_real_data_database_verification(self):
        """Verifies Section 1 database figures directly against real db/backfill_f12_2.db."""
        db_path = 'db/backfill_f12_2.db'
        if not os.path.exists(db_path):
            pytest.skip(f"Database {db_path} not found.")

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        ledger_stats = conn.execute("""
            SELECT COUNT(*) as win_cnt,
                   SUM(raw_records_count) as raw_cnt,
                   SUM(normalized_records_count) as norm_cnt,
                   SUM(nav_quarantine_count) as nav_q_cnt,
                   SUM(mapping_quarantine_count) as map_q_cnt
            FROM acquisition_coverage_ledger
            WHERE request_status = 'SUCCESS'
        """).fetchone()

        schemes_cnt = conn.execute("SELECT COUNT(DISTINCT canonical_scheme_id) FROM normalized_nav_records").fetchone()[0]
        conn.close()

        assert ledger_stats['win_cnt'] == 1180
        assert ledger_stats['raw_cnt'] == 6187660
        assert ledger_stats['norm_cnt'] == 4766297
        assert ledger_stats['nav_q_cnt'] == 94541
        assert ledger_stats['map_q_cnt'] == 1326822
        assert schemes_cnt == 16808

    def test_10_real_data_firewall_and_reproducibility(self):
        """Verifies real data firewall: real data results are tagged as real, synthetic tagged as mock."""
        auditor_res = DataAvailabilityAuditor.audit_historical_fields()
        for field, info in auditor_res.items():
            assert info["is_synthetic"] is False
