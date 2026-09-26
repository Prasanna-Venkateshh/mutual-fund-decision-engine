"""
Scoring Metric Adapter (Phase D.6 Refactored).

Consumes output from the existing financial metric engine orchestrator
(metrics/engine.py & metrics/maturity.py) and translates them into a point-in-time
SchemeMetricSnapshot contract object.

Enforces:
- CONSUMPTION of existing metric engine outputs (NO duplicate metric formulas).
- Point-in-time filtering of NAV up to observation date T.
- Mapping missing metrics explicitly to None (Missing != 0).
- HistoryMaturityBucket classification directly from metrics/maturity.py.
"""

from datetime import date
from typing import List, Dict, Any, Optional

from models.fund_quality_dataset import SchemeMetricSnapshot
from models.metric_data import HistoryMaturityBucket
from metrics.engine import FundMetricEngine
from metrics.maturity import calculate_fund_history_maturity


class ScoringMetricAdapter:
    """
    Adapter transforming outputs from FundMetricEngine into point-in-time SchemeMetricSnapshot.
    Acts purely as an adapter layer (does NOT reimplement financial formulas).
    """

    def __init__(self, metric_engine: Optional[FundMetricEngine] = None):
        self.metric_engine = metric_engine or FundMetricEngine()

    def compute_metric_snapshot(
        self,
        nav_records: List[Dict[str, Any]],
        observation_date: date,
        ter_value: Optional[float] = None,
        ter_observation_date: Optional[date] = None,
        canonical_scheme_id: str = "SCHEME_CANONICAL"
    ) -> SchemeMetricSnapshot:
        """
        Translates outputs from FundMetricEngine into a SchemeMetricSnapshot.
        """
        # Filter NAV history up to observation_date
        filtered_nav = [
            r for r in nav_records
            if r.get("nav_date") and r["nav_date"] <= observation_date
        ]
        filtered_nav.sort(key=lambda r: r["nav_date"])

        if len(filtered_nav) < 2:
            return SchemeMetricSnapshot(
                observation_date=observation_date,
                history_length_years=0.0,
                maturity_tier=HistoryMaturityBucket.LESS_THAN_1_YEAR,
                total_expense_ratio=ter_value,
                ter_observation_date=ter_observation_date
            )

        # 1. Maturity Evaluation via metrics/maturity.py
        total_days, maturity_bucket, _, start_date, end_date, _ = (
            calculate_fund_history_maturity(filtered_nav)
        )
        history_years = round(total_days / 365.25, 2)

        # 2. Invoke established FundMetricEngine orchestrator
        observations = self.metric_engine.compute_metrics_from_nav_records(
            canonical_scheme_id=canonical_scheme_id,
            nav_history=filtered_nav
        )

        obs_map = {obs.metric_name: obs for obs in observations}

        # 3. Extract metrics from MetricObservation objects
        cagr_overall = obs_map["CAGR_OVERALL"].metric_value if "CAGR_OVERALL" in obs_map else None

        r1_obs = obs_map.get("ROLLING_RETURN_MEAN_1Y")
        r1_mean = r1_obs.metric_value if r1_obs else None
        r1_min = r1_obs.metadata_json.get("min_return") if r1_obs and r1_obs.metadata_json else None
        r1_max = r1_obs.metadata_json.get("max_return") if r1_obs and r1_obs.metadata_json else None

        r3_obs = obs_map.get("ROLLING_RETURN_MEAN_3Y")
        r3_mean = r3_obs.metric_value if r3_obs else None
        r3_min = r3_obs.metadata_json.get("min_return") if r3_obs and r3_obs.metadata_json else None
        r3_max = r3_obs.metadata_json.get("max_return") if r3_obs and r3_obs.metadata_json else None

        volatility = obs_map["ANNUALIZED_VOLATILITY"].metric_value if "ANNUALIZED_VOLATILITY" in obs_map else None
        downside_dev = obs_map["DOWNSIDE_DEVIATION"].metric_value if "DOWNSIDE_DEVIATION" in obs_map else None

        max_dd = None
        if "MAX_DRAWDOWN" in obs_map:
            dd_obs = obs_map["MAX_DRAWDOWN"]
            meta = dd_obs.metadata_json or {}
            peak_d = date.fromisoformat(meta["peak_date"]) if meta.get("peak_date") else None
            trough_d = date.fromisoformat(meta["trough_date"]) if meta.get("trough_date") else None
            max_dd = (dd_obs.metric_value, peak_d, trough_d)

        return SchemeMetricSnapshot(
            observation_date=observation_date,
            history_length_years=history_years,
            maturity_tier=maturity_bucket,
            cagr_overall=cagr_overall,
            cagr_3y=None,  # Available via rolling 3Y mean
            cagr_5y=None,
            rolling_1y_mean=r1_mean,
            rolling_1y_min=r1_min,
            rolling_1y_max=r1_max,
            rolling_3y_mean=r3_mean,
            rolling_3y_min=r3_min,
            rolling_3y_max=r3_max,
            annualized_volatility=volatility,
            downside_deviation=downside_dev,
            max_drawdown=max_dd,
            total_expense_ratio=ter_value,
            ter_observation_date=ter_observation_date
        )
