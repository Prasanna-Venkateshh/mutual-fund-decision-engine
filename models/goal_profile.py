"""
Goal Profile Data Contract (Phase F.2).

Defines frozen dataclasses and enums for representing individual investment goals
and general-wealth (non-goal) surplus capital contexts.

Governance Rules Enforced:
- Goal target amounts and dates can be explicitly unknown/skipped (is_target_amount_known=False).
- No fake target amounts or fabricated horizons are generated if missing.
- Supports multiple independent goals for the same investor.
- Supports general wealth / non-goal surplus capital context explicitly.
- Dataclasses are immutable (frozen=True).
- NO financial calculations (horizon tiers, risk ceilings, funding gap) are implemented in contracts.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional

from models.fund_quality_dataset import ProvenanceMetadata


class GoalPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


class GoalCategory(Enum):
    EDUCATION = "EDUCATION"
    RETIREMENT = "RETIREMENT"
    HOUSING = "HOUSING"
    WEALTH_CREATION = "WEALTH_CREATION"
    EMERGENCY = "EMERGENCY"
    GENERAL_WEALTH = "GENERAL_WEALTH"
    OTHER = "OTHER"


@dataclass(frozen=True)
class GoalProfile:
    """
    Immutable data contract representing a single investment goal or general-wealth context.
    """
    goal_id: str
    investor_id: str
    goal_name: str
    goal_category: GoalCategory
    target_date: Optional[date] = None
    effective_horizon_years: Optional[float] = None
    target_amount: Optional[float] = None
    is_target_amount_known: bool = True
    is_target_date_known: bool = True
    priority: GoalPriority = GoalPriority.MEDIUM
    current_funding_amount: Optional[float] = None
    current_monthly_contribution: Optional[float] = None
    is_general_wealth: bool = False
    created_timestamp_utc: Optional[datetime] = None
    provenance: Optional[ProvenanceMetadata] = None
    methodology_version: str = "1.0.0"
    rule_version: str = "1.0.0"

    def __post_init__(self):
        if not self.goal_id or not self.goal_id.strip():
            raise ValueError("goal_id cannot be empty")
        if not self.investor_id or not self.investor_id.strip():
            raise ValueError("investor_id cannot be empty")
        if not self.goal_name or not self.goal_name.strip():
            raise ValueError("goal_name cannot be empty")
        if self.target_amount is not None and self.target_amount < 0.0:
            raise ValueError(f"target_amount cannot be negative, got {self.target_amount}")
        if self.effective_horizon_years is not None and self.effective_horizon_years < 0.0:
            raise ValueError(f"effective_horizon_years cannot be negative, got {self.effective_horizon_years}")
        if self.current_funding_amount is not None and self.current_funding_amount < 0.0:
            raise ValueError(f"current_funding_amount cannot be negative, got {self.current_funding_amount}")
        if self.current_monthly_contribution is not None and self.current_monthly_contribution < 0.0:
            raise ValueError(f"current_monthly_contribution cannot be negative, got {self.current_monthly_contribution}")
