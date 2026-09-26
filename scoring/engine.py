"""
Fund Quality Scoring Engine (Phase E).

Core orchestrator for calculating deterministic, category-aware, explainable,
bounded, evidence-grounded Fund Quality Scores from FundQualityDatasetInput contracts.

Enforces:
- Intrinsic Fund Quality evaluation ONLY (NO investor suitability, portfolio need, or trade recommendations).
- Score vs Confidence separation.
- Anti-survivorship peer group selection.
- Missing data handling (Missing != 0, proportional weight re-scaling).
- Strict bounds in [0.0, 100.0].
- Full reproducibility and explanation generation.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from models.fund_quality_dataset import FundQualityDatasetInput, OptionType
from models.metric_data import HistoryMaturityBucket
from scoring.config import (
    SCORING_METHODOLOGY_VERSION,
    WEIGHT_CONFIG_VERSION,
    SCORE_MIN,
    SCORE_MAX,
    MIN_PEER_COUNT_PREFERRED
)
from scoring.models import DimensionScore, FundQualityScoreResult
from scoring.normalization import PeerGroupNormalizer
from scoring.weights import ScoringWeightManager
from scoring.explanations import ScoringExplanationGenerator


class FundQualityScoringEngine:
    """Orchestrator for Fund Quality Score calculation and peer normalization."""

    def __init__(
        self,
        normalizer: Optional[PeerGroupNormalizer] = None,
        weight_manager: Optional[ScoringWeightManager] = None,
        explanation_generator: Optional[ScoringExplanationGenerator] = None
    ):
        self.normalizer = normalizer or PeerGroupNormalizer()
        self.weight_manager = weight_manager or ScoringWeightManager()
        self.explanation_generator = explanation_generator or ScoringExplanationGenerator()

    def calculate_fund_quality_score(
        self,
        target_input: FundQualityDatasetInput,
        peer_inputs: List[FundQualityDatasetInput]
    ) -> FundQualityScoreResult:
        """
        Calculates a FundQualityScoreResult for target_input relative to peer_inputs.
        """
        category = target_input.category_context.category
        subcategory = target_input.category_context.subcategory
        plan_type = target_input.plan_type

        # 1. Peer Group Filtering (Intra-category, intra-plan_type)
        peers = [
            p for p in peer_inputs
            if p.category_context.category == category
            and p.category_context.subcategory == subcategory
            and p.plan_type == plan_type
        ]

        if target_input not in peers:
            peers.append(target_input)

        peer_count = len(peers)

        # 2. Weight Resolution
        weights = self.weight_manager.get_dimension_weights(category, subcategory)

        # 3. Extract Raw Metrics for Target & Peers (Respecting IDCW return comparability)
        return_comp = target_input.return_comparability_available

        dims_data: Dict[str, Tuple[Optional[float], List[float], bool]] = {
            # (target_raw_value, list_of_peer_raw_values, higher_is_better)
            "return": (
                (target_input.metrics.cagr_overall if target_input.metrics.cagr_overall is not None else target_input.metrics.rolling_1y_mean) if return_comp else None,
                [
                    (p.metrics.cagr_overall if p.metrics.cagr_overall is not None else p.metrics.rolling_1y_mean) if p.return_comparability_available else None
                    for p in peers
                ],
                True
            ),
            "consistency": (
                (target_input.metrics.rolling_3y_mean if target_input.metrics.rolling_3y_mean is not None else target_input.metrics.rolling_1y_mean) if return_comp else None,
                [
                    (p.metrics.rolling_3y_mean if p.metrics.rolling_3y_mean is not None else p.metrics.rolling_1y_mean) if p.return_comparability_available else None
                    for p in peers
                ],
                True
            ),
            "volatility": (
                target_input.metrics.annualized_volatility,
                [p.metrics.annualized_volatility for p in peers],
                False
            ),
            "downside_risk": (
                target_input.metrics.downside_deviation,
                [p.metrics.downside_deviation for p in peers],
                False
            ),
            "max_drawdown": (
                abs(target_input.metrics.max_drawdown[0]) if isinstance(target_input.metrics.max_drawdown, (list, tuple))
                else (abs(target_input.metrics.max_drawdown) if target_input.metrics.max_drawdown is not None else None),
                [
                    abs(p.metrics.max_drawdown[0]) if isinstance(p.metrics.max_drawdown, (list, tuple))
                    else (abs(p.metrics.max_drawdown) if p.metrics.max_drawdown is not None else None)
                    for p in peers
                ],
                False
            ),
            "cost_efficiency": (
                target_input.metrics.total_expense_ratio,
                [p.metrics.total_expense_ratio for p in peers],
                False
            )
        }

        # 4. Normalize & Scale Active Dimension Weights
        dimension_scores: Dict[str, DimensionScore] = {}
        active_weights_sum = 0.0

        for dim_name, (raw_val, peer_vals, higher_is_better) in dims_data.items():
            base_weight = weights.get(dim_name, 0.0)
            data_available = (raw_val is not None)

            if data_available:
                active_weights_sum += base_weight

        # Normalize metrics and calculate weighted contributions
        total_score_sum = 0.0
        available_count = 0

        for dim_name, (raw_val, peer_vals, higher_is_better) in dims_data.items():
            base_weight = weights.get(dim_name, 0.0)
            data_available = (raw_val is not None)

            if data_available and active_weights_sum > 0.0:
                available_count += 1
                adjusted_weight = round((base_weight / active_weights_sum) * 100.0, 2)
                percentile, norm_score = self.normalizer.normalize_dimension(
                    target_value=raw_val,
                    peer_values=peer_vals,
                    higher_is_better=higher_is_better
                )
                contribution = round((norm_score * adjusted_weight) / 100.0, 2)
                total_score_sum += contribution
            else:
                adjusted_weight = base_weight
                percentile = None
                norm_score = None
                contribution = 0.0

            exp_text = self.explanation_generator.generate_dimension_explanation(
                dimension_name=dim_name,
                raw_value=raw_val,
                peer_percentile=percentile,
                normalized_score=norm_score,
                weight=adjusted_weight,
                data_available=data_available
            )

            dimension_scores[dim_name] = DimensionScore(
                dimension_name=dim_name,
                raw_value=raw_val,
                peer_percentile=percentile,
                normalized_score=norm_score,
                weight=adjusted_weight,
                weighted_contribution=contribution,
                data_available=data_available,
                explanation=exp_text
            )

        # 5. Determine Overall Quality Score
        if active_weights_sum < 40.0 or target_input.metrics.maturity_tier == HistoryMaturityBucket.LESS_THAN_1_YEAR:
            # Insufficient metric evidence or track record under 1 year to calculate a quality score
            final_quality_score = None
        else:
            final_quality_score = max(SCORE_MIN, min(SCORE_MAX, round(total_score_sum, 1)))

        # 6. Calculate Platform Confidence
        confidence = target_input.confidence_score

        # Reduce confidence if peer count is small (< MIN_PEER_COUNT_PREFERRED)
        if peer_count < MIN_PEER_COUNT_PREFERRED:
            confidence *= 0.70

        # Reduce confidence if active weight sum is partial
        if active_weights_sum < 80.0:
            confidence *= (active_weights_sum / 100.0)

        final_confidence = round(max(0.0, min(1.0, confidence)), 2)

        # 7. Generate Summary Explanation
        summary_exp = self.explanation_generator.generate_summary_explanation(
            quality_score=final_quality_score,
            confidence_score=final_confidence,
            dimension_scores=dimension_scores,
            peer_group_size=peer_count
        )

        now_utc = datetime.now(timezone.utc)

        return FundQualityScoreResult(
            canonical_scheme_id=target_input.canonical_scheme_id,
            amfi_code=target_input.amfi_code,
            scheme_name=target_input.scheme_name,
            category=category,
            subcategory=subcategory,
            observation_date=target_input.observation_date,
            quality_score=final_quality_score,
            confidence_score=final_confidence,
            data_quality_score=target_input.data_quality_score,
            dimension_scores=dimension_scores,
            available_dimensions_count=available_count,
            total_dimensions_count=len(dims_data),
            peer_group_size=peer_count,
            scoring_methodology_version=SCORING_METHODOLOGY_VERSION,
            weight_config_version=WEIGHT_CONFIG_VERSION,
            calculation_timestamp_utc=now_utc,
            summary_explanation=summary_exp,
            is_provisional=True
        )

    def calculate_category_peer_scores(
        self,
        pool: List[FundQualityDatasetInput]
    ) -> List[FundQualityScoreResult]:
        """
        Calculates FundQualityScoreResult for all schemes in pool against their respective peer groups.
        """
        results: List[FundQualityScoreResult] = []
        for item in pool:
            res = self.calculate_fund_quality_score(item, pool)
            results.append(res)
        return results
