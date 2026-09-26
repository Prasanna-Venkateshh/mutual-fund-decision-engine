"""
Fund Quality Scoring Output Models (Phase E).

Defines immutable output dataclasses for calculated Fund Quality Scores,
dimension breakdown scores, and component-level explanations.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional


@dataclass(frozen=True)
class DimensionScore:
    """Represents calculated score for a single Fund Quality dimension."""
    dimension_name: str
    raw_value: Optional[float]
    peer_percentile: Optional[float]
    normalized_score: Optional[float]
    weight: float
    weighted_contribution: float
    data_available: bool
    explanation: str


@dataclass(frozen=True)
class FundQualityScoreResult:
    """
    Complete, reproducible, explainable Fund Quality Score result for a scheme
    as of observation date T.
    """
    canonical_scheme_id: str
    amfi_code: str
    scheme_name: str
    category: str
    subcategory: str
    observation_date: date
    quality_score: Optional[float]        # [0.0, 100.0] intrinsic quality score (None if missing critical data)
    confidence_score: float               # [0.0, 1.0] platform confidence
    data_quality_score: float           # [0.0, 1.0] completeness score
    dimension_scores: Dict[str, DimensionScore]
    available_dimensions_count: int
    total_dimensions_count: int
    peer_group_size: int
    scoring_methodology_version: str
    weight_config_version: str
    calculation_timestamp_utc: datetime
    summary_explanation: str
    is_provisional: bool = True
