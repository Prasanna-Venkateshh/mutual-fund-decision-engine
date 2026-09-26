"""
Data models for Fund Metric Observations and Historical Maturity Buckets.

Implements structural observation models for financial metrics as mandated by
ARCHITECTURE.md Section 4 & 7 and PRODUCT_SPEC.md Section 7.
"""

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Optional, List, Dict, Any

from models.nav_data import DataQualityState


class HistoryMaturityBucket(Enum):
    """
    Historical data maturity classification as defined in PRODUCT_SPEC.md Section 7.
    """
    LESS_THAN_1_YEAR = "LESS_THAN_1_YEAR"      # < 1 Year: Conventional score unavailable
    ONE_TO_THREE_YEARS = "ONE_TO_THREE_YEARS"  # 1–3 Years: Limited evidence
    THREE_TO_FIVE_YEARS = "THREE_TO_FIVE_YEARS"# 3–5 Years: Reduced/normal evidence
    FIVE_TO_TEN_YEARS = "FIVE_TO_TEN_YEARS"    # 5–10 Years: Fuller evidence
    TEN_PLUS_YEARS = "TEN_PLUS_YEARS"          # 10+ Years: Strong historical evidence


@dataclass
class MetricObservation:
    """
    Structured financial metric observation calculated from normalized NAV time-series.
    Preserves exact observation dates, sample size, calculation timestamp, methodology version,
    and quality confidence state.
    """
    metric_id: str
    canonical_scheme_id: str
    metric_name: str
    metric_value: float
    start_date: date
    end_date: date
    observation_count: int
    confidence_state: DataQualityState = DataQualityState.VALID
    calculation_timestamp: Optional[datetime] = None
    methodology_version: str = "1.0.0"
    notes: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None

    def to_dict(self) -> dict:
        """Serialize metric observation to dictionary format."""
        return {
            "metric_id": self.metric_id,
            "canonical_scheme_id": self.canonical_scheme_id,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "observation_count": self.observation_count,
            "confidence_state": self.confidence_state.value,
            "calculation_timestamp": self.calculation_timestamp.isoformat() if self.calculation_timestamp else None,
            "methodology_version": self.methodology_version,
            "notes": self.notes,
            "metadata": self.metadata_json
        }
