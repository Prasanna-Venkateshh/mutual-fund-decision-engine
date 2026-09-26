"""
Investor Profile & Risk Snapshot Data Contracts (Phase F.2).

Defines frozen, versioned dataclasses and enums for representing investor financial
capacity, behavioral risk tolerance, and point-in-time investor profile snapshots.

Governance Rules Enforced:
- Missing information MUST remain explicitly missing (None / NULL).
- Dataclasses are immutable (frozen=True).
- NO financial calculations (debt servicing caps, capacity tiers, tolerance scoring) are implemented in contracts.
- Provenance and versioning metadata are preserved for historical audit reproducibility.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional, Dict, Any

from models.fund_quality_dataset import ProvenanceMetadata


class RiskCapacityLevel(Enum):
    VERY_LOW = 1
    LOW = 2
    MODERATE = 3
    HIGH = 4
    VERY_HIGH = 5


class RiskToleranceLevel(Enum):
    VERY_LOW = 1
    LOW = 2
    MODERATE = 3
    HIGH = 4
    VERY_HIGH = 5


class ProfileStatus(Enum):
    ACTIVE = "ACTIVE"
    STALE = "STALE"
    ARCHIVED = "ARCHIVED"
    DRAFT = "DRAFT"


@dataclass(frozen=True)
class FinancialCapacitySnapshot:
    """
    Observed financial capacity inputs and context as of observation date T.
    Data contract ONLY — does not calculate capacity tiers or financial rules.
    """
    observation_date: date
    effective_date: date
    monthly_gross_income: Optional[float] = None
    monthly_fixed_expenses: Optional[float] = None
    monthly_debt_servicing: Optional[float] = None
    liquid_emergency_reserves: Optional[float] = None
    emergency_reserve_months: Optional[float] = None
    savings_ratio: Optional[float] = None
    sustainable_monthly_capacity: Optional[float] = None
    capacity_tier: Optional[RiskCapacityLevel] = None
    confidence_score: float = 1.0
    provenance: Optional[ProvenanceMetadata] = None
    methodology_version: str = "1.0.0"
    rule_version: str = "1.0.0"

    def __post_init__(self):
        if self.confidence_score < 0.0 or self.confidence_score > 1.0:
            raise ValueError(f"confidence_score must be between 0.0 and 1.0, got {self.confidence_score}")
        for field_name, val in [
            ("monthly_gross_income", self.monthly_gross_income),
            ("monthly_fixed_expenses", self.monthly_fixed_expenses),
            ("monthly_debt_servicing", self.monthly_debt_servicing),
            ("liquid_emergency_reserves", self.liquid_emergency_reserves),
            ("emergency_reserve_months", self.emergency_reserve_months),
        ]:
            if val is not None and val < 0.0:
                raise ValueError(f"{field_name} cannot be negative, got {val}")


@dataclass(frozen=True)
class BehavioralToleranceSnapshot:
    """
    Observed behavioral risk tolerance responses as of assessment date T.
    Data contract ONLY — does not calculate tolerance tiers or fallback logic.
    """
    observation_date: date
    assessment_date: date
    loss_reaction_choice: Optional[str] = None
    stagnation_comfort_choice: Optional[str] = None
    historical_drawdown_action: Optional[str] = None
    volatility_preference: Optional[str] = None
    behavioral_consistency_score: float = 1.0
    tolerance_tier: Optional[RiskToleranceLevel] = None
    confidence_score: float = 1.0
    provenance: Optional[ProvenanceMetadata] = None
    methodology_version: str = "1.0.0"
    rule_version: str = "1.0.0"

    def __post_init__(self):
        if self.confidence_score < 0.0 or self.confidence_score > 1.0:
            raise ValueError(f"confidence_score must be between 0.0 and 1.0, got {self.confidence_score}")
        if self.behavioral_consistency_score < 0.0 or self.behavioral_consistency_score > 1.0:
            raise ValueError(f"behavioral_consistency_score must be between 0.0 and 1.0, got {self.behavioral_consistency_score}")


@dataclass(frozen=True)
class InvestorProfileSnapshot:
    """
    Immutable, versioned investor profile container capturing the exact state
    of investor financial capacity, behavioral tolerance, and risk alignment
    used at assessment date T.
    """
    profile_id: str
    investor_id: str
    profile_version: str
    effective_date: date
    birth_date: Optional[date] = None
    financial_capacity: Optional[FinancialCapacitySnapshot] = None
    behavioral_tolerance: Optional[BehavioralToleranceSnapshot] = None
    overall_effective_risk_alignment: Optional[RiskCapacityLevel] = None
    profiling_tier_completed: int = 1
    status: ProfileStatus = ProfileStatus.ACTIVE
    confidence_score: float = 1.0
    provenance: Optional[ProvenanceMetadata] = None
    created_timestamp_utc: Optional[datetime] = None
    methodology_version: str = "1.0.0"
    rule_version: str = "1.0.0"
    is_stale: bool = False

    def __post_init__(self):
        if not self.profile_id or not self.profile_id.strip():
            raise ValueError("profile_id cannot be empty")
        if not self.investor_id or not self.investor_id.strip():
            raise ValueError("investor_id cannot be empty")
        if self.confidence_score < 0.0 or self.confidence_score > 1.0:
            raise ValueError(f"confidence_score must be between 0.0 and 1.0, got {self.confidence_score}")
        if self.profiling_tier_completed not in (1, 2, 3):
            raise ValueError(f"profiling_tier_completed must be 1, 2, or 3, got {self.profiling_tier_completed}")
        if self.birth_date is not None and self.birth_date > self.effective_date:
            raise ValueError(f"birth_date {self.birth_date} cannot be in the future relative to effective_date {self.effective_date}")
