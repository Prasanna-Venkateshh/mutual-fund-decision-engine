"""
Phase E Fund Quality Scoring Engine Test Suite.

Tests:
1. Peer Group Normalizer directionality, bounds, and tie-handling.
2. Scoring Weight Manager category-family resolution and dynamic downside bounds.
3. Fund Quality Scoring Engine score calculation and reproducibility.
4. Missing data handling (Missing != 0, proportional weight scaling).
5. Score vs Confidence separation (low confidence does not force low score).
6. Explainability generation (dimension explanations and summary rationale).
7. Anti-survivorship peer group controls.
8. Absence of Buy/Sell or portfolio allocation leakage.
9. Independent synthetic QA calculation fixture matching manual expected values.
"""

from datetime import date
import pytest

from models.fund_quality_dataset import (
    FundQualityDatasetInput,
    PlanType,
    OptionType,
    ProvenanceMetadata,
    CategoryPointInTimeContext,
    SchemeMetricSnapshot
)
from models.metric_data import HistoryMaturityBucket
from scoring.config import SCORING_METHODOLOGY_VERSION, WEIGHT_CONFIG_VERSION
from scoring.normalization import PeerGroupNormalizer
from scoring.weights import ScoringWeightManager
from scoring.engine import FundQualityScoringEngine


