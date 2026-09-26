"""
Scoring Dataset Validator (Phase D.6).

Performs quantitative data completeness evaluation, metric bounds validation,
and confidence assessment for FundQualityDatasetInput records.

Enforces:
- Deterministic data quality score [0.0, 1.0] representing dataset completeness.
- Deterministic confidence score [0.0, 1.0] representing source & history authority.
- Quarantine flag generation for invalid or ambiguous records.
- Missing values reduce completeness/confidence but do NOT mutate to zero.
"""

from typing import Tuple, List
from models.fund_quality_dataset import (
    FundQualityDatasetInput,
    OptionType,
    PlanType
)
from models.metric_data import HistoryMaturityBucket


class ScoringDatasetValidator:
    """Validator and quality score generator for Fund Quality dataset inputs."""

    def validate_and_score(
        self,
        dataset_input: FundQualityDatasetInput
    ) -> Tuple[float, float, bool, List[str]]:
        """
        Evaluates data_quality_score, confidence_score, and quarantine state.
        Returns (data_quality_score, confidence_score, is_quarantined, quarantine_reasons).
        """
        reasons: List[str] = list(dataset_input.quarantine_reasons)
        is_quarantined = dataset_input.is_quarantined

        # 1. Identity Check
        if not dataset_input.canonical_scheme_id:
            is_quarantined = True
            reasons.append("Missing canonical_scheme_id.")
        if dataset_input.plan_type == PlanType.UNKNOWN:
            is_quarantined = True
            reasons.append("Ambiguous or UNKNOWN plan_type.")

        # 2. Completeness (data_quality_score)
        completeness_checks = 0
        total_checks = 7

        m = dataset_input.metrics
        if m.history_length_years > 0:
            completeness_checks += 1
        if m.cagr_overall is not None or m.maturity_tier == HistoryMaturityBucket.LESS_THAN_1_YEAR:
            completeness_checks += 1
        if m.rolling_1y_mean is not None or m.maturity_tier == HistoryMaturityBucket.LESS_THAN_1_YEAR:
            completeness_checks += 1
        if m.annualized_volatility is not None or m.history_length_years < 0.1:
            completeness_checks += 1
        if m.max_drawdown is not None or m.history_length_years < 0.1:
            completeness_checks += 1
        if m.total_expense_ratio is not None:
            completeness_checks += 1
        if dataset_input.category_context.category != "UNKNOWN":
            completeness_checks += 1

        data_quality_score = round(completeness_checks / total_checks, 2)

        # 3. Confidence (confidence_score)
        confidence = 1.0

        # Reduce confidence if pre-2017 category estimate
        if dataset_input.category_context.source == "PRE_SEBI_2017_ESTIMATE":
            confidence *= 0.85

        # Reduce confidence for new funds with constrained track record
        if m.maturity_tier == HistoryMaturityBucket.LESS_THAN_1_YEAR:
            confidence *= 0.60
        elif m.maturity_tier == HistoryMaturityBucket.ONE_TO_THREE_YEARS:
            confidence *= 0.80

        # Reduce confidence for IDCW options without total return adjustment
        if dataset_input.option_type in (OptionType.IDCW_REINVESTMENT, OptionType.IDCW_PAYOUT):
            if not dataset_input.return_comparability_available:
                confidence *= 0.75
                reasons.append("IDCW option return comparability unavailable without total return adjustment.")

        # Quarantine if confidence is zero or critical errors exist
        if is_quarantined:
            confidence = min(confidence, 0.50)

        return (
            data_quality_score,
            round(confidence, 2),
            is_quarantined,
            reasons
        )
