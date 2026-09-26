"""
Risk Capacity Assessment Output Data Contracts (Phase F.3.1).

Defines frozen, versioned dataclasses and enums for representing the output of the
Risk Capacity Engine.

Governance Rules Enforced:
- Output contract ONLY — does not calculate suitability status, lower-of-two alignment, or portfolio rules.
- Dataclasses are immutable (frozen=True).
- Full auditability, versioning, confidence, and provenance fields are preserved.
- Missing or insufficient inputs produce clear status tags (PARTIAL, INSUFFICIENT_INFORMATION, CONFIGURATION_ERROR).
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import List, Optional, Dict, Any

from models.fund_quality_dataset import ProvenanceMetadata
from models.investor_profile import RiskCapacityLevel
from config.risk.capacity_config import StartupMode


class AssessmentStatus(Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"


class ConstraintLevel(Enum):
    UNCONSTRAINED = "UNCONSTRAINED"
    LOW_CONSTRAINT = "LOW_CONSTRAINT"
    MODERATE_CONSTRAINT = "MODERATE_CONSTRAINT"
    HIGH_CONSTRAINT = "HIGH_CONSTRAINT"
    CRITICAL_CONSTRAINT = "CRITICAL_CONSTRAINT"


@dataclass(frozen=True)
class ConstraintResult:
    """
    Immutable result container for an individual constraint dimension evaluation.
    """
    dimension_name: str
    calculated_ratio: Optional[float]
    constraint_level: str
    ceiling_capacity_tier: Optional[RiskCapacityLevel]
    rule_version: str
    status: str
    evidence_references: List[str] = field(default_factory=list)
    is_binding: bool = False


@dataclass(frozen=True)
class RiskCapacityAssessmentResult:
    """
    Immutable data contract representing the reproducible Risk Capacity assessment result
    for investor profile snapshot at observation date T.
    """
    assessment_id: str
    investor_id: str
    profile_version_used: str
    observation_date: date
    assessment_timestamp_utc: datetime
    startup_mode: StartupMode
    assessment_status: AssessmentStatus
    overall_capacity_tier: Optional[RiskCapacityLevel] = None
    binding_constraint_name: Optional[str] = None
    debt_constraint: Optional[ConstraintResult] = None
    reserve_constraint: Optional[ConstraintResult] = None
    surplus_constraint: Optional[ConstraintResult] = None
    confidence_score: float = 1.0
    explanation_tokens: List[str] = field(default_factory=list)
    provenance: Optional[ProvenanceMetadata] = None
    output_tag: Optional[str] = None
    methodology_version: str = "1.0.0"
    rule_version: str = "1.0.0"

    def __post_init__(self):
        if not self.assessment_id or not self.assessment_id.strip():
            raise ValueError("assessment_id cannot be empty")
        if not self.investor_id or not self.investor_id.strip():
            raise ValueError("investor_id cannot be empty")
        if self.confidence_score < 0.0 or self.confidence_score > 1.0:
            raise ValueError(f"confidence_score must be between 0.0 and 1.0, got {self.confidence_score}")
