"""
Fund Data History & Maturity Evaluation Module.

Evaluates scheme historical NAV observation data maturity and maps to history buckets
defined in PRODUCT_SPEC.md Section 7.
"""

from datetime import date, datetime
from typing import List, Dict, Any, Tuple

from models.metric_data import HistoryMaturityBucket
from models.nav_data import DataQualityState


def calculate_fund_history_maturity(
    nav_records: List[Dict[str, Any]]
) -> Tuple[int, HistoryMaturityBucket, DataQualityState, date, date, int]:
    """
    Evaluate fund historical data maturity.
    
    Inputs:
    - nav_records: Sorted list of normalized NAV record dictionaries containing 'nav_date' and 'nav_value'.
    
    Returns:
    - total_days: Total calendar days between start_date and end_date.
    - bucket: HistoryMaturityBucket enum value.
    - quality_state: DataQualityState (INCOMPLETE if <1 year history).
    - start_date: Earliest observation date.
    - end_date: Latest observation date.
    - observation_count: Number of NAV records.
    """
    if not nav_records:
        raise ValueError("Cannot calculate maturity metrics on empty NAV history.")

    # Parse dates if passed as strings
    parsed_records = []
    for r in nav_records:
        d = r["nav_date"]
        if isinstance(d, str):
            d = datetime.strptime(d, "%Y-%m-%d").date()
        parsed_records.append({"date": d, "value": float(r["nav_value"])})

    parsed_records.sort(key=lambda x: x["date"])
    start_date = parsed_records[0]["date"]
    end_date = parsed_records[-1]["date"]
    observation_count = len(parsed_records)

    total_days = (end_date - start_date).days

    # Map total calendar days to PRODUCT_SPEC Section 7 History Buckets
    if total_days < 365:
        bucket = HistoryMaturityBucket.LESS_THAN_1_YEAR
        quality_state = DataQualityState.INCOMPLETE
    elif total_days < 1095:  # 1–3 years
        bucket = HistoryMaturityBucket.ONE_TO_THREE_YEARS
        quality_state = DataQualityState.VALID
    elif total_days < 1825:  # 3–5 years
        bucket = HistoryMaturityBucket.THREE_TO_FIVE_YEARS
        quality_state = DataQualityState.VALID
    elif total_days < 3652:  # 5–10 years
        bucket = HistoryMaturityBucket.FIVE_TO_TEN_YEARS
        quality_state = DataQualityState.VALID
    else:  # 10+ years
        bucket = HistoryMaturityBucket.TEN_PLUS_YEARS
        quality_state = DataQualityState.VALID

    return total_days, bucket, quality_state, start_date, end_date, observation_count
