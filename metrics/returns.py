"""
Metrics Engine — Returns & Rolling Returns Calculations.

Implements deterministic return metric algorithms taking validated, normalized NAV time-series
as input as mandated by ARCHITECTURE.md Section 4 & PRODUCT_SPEC.md Section 8.
"""

from datetime import date, datetime
from typing import List, Dict, Any, Optional
import math


def calculate_absolute_return(start_nav: float, end_nav: float) -> float:
    """
    Calculate Simple Point-to-Point Absolute Return.
    
    Formula: (End NAV - Start NAV) / Start NAV
    """
    if start_nav <= 0.0 or end_nav <= 0.0:
        raise ValueError("NAV values must be positive floats (> 0.0).")
    return (end_nav - start_nav) / start_nav


def calculate_cagr(start_nav: float, end_nav: float, start_date: date, end_date: date) -> float:
    """
    Calculate Compound Annual Growth Rate (CAGR).
    
    Formula: (End NAV / Start NAV) ^ (365.25 / Calendar Days) - 1
    Used for holding periods >= 1 year.
    """
    if start_nav <= 0.0 or end_nav <= 0.0:
        raise ValueError("NAV values must be positive floats (> 0.0).")

    days = (end_date - start_date).days
    if days <= 0:
        raise ValueError(f"End date ({end_date}) must be strictly after start date ({start_date}).")

    if days < 365:
        # For periods under 1 year, return absolute return without annualizing to prevent distortion
        return calculate_absolute_return(start_nav, end_nav)

    years = days / 365.25
    return math.pow(end_nav / start_nav, 1.0 / years) - 1.0


def calculate_rolling_returns(
    nav_records: List[Dict[str, Any]],
    window_years: int = 1,
    tolerance_days: int = 30
) -> Dict[str, Any]:
    """
    Calculate N-year Rolling CAGR across historical daily NAV time-series.
    
    Provisional Methodology Assumption:
    - tolerance_days (default 30): Calendar day window matching tolerance around target window length.
      "Methodology to be validated" before Fund Quality Scoring.

    Returns summary statistics:
    - window_years: Rolling window length (e.g., 1, 3, 5 years)
    - total_rolling_windows: Number of valid rolling windows evaluated
    - mean_return: Mean annualized rolling return
    - median_return: Median annualized rolling return
    - min_return: Minimum rolling return observed
    - max_return: Maximum rolling return observed
    - positive_return_ratio: Proportion of rolling periods yielding positive return (>= 0.0)
    """
    if not nav_records or len(nav_records) < 2:
        raise ValueError("Insufficient NAV history for rolling returns calculation.")

    # Parse and sort records
    parsed = []
    for r in nav_records:
        d = r["nav_date"]
        if isinstance(d, str):
            d = datetime.strptime(d, "%Y-%m-%d").date()
        parsed.append({"date": d, "nav": float(r["nav_value"])})

    parsed.sort(key=lambda x: x["date"])
    target_days = int(window_years * 365.25)

    rolling_cagrs: List[float] = []

    # Slide window over daily time-series
    start_idx = 0
    end_idx = 0
    n = len(parsed)

    for start_idx in range(n):
        start_obs = parsed[start_idx]
        # Find observation closest to start_date + target_days
        while end_idx < n and (parsed[end_idx]["date"] - start_obs["date"]).days < target_days:
            end_idx += 1

        if end_idx < n:
            end_obs = parsed[end_idx]
            actual_days = (end_obs["date"] - start_obs["date"]).days
            # Accept window if within ±tolerance_days of target window length
            if abs(actual_days - target_days) <= tolerance_days:
                cagr = calculate_cagr(start_obs["nav"], end_obs["nav"], start_obs["date"], end_obs["date"])
                rolling_cagrs.append(cagr)

    if not rolling_cagrs:
        return {
            "window_years": window_years,
            "total_rolling_windows": 0,
            "mean_return": 0.0,
            "median_return": 0.0,
            "min_return": 0.0,
            "max_return": 0.0,
            "positive_return_ratio": 0.0,
            "status": "INSUFFICIENT_HISTORY"
        }

    rolling_cagrs.sort()
    count = len(rolling_cagrs)
    mean_val = sum(rolling_cagrs) / count

    if count % 2 == 1:
        median_val = rolling_cagrs[count // 2]
    else:
        median_val = (rolling_cagrs[count // 2 - 1] + rolling_cagrs[count // 2]) / 2.0

    pos_count = sum(1 for r in rolling_cagrs if r >= 0.0)

    return {
        "window_years": window_years,
        "total_rolling_windows": count,
        "mean_return": mean_val,
        "median_return": median_val,
        "min_return": rolling_cagrs[0],
        "max_return": rolling_cagrs[-1],
        "positive_return_ratio": pos_count / count,
        "status": "VALID"
    }