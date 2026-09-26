"""
Metrics Engine — Risk, Downside Deviation & Drawdown Calculations.

Implements risk and downside metrics taking validated, normalized NAV time-series
as input as mandated by ARCHITECTURE.md Section 4 & PRODUCT_SPEC.md Section 8.
"""

from datetime import date, datetime
from typing import List, Dict, Any, Tuple
import math


def _extract_daily_returns(nav_records: List[Dict[str, Any]]) -> List[Tuple[date, float]]:
    """
    Helper to parse sorted daily NAV records and calculate simple daily percentage returns.
    Daily Return_t = (NAV_t - NAV_{t-1}) / NAV_{t-1}
    """
    if not nav_records or len(nav_records) < 2:
        return []

    parsed = []
    for r in nav_records:
        d = r["nav_date"]
        if isinstance(d, str):
            d = datetime.strptime(d, "%Y-%m-%d").date()
        parsed.append({"date": d, "nav": float(r["nav_value"])})

    parsed.sort(key=lambda x: x["date"])

    daily_returns: List[Tuple[date, float]] = []
    for i in range(1, len(parsed)):
        prev_nav = parsed[i - 1]["nav"]
        curr_nav = parsed[i]["nav"]
        curr_date = parsed[i]["date"]
        if prev_nav > 0.0:
            ret = (curr_nav - prev_nav) / prev_nav
            daily_returns.append((curr_date, ret))

    return daily_returns


def calculate_annualized_volatility(
    nav_records: List[Dict[str, Any]],
    trading_days_per_year: int = 252
) -> float:
    """
    Calculate Annualized Volatility (Standard Deviation of Daily Returns).
    
    Provisional Methodology Assumption:
    - trading_days_per_year (default 252): Current annualization convention ("Methodology to be validated").
    
    Formula: Standard Deviation(Daily Returns) * sqrt(trading_days_per_year)
    """
    daily_returns = [ret for _, ret in _extract_daily_returns(nav_records)]
    if not daily_returns or len(daily_returns) < 2:
        return 0.0

    mean_ret = sum(daily_returns) / len(daily_returns)
    variance = sum((r - mean_ret) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
    daily_std = math.sqrt(variance)

    return daily_std * math.sqrt(trading_days_per_year)


def calculate_downside_deviation(
    nav_records: List[Dict[str, Any]],
    mar_daily: float = 0.0,
    trading_days_per_year: int = 252
) -> float:
    """
    Calculate Downside Deviation (Semi-Standard Deviation of Returns Below Target/MAR).
    
    Provisional Methodology Assumptions:
    - mar_daily (default 0.0): Minimum Acceptable Return threshold ("Methodology to be validated").
    - trading_days_per_year (default 252): Current annualization convention ("Methodology to be validated").
    
    Formula: sqrt( Sum( min(0, Return_t - MAR)^2 ) / N ) * sqrt(trading_days_per_year)
    """
    daily_returns = [ret for _, ret in _extract_daily_returns(nav_records)]
    if not daily_returns:
        return 0.0

    downside_squared_diffs = [
        (r - mar_daily) ** 2 for r in daily_returns if r < mar_daily
    ]

    if not downside_squared_diffs:
        return 0.0

    # Downside variance over total observation count
    downside_variance = sum(downside_squared_diffs) / len(daily_returns)
    daily_downside_dev = math.sqrt(downside_variance)

    return daily_downside_dev * math.sqrt(trading_days_per_year)


def calculate_max_drawdown(
    nav_records: List[Dict[str, Any]]
) -> Tuple[float, Optional[date], Optional[date]]:
    """
    Calculate Peak-to-Trough Maximum Drawdown over observation period.
    
    Formula: (NAV_trough - NAV_peak) / NAV_peak
    Expressed as a non-positive float <= 0.0 (e.g., -0.15 for 15% drawdown).
    
    Returns:
    - max_drawdown: Non-positive float representing maximum drawdown ratio.
    - peak_date: Date when peak NAV occurred.
    - trough_date: Date when trough NAV occurred.
    """
    if not nav_records or len(nav_records) < 2:
        return 0.0, None, None

    parsed = []
    for r in nav_records:
        d = r["nav_date"]
        if isinstance(d, str):
            d = datetime.strptime(d, "%Y-%m-%d").date()
        parsed.append({"date": d, "nav": float(r["nav_value"])})

    parsed.sort(key=lambda x: x["date"])

    max_dd = 0.0
    peak_nav = parsed[0]["nav"]
    peak_date = parsed[0]["date"]
    
    best_peak_date = peak_date
    best_trough_date = peak_date

    for obs in parsed:
        current_nav = obs["nav"]
        current_date = obs["date"]

        if current_nav > peak_nav:
            peak_nav = current_nav
            peak_date = current_date
        else:
            drawdown = (current_nav - peak_nav) / peak_nav
            if drawdown < max_dd:
                max_dd = drawdown
                best_peak_date = peak_date
                best_trough_date = current_date

    return max_dd, best_peak_date, best_trough_date