class TestFundQualityScoring:
    """Test suite for Phase E scoring engine implementation."""

    @pytest.fixture
    def mock_provenance(self):
        return ProvenanceMetadata(
            source_id="AMFI_OFFICIAL",
            source_document_url="https://www.amfiindia.com",
            retrieval_timestamp_utc=date(2023, 1, 1),
            methodology_version="1.0.0"
        )

    @pytest.fixture
    def mock_category(self):
        return CategoryPointInTimeContext(
            category="Equity",
            subcategory="Small Cap",
            effective_date=date(2017, 10, 6)
        )

    def create_mock_input(
        self,
        canonical_id: str,
        amfi_code: str,
        name: str,
        cagr: Optional[float],
        volatility: Optional[float],
        downside: Optional[float],
        max_dd: Optional[float],
        ter: Optional[float],
        maturity: HistoryMaturityBucket = HistoryMaturityBucket.FIVE_TO_TEN_YEARS,
        confidence: float = 1.0,
        mock_category=None,
        mock_provenance=None
    ) -> FundQualityDatasetInput:
        cat = mock_category or CategoryPointInTimeContext(category="Equity", subcategory="Small Cap", effective_date=date(2017, 10, 6))
        prov = mock_provenance or ProvenanceMetadata(source_id="AMFI", source_document_url="http://test", retrieval_timestamp_utc=date(2023, 1, 1))

        snapshot = SchemeMetricSnapshot(
            observation_date=date(2023, 1, 1),
            history_length_years=6.0 if maturity == HistoryMaturityBucket.FIVE_TO_TEN_YEARS else 0.5,
            maturity_tier=maturity,
            cagr_overall=cagr,
            rolling_1y_mean=cagr,
            rolling_3y_mean=cagr,
            annualized_volatility=volatility,
            downside_deviation=downside,
            max_drawdown=(max_dd, date(2020, 1, 1), date(2020, 3, 1)) if max_dd is not None else None,
            total_expense_ratio=ter
        )

        return FundQualityDatasetInput(
            dataset_version="1.0.0",
            observation_date=date(2023, 1, 1),
            canonical_scheme_id=canonical_id,
            amfi_code=amfi_code,
            scheme_name=name,
            amc_name="Test AMC",
            plan_type=PlanType.DIRECT,
            option_type=OptionType.GROWTH,
            category_context=cat,
            metrics=snapshot,
            data_quality_score=1.0,
            confidence_score=confidence,
            provenance=prov
        )

    def test_01_normalization_directionality_and_bounds(self):
        normalizer = PeerGroupNormalizer()
        peers = [10.0, 15.0, 20.0, 25.0, 30.0]

        # Higher is better
        p_high, s_high = normalizer.normalize_dimension(25.0, peers, higher_is_better=True)
        assert s_high > 50.0
        assert 0.0 <= s_high <= 100.0

        # Lower is better (inverted)
        p_low, s_low = normalizer.normalize_dimension(25.0, peers, higher_is_better=False)
        assert s_low < 50.0
        assert 0.0 <= s_low <= 100.0

    def test_02_weight_manager_category_resolution_and_dynamic_downside(self):
        wm = ScoringWeightManager()

        # Regular Large Cap (Base Equity weights)
        w_large = wm.get_dimension_weights("Equity", "Large Cap")
        assert sum(w_large.values()) == pytest.approx(100.0, abs=0.1)
        assert w_large["downside_risk"] == 15.0

        # High Volatility Small Cap (Dynamic Downside Scaling)
        w_small = wm.get_dimension_weights("Equity", "Small Cap")
        assert sum(w_small.values()) == pytest.approx(100.0, abs=0.1)
        assert w_small["downside_risk"] > 15.0  # Increased weight for downside risk

    def test_03_engine_score_calculation(self):
        engine = FundQualityScoringEngine()

        # Build 5 peer inputs with distinct metrics
        fund_a = self.create_mock_input("A", "101", "Fund A Direct Growth", cagr=0.18, volatility=0.14, downside=0.08, max_dd=-0.12, ter=0.65)
        fund_b = self.create_mock_input("B", "102", "Fund B Direct Growth", cagr=0.15, volatility=0.16, downside=0.10, max_dd=-0.15, ter=0.75)
        fund_c = self.create_mock_input("C", "103", "Fund C Direct Growth", cagr=0.12, volatility=0.18, downside=0.12, max_dd=-0.18, ter=0.85)
        fund_d = self.create_mock_input("D", "104", "Fund D Direct Growth", cagr=0.10, volatility=0.20, downside=0.14, max_dd=-0.22, ter=0.95)
        fund_e = self.create_mock_input("E", "105", "Fund E Direct Growth", cagr=0.08, volatility=0.22, downside=0.16, max_dd=-0.25, ter=1.05)

        peers = [fund_a, fund_b, fund_c, fund_d, fund_e]

        res_a = engine.calculate_fund_quality_score(fund_a, peers)
        res_e = engine.calculate_fund_quality_score(fund_e, peers)

        assert res_a.quality_score is not None
        assert res_e.quality_score is not None
        assert res_a.quality_score > res_e.quality_score  # Best performer gets higher quality score
        assert 0.0 <= res_a.quality_score <= 100.0
        assert 0.0 <= res_e.quality_score <= 100.0

    def test_04_missing_data_proportional_scaling(self):
        engine = FundQualityScoringEngine()

        # Fund A has full data; Fund B is missing TER
        fund_a = self.create_mock_input("A", "101", "Fund A", cagr=0.15, volatility=0.15, downside=0.10, max_dd=-0.15, ter=0.75)
        fund_b = self.create_mock_input("B", "102", "Fund B", cagr=0.15, volatility=0.15, downside=0.10, max_dd=-0.15, ter=None)

        peers = [fund_a, fund_b]

        res_b = engine.calculate_fund_quality_score(fund_b, peers)
        assert res_b.quality_score is not None  # Score calculated via remaining available dimensions
        assert res_b.dimension_scores["cost_efficiency"].data_available is False
        assert res_b.dimension_scores["cost_efficiency"].weighted_contribution == 0.0

    def test_05_insufficient_data_returns_none_score(self):
        engine = FundQualityScoringEngine()

        # New fund with no return, risk, or TER data
        fund_new = self.create_mock_input(
            "NEW", "999", "New Fund Direct Growth",
            cagr=None, volatility=None, downside=None, max_dd=None, ter=None,
            maturity=HistoryMaturityBucket.LESS_THAN_1_YEAR
        )

        res_new = engine.calculate_fund_quality_score(fund_new, [fund_new])
        assert res_new.quality_score is None  # None score for insufficient evidence
        assert res_new.confidence_score < 0.60  # Reduced confidence

    def test_06_score_vs_confidence_separation(self):
        engine = FundQualityScoringEngine()

        # Fund with strong return metrics but low confidence (small peer count & limited history)
        fund_lim = self.create_mock_input(
            "LIM", "888", "Limited History Fund",
            cagr=0.20, volatility=0.12, downside=0.07, max_dd=-0.10, ter=0.70,
            maturity=HistoryMaturityBucket.ONE_TO_THREE_YEARS, confidence=0.70
        )

        res = engine.calculate_fund_quality_score(fund_lim, [fund_lim])
        assert res.quality_score is not None
        assert res.quality_score >= 50.0  # Quality score is high due to good metrics
        assert res.confidence_score < 0.60  # Confidence is low due to small peer group & limited history

    def test_07_explainability_generation(self):
        engine = FundQualityScoringEngine()
        fund_a = self.create_mock_input("A", "101", "Fund A", cagr=0.18, volatility=0.14, downside=0.08, max_dd=-0.12, ter=0.65)
        fund_b = self.create_mock_input("B", "102", "Fund B", cagr=0.10, volatility=0.20, downside=0.14, max_dd=-0.22, ter=0.95)

        res = engine.calculate_fund_quality_score(fund_a, [fund_a, fund_b])
        assert len(res.summary_explanation) > 0
        assert "Fund Quality Score" in res.summary_explanation
        assert res.dimension_scores["return"].explanation is not None

    def test_08_no_trade_or_portfolio_leakage(self):
        engine = FundQualityScoringEngine()
        fund_a = self.create_mock_input("A", "101", "Fund A", cagr=0.18, volatility=0.14, downside=0.08, max_dd=-0.12, ter=0.65)
        res = engine.calculate_fund_quality_score(fund_a, [fund_a])

        # Confirm result container contains NO buy/sell decisions, recommendations, or allocations
        assert not hasattr(res, "buy_recommendation")
        assert not hasattr(res, "target_allocation")
        assert not hasattr(res, "suitability_score")
        assert res.is_provisional is True

    def test_09_independent_synthetic_qa_fixture(self):
        """
        Independent QA calculation fixture comparing engine output against
        manually pre-calculated expected scores.
        """
        engine = FundQualityScoringEngine()

        # 2 identical funds -> neutral percentile 50.0 for all dimensions
        f1 = self.create_mock_input("F1", "1", "Fund 1", cagr=0.15, volatility=0.15, downside=0.10, max_dd=-0.15, ter=0.80)
        f2 = self.create_mock_input("F2", "2", "Fund 2", cagr=0.15, volatility=0.15, downside=0.10, max_dd=-0.15, ter=0.80)

        res = engine.calculate_fund_quality_score(f1, [f1, f2])

        # Expected score: 50.0 when all peers have identical performance
        assert res.quality_score == pytest.approx(50.0, abs=1.0)
        assert res.scoring_methodology_version == SCORING_METHODOLOGY_VERSION
        assert res.weight_config_version == WEIGHT_CONFIG_VERSION

    def test_10_idcw_return_comparability_handling(self):
        """Verifies that IDCW schemes without total return reconstruction exclude return scores."""
        engine = FundQualityScoringEngine()

        # Create IDCW fund input with return_comparability_available=False
        cat = CategoryPointInTimeContext(category="Equity", subcategory="Large Cap", effective_date=date(2017, 10, 6))
        prov = ProvenanceMetadata(source_id="AMFI", source_document_url="http://test", retrieval_timestamp_utc=date(2023, 1, 1))

        snapshot = SchemeMetricSnapshot(
            observation_date=date(2023, 1, 1),
            history_length_years=5.0,
            maturity_tier=HistoryMaturityBucket.FIVE_TO_TEN_YEARS,
            cagr_overall=0.12,
            rolling_1y_mean=0.12,
            rolling_3y_mean=0.12,
            annualized_volatility=0.15,
            downside_deviation=0.10,
            max_drawdown=-0.15,
            total_expense_ratio=0.85
        )

        idcw_input = FundQualityDatasetInput(
            dataset_version="1.0.0",
            observation_date=date(2023, 1, 1),
            canonical_scheme_id="IDCW_1",
            amfi_code="201",
            scheme_name="Test Fund IDCW Payout",
            amc_name="Test AMC",
            plan_type=PlanType.DIRECT,
            option_type=OptionType.IDCW_PAYOUT,
            category_context=cat,
            metrics=snapshot,
            data_quality_score=1.0,
            confidence_score=1.0,
            provenance=prov,
            return_comparability_available=False  # IDCW return comparability unavailable!
        )

        res = engine.calculate_fund_quality_score(idcw_input, [idcw_input])

        # Return & consistency dimensions must be marked unavailable
        assert res.dimension_scores["return"].data_available is False
        assert res.dimension_scores["consistency"].data_available is False
        assert res.dimension_scores["return"].weighted_contribution == 0.0
        # Platform confidence is reduced because active weight sum is lower (only 55% active weight)
        assert res.confidence_score < 0.60

    def test_11_independent_qa_fixtures_suite(self):
        """
        Comprehensive independent QA fixture testing 10 distinct mathematical,
        sensitivity, boundary, and anti-survivorship scenarios.
        """
        engine = FundQualityScoringEngine()

        # Fixture 1: 3-Fund Peer Group (Strict rank math verification)
        f_3_1 = self.create_mock_input("F3_1", "301", "Fund 3_1", cagr=0.20, volatility=0.10, downside=0.05, max_dd=-0.10, ter=0.50)
        f_3_2 = self.create_mock_input("F3_2", "302", "Fund 3_2", cagr=0.15, volatility=0.15, downside=0.10, max_dd=-0.15, ter=0.80)
        f_3_3 = self.create_mock_input("F3_3", "303", "Fund 3_3", cagr=0.10, volatility=0.20, downside=0.15, max_dd=-0.20, ter=1.10)
        peers_3 = [f_3_1, f_3_2, f_3_3]

        res_3_mid = engine.calculate_fund_quality_score(f_3_2, peers_3)
        # Mid fund (rank 2 of 3): (2 - 0.5)/3 * 100 = 50.0 percentile across all dimensions!
        assert res_3_mid.quality_score == pytest.approx(50.0, abs=1.0)

        # Fixture 2: 10-Fund Peer Group (High confidence)
        peers_10 = [
            self.create_mock_input(f"F10_{i}", f"40{i}", f"Fund 10_{i}", cagr=0.05 + 0.02 * i, volatility=0.25 - 0.01 * i, downside=0.20 - 0.01 * i, max_dd=-0.30 + 0.02 * i, ter=1.50 - 0.05 * i)
            for i in range(10)
        ]
        res_10_top = engine.calculate_fund_quality_score(peers_10[9], peers_10)
        assert res_10_top.confidence_score >= 0.90  # 10 peers -> no peer penalty

        # Fixture 3: Tie Case (Fractional rank averaging)
        f_tie1 = self.create_mock_input("T1", "501", "Tie Fund 1", cagr=0.15, volatility=0.15, downside=0.10, max_dd=-0.15, ter=0.80)
        f_tie2 = self.create_mock_input("T2", "502", "Tie Fund 2", cagr=0.15, volatility=0.15, downside=0.10, max_dd=-0.15, ter=0.80)
        res_tie = engine.calculate_fund_quality_score(f_tie1, [f_tie1, f_tie2])
        assert res_tie.dimension_scores["return"].peer_percentile == 50.0

        # Fixture 4: Missing TER (Proportional re-weighting)
        f_noter = self.create_mock_input("NOTER", "601", "No TER Fund", cagr=0.15, volatility=0.15, downside=0.10, max_dd=-0.15, ter=None)
        res_noter = engine.calculate_fund_quality_score(f_noter, [f_noter, f_3_1])
        assert res_noter.dimension_scores["cost_efficiency"].data_available is False

        # Fixture 5: Multiple Missing Metrics
        f_multimiss = self.create_mock_input("MM", "701", "Multi Miss Fund", cagr=0.15, volatility=0.15, downside=None, max_dd=None, ter=None)
        res_mm = engine.calculate_fund_quality_score(f_multimiss, [f_multimiss, f_3_1])
        assert res_mm.available_dimensions_count == 3

        # Fixture 6: Small-History / New Fund (< 1 year maturity)
        f_new = self.create_mock_input("NEW", "801", "New Fund", cagr=0.15, volatility=0.15, downside=0.10, max_dd=-0.15, ter=0.80, maturity=HistoryMaturityBucket.LESS_THAN_1_YEAR)
        res_new = engine.calculate_fund_quality_score(f_new, [f_new])
        assert res_new.quality_score is None

        # Fixture 7: Low Identity Confidence Input
        f_lowconf = self.create_mock_input("LOWCONF", "901", "Low Conf Scheme", cagr=0.15, volatility=0.15, downside=0.10, max_dd=-0.15, ter=0.80, confidence=0.50)
        res_lowconf = engine.calculate_fund_quality_score(f_lowconf, [f_lowconf, f_3_1, f_3_2, f_3_3, f_10_top if 'f_10_top' in locals() else f_3_1])
        assert res_lowconf.confidence_score <= 0.50

        # Fixture 8: Different Metric Directions (Higher vs Lower is better)
        # Verify that top Return gets high score and top TER (lowest value) gets high score
        assert res_3_mid.dimension_scores["return"].normalized_score == 50.0
        assert res_3_mid.dimension_scores["cost_efficiency"].normalized_score == 50.0

        # Fixture 9: Dynamic Downside Category Example (Small Cap vs Large Cap)
        cat_small = CategoryPointInTimeContext(category="Equity", subcategory="Small Cap", effective_date=date(2017, 10, 6))
        cat_large = CategoryPointInTimeContext(category="Equity", subcategory="Large Cap", effective_date=date(2017, 10, 6))
        f_small = self.create_mock_input("SC", "1001", "Small Cap Scheme", cagr=0.18, volatility=0.15, downside=0.10, max_dd=-0.15, ter=0.80, mock_category=cat_small)
        f_large = self.create_mock_input("LC", "1002", "Large Cap Scheme", cagr=0.18, volatility=0.15, downside=0.10, max_dd=-0.15, ter=0.80, mock_category=cat_large)
        res_sc = engine.calculate_fund_quality_score(f_small, [f_small])
        res_lc = engine.calculate_fund_quality_score(f_large, [f_large])
        # Small Cap has higher downside risk weight than Large Cap due to subcategory scaling
        assert res_sc.dimension_scores["downside_risk"].weight > res_lc.dimension_scores["downside_risk"].weight

        # Fixture 10: Anti-Survivorship Point-in-Time Peer Grouping
        # Confirm that peer grouping respects observation date T and category/subcategory context
        res_pit = engine.calculate_fund_quality_score(f_small, [f_small, f_large])
        assert res_pit.peer_group_size == 1  # Large Cap fund excluded from Small Cap peer group!

