"""
Fund Metric Engine Orchestrator (metrics/engine.py).

Orchestrates metric calculations from normalized NAV records, attaching full provenance
metadata and persisting structured MetricObservation records as mandated by
ARCHITECTURE.md Section 4 & PRODUCT_SPEC.md Section 8.
"""

import uuid
from datetime import datetime, date, timezone
from typing import List, Dict, Any, Optional

from models.metric_data import MetricObservation, HistoryMaturityBucket
from models.nav_data import DataQualityState
from data.repositories.nav_repository import NAVRepository
from data.repositories.metric_repository import MetricRepository

from metrics.maturity import calculate_fund_history_maturity
from metrics.returns import (
    calculate_absolute_return,
    calculate_cagr,
    calculate_rolling_returns
)
from metrics.risk import (
    calculate_annualized_volatility,
    calculate_downside_deviation,
    calculate_max_drawdown
)


class FundMetricEngine:
    """Orchestrator for fund metric observations calculation and storage."""

    METHODOLOGY_VERSION = "1.0.0"

    def __init__(
        self,
        nav_repo: Optional[NAVRepository] = None,
        metric_repo: Optional[MetricRepository] = None
    ):
        self.nav_repo = nav_repo
        self.metric_repo = metric_repo

    def compute_metrics_for_scheme(
        self,
        canonical_scheme_id: str
    ) -> List[MetricObservation]:
        """
        Compute and persist all financial metric observations for a canonical scheme from DB.
        """
        if not self.nav_repo:
            return []
        nav_history = self.nav_repo.get_normalized_nav_history(canonical_scheme_id)
        metrics = self.compute_metrics_from_nav_records(canonical_scheme_id, nav_history)
        if self.metric_repo and metrics:
            self.metric_repo.save_metric_observations(metrics)
        return metrics

    def compute_metrics_from_nav_records(
        self,
        canonical_scheme_id: str,
        nav_history: List[Dict[str, Any]]
    ) -> List[MetricObservation]:
        """
        Compute financial metric observations directly from a list of normalized NAV records.
        """
        if not nav_history or len(nav_history) < 2:
            return []

        # 1. Maturity Observation
        total_days, maturity_bucket, quality_state, start_date, end_date, obs_count = (
            calculate_fund_history_maturity(nav_history)
        )

        now = datetime.now(timezone.utc)
        metrics: List[MetricObservation] = []

        # Metric 1: History Days
        m_history_days = MetricObservation(
            metric_id=f"m_hist_days_{canonical_scheme_id}_{end_date.strftime('%Y%m%d')}",
            canonical_scheme_id=canonical_scheme_id,
            metric_name="HISTORY_LENGTH_DAYS",
            metric_value=float(total_days),
            start_date=start_date,
            end_date=end_date,
            observation_count=obs_count,
            confidence_state=quality_state,
            calculation_timestamp=now,
            methodology_version=self.METHODOLOGY_VERSION,
            notes=f"Maturity bucket: {maturity_bucket.value}"
        )
        metrics.append(m_history_days)

        start_nav = float(nav_history[0]["nav_value"])
        end_nav = float(nav_history[-1]["nav_value"])

        # Metric 2: Absolute Return
        abs_ret = calculate_absolute_return(start_nav, end_nav)
        m_abs = MetricObservation(
            metric_id=f"m_abs_ret_{canonical_scheme_id}_{end_date.strftime('%Y%m%d')}",
            canonical_scheme_id=canonical_scheme_id,
            metric_name="ABSOLUTE_RETURN",
            metric_value=abs_ret,
            start_date=start_date,
            end_date=end_date,
            observation_count=obs_count,
            confidence_state=quality_state,
            calculation_timestamp=now,
            methodology_version=self.METHODOLOGY_VERSION
        )
        metrics.append(m_abs)

        # Metric 3: CAGR (If history >= 365 days)
        if total_days >= 365:
            cagr_val = calculate_cagr(start_nav, end_nav, start_date, end_date)
            m_cagr = MetricObservation(
                metric_id=f"m_cagr_overall_{canonical_scheme_id}_{end_date.strftime('%Y%m%d')}",
                canonical_scheme_id=canonical_scheme_id,
                metric_name="CAGR_OVERALL",
                metric_value=cagr_val,
                start_date=start_date,
                end_date=end_date,
                observation_count=obs_count,
                confidence_state=quality_state,
                calculation_timestamp=now,
                methodology_version=self.METHODOLOGY_VERSION
            )
            metrics.append(m_cagr)

        # Metric 4: 1-Year Rolling Returns
        if total_days >= 365:
            rolling_1y = calculate_rolling_returns(nav_history, window_years=1)
            if rolling_1y["status"] == "VALID":
                m_roll_1y = MetricObservation(
                    metric_id=f"m_roll_1y_mean_{canonical_scheme_id}_{end_date.strftime('%Y%m%d')}",
                    canonical_scheme_id=canonical_scheme_id,
                    metric_name="ROLLING_RETURN_MEAN_1Y",
                    metric_value=rolling_1y["mean_return"],
                    start_date=start_date,
                    end_date=end_date,
                    observation_count=obs_count,
                    confidence_state=quality_state,
                    calculation_timestamp=now,
                    methodology_version=self.METHODOLOGY_VERSION,
                    metadata_json=rolling_1y
                )
                metrics.append(m_roll_1y)

        # Metric 5: 3-Year Rolling Returns
        if total_days >= 1095:
            rolling_3y = calculate_rolling_returns(nav_history, window_years=3)
            if rolling_3y["status"] == "VALID":
                m_roll_3y = MetricObservation(
                    metric_id=f"m_roll_3y_mean_{canonical_scheme_id}_{end_date.strftime('%Y%m%d')}",
                    canonical_scheme_id=canonical_scheme_id,
                    metric_name="ROLLING_RETURN_MEAN_3Y",
                    metric_value=rolling_3y["mean_return"],
                    start_date=start_date,
                    end_date=end_date,
                    observation_count=obs_count,
                    confidence_state=quality_state,
                    calculation_timestamp=now,
                    methodology_version=self.METHODOLOGY_VERSION,
                    metadata_json=rolling_3y
                )
                metrics.append(m_roll_3y)

        # Metric 6: Annualized Volatility
        volatility_val = calculate_annualized_volatility(nav_history)
        m_vol = MetricObservation(
            metric_id=f"m_volatility_{canonical_scheme_id}_{end_date.strftime('%Y%m%d')}",
            canonical_scheme_id=canonical_scheme_id,
            metric_name="ANNUALIZED_VOLATILITY",
            metric_value=volatility_val,
            start_date=start_date,
            end_date=end_date,
            observation_count=obs_count,
            confidence_state=quality_state,
            calculation_timestamp=now,
            methodology_version=self.METHODOLOGY_VERSION
        )
        metrics.append(m_vol)

        # Metric 7: Downside Deviation
        downside_val = calculate_downside_deviation(nav_history)
        m_down = MetricObservation(
            metric_id=f"m_downside_dev_{canonical_scheme_id}_{end_date.strftime('%Y%m%d')}",
            canonical_scheme_id=canonical_scheme_id,
            metric_name="DOWNSIDE_DEVIATION",
            metric_value=downside_val,
            start_date=start_date,
            end_date=end_date,
            observation_count=obs_count,
            confidence_state=quality_state,
            calculation_timestamp=now,
            methodology_version=self.METHODOLOGY_VERSION
        )
        metrics.append(m_down)

        # Metric 8: Max Drawdown
        max_dd_val, peak_d, trough_d = calculate_max_drawdown(nav_history)
        m_dd = MetricObservation(
            metric_id=f"m_max_drawdown_{canonical_scheme_id}_{end_date.strftime('%Y%m%d')}",
            canonical_scheme_id=canonical_scheme_id,
            metric_name="MAX_DRAWDOWN",
            metric_value=max_dd_val,
            start_date=start_date,
            end_date=end_date,
            observation_count=obs_count,
            confidence_state=quality_state,
            calculation_timestamp=now,
            methodology_version=self.METHODOLOGY_VERSION,
            metadata_json={
                "peak_date": peak_d.isoformat() if peak_d else None,
                "trough_date": trough_d.isoformat() if trough_d else None
            }
        )
        metrics.append(m_dd)

        if self.metric_repo:
            self.metric_repo.save_metric_observations(metrics)
        return metrics
