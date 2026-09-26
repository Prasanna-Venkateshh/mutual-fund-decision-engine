"""
Maturity Adapter (Phase D.6).

Connects history length in years to FundMaturityTier classification.

Enforces:
- Separation of Fund Maturity, Quality Score, and Confidence.
- Insufficient track record (< 1 year) maps to NEW_FUND without setting quality score to zero.
"""

from typing import List, Dict, Any
from models.metric_data import HistoryMaturityBucket
from metrics.maturity import calculate_fund_history_maturity


class MaturityAdapter:
    """Adapter delegating scheme track record maturity classification to metrics/maturity.py."""

    def classify_maturity(self, nav_records: List[Dict[str, Any]]) -> HistoryMaturityBucket:
        """
        Classifies history length into HistoryMaturityBucket using metrics/maturity.py.
        """
        if not nav_records or len(nav_records) < 2:
            return HistoryMaturityBucket.LESS_THAN_1_YEAR
        _, bucket, _, _, _, _ = calculate_fund_history_maturity(nav_records)
        return bucket
