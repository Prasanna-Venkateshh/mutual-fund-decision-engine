"""
Fund Quality Dataset Models (Phase D.6).

Defines the frozen, versionable, point-in-time dataclasses for passing
validated metric, identity, category, cost, maturity, and provenance inputs
to the future Fund Quality Scoring Engine.

Governance Rules Enforced:
- Missing metric values MUST be represented as None / NULL (Missing != 0).
- Dataclasses are immutable (frozen=True).
- Score and Confidence remain separate.
- No final score field or ranking logic is included.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import List, Optional


class PlanType(Enum):
    DIRECT = "DIRECT"
    REGULAR = "REGULAR"
    UNKNOWN = "UNKNOWN"


class OptionType(Enum):
    GROWTH = "GROWTH"
    IDCW_REINVESTMENT = "IDCW_REINVESTMENT"
    IDCW_PAYOUT = "IDCW_PAYOUT"
    UNKNOWN = "UNKNOWN"


from models.metric_data import HistoryMaturityBucket

# Alias FundMaturityTier to previously approved HistoryMaturityBucket for governance compliance
FundMaturityTier = HistoryMaturityBucket


@dataclass(frozen=True)
class ProvenanceMetadata:
    """Provenance metadata tracking source authority, retrieval, and methodology version."""
    source_id: str
    source_document_url: str
    retrieval_timestamp_utc: datetime
    methodology_version: str = "1.0.0"
    is_platform_calculated: bool = True


@dataclass(frozen=True)
class CategoryPointInTimeContext:
    """Point-in-time category classification as of observation date T."""
    category: str
    subcategory: str
    effective_date: date
    source: str = "SEBI_2017_CIRCULAR"
    strategy_style: Optional[str] = None
    source_precision: str = "DAY"
    confidence_score: float = 1.0


@dataclass(frozen=True)
class SchemeMetricSnapshot:
    """Point-in-time financial metrics calculated from historical NAV series."""
    observation_date: date
    history_length_years: float
    maturity_tier: FundMaturityTier
    cagr_overall: Optional[float] = None
    cagr_3y: Optional[float] = None
    cagr_5y: Optional[float] = None
    rolling_1y_mean: Optional[float] = None
    rolling_1y_min: Optional[float] = None
    rolling_1y_max: Optional[float] = None
    rolling_3y_mean: Optional[float] = None
    rolling_3y_min: Optional[float] = None
    rolling_3y_max: Optional[float] = None
    annualized_volatility: Optional[float] = None
    downside_deviation: Optional[float] = None
    max_drawdown: Optional[float] = None
    total_expense_ratio: Optional[float] = None
    ter_observation_date: Optional[date] = None


@dataclass(frozen=True)
class FundQualityDatasetInput:
    """
    Immutable dataset container for a single scheme observation date T.
    Consumed by the future Fund Quality Scoring Engine.
    """
    dataset_version: str
    observation_date: date
    canonical_scheme_id: str
    amfi_code: str
    scheme_name: str
    amc_name: str
    plan_type: PlanType
    option_type: OptionType
    category_context: CategoryPointInTimeContext
    metrics: SchemeMetricSnapshot
    data_quality_score: float          # [0.0, 1.0] quantitative completeness
    confidence_score: float            # [0.0, 1.0] platform confidence
    provenance: ProvenanceMetadata
    isin: Optional[str] = None
    is_quarantined: bool = False
    quarantine_reasons: List[str] = field(default_factory=list)
    return_comparability_available: bool = True  # False for IDCW options pending total return adjustment
