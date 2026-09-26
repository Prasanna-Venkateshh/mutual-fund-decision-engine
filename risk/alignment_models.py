"""
Risk Alignment Output & Data Contracts (Phase F.3.3 Specification).

Defines frozen, versioned dataclasses and enums for representing the input contracts,
alignment states, limiting constraints, and output contract of the Risk Alignment Engine.

Governance Rules Enforced:
- Output contract ONLY — does not implement downstream suitability, fund scoring, or portfolio allocation rules.
- Dataclasses are immutable (frozen=True).
- Preserves full auditability, versioning, confidence, and provenance from both underlying assessments.
- Enforces lower-of-two constraint (Aligned Risk <= Capacity AND Aligned Risk <= Tolerance).
- Preserves distinction between Risk Capacity and Risk Tolerance constructs.
- Does NOT manufacture precision when underlying data is partial or insufficient.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from models.fund_quality_dataset import ProvenanceMetadata
from models.investor_profile import RiskCapacityLevel, RiskToleranceLevel
from config.risk.capacity_config import StartupMode
from risk.capacity_models import AssessmentStatus


class AlignmentStatus(Enum):
    FULLY_ALIGNED = "FULLY_ALIGNED"
    CAPACITY_CONSTRAINED = "CAPACITY_CONSTRAINED"
    TOLERANCE_CONSTRAINED = "TOLERANCE_CONSTRAINED"
    PARTIAL_ALIGNMENT = "PARTIAL_ALIGNMENT"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"
    INVALID_ASSESSMENT = "INVALID_ASSESSMENT"


class LimitingConstraint(Enum):
    NONE = "NONE"
    RISK_CAPACITY = "RISK_CAPACITY"
    RISK_TOLERANCE = "RISK_TOLERANCE"
    BOTH_INSUFFICIENT = "BOTH_INSUFFICIENT"
    UNCLASSIFIED = "UNCLASSIFIED"


class AlignedRiskLevel(Enum):
    VERY_LOW = 1
    LOW = 2
    MODERATE = 3
    HIGH = 4
    VERY_HIGH = 5

    @classmethod
    def from_capacity_level(cls, level: RiskCapacityLevel) -> "AlignedRiskLevel":
        return cls(level.value)

    @classmethod
    def from_tolerance_level(cls, level: RiskToleranceLevel) -> "AlignedRiskLevel":
        return cls(level.value)


@dataclass(frozen=True)
class RiskAlignmentAssessmentResult:
    """
    Immutable data contract representing the reproducible Risk Alignment result
    combining independent Risk Capacity and Risk Tolerance assessments at date T.
    """
    assessment_id: str
    investor_id: str
    profile_version_used: str
    observation_date: date
    assessment_timestamp_utc: datetime
    startup_mode: StartupMode
    alignment_status: AlignmentStatus
    limiting_constraint: LimitingConstraint
    aligned_risk_level: Optional[AlignedRiskLevel] = None
    risk_capacity_level: Optional[RiskCapacityLevel] = None
    risk_tolerance_level: Optional[RiskToleranceLevel] = None
    capacity_assessment_id: Optional[str] = None
    tolerance_assessment_id: Optional[str] = None
    capacity_confidence_score: float = 1.0
    tolerance_confidence_score: float = 1.0
    alignment_confidence_score: float = 1.0
    explanation_tokens: List[str] = field(default_factory=list)
    missing_information_tokens: List[str] = field(default_factory=list)
    provenance: Optional[ProvenanceMetadata] = None
    output_tag: Optional[str] = None
    is_stale_input: bool = False
    methodology_version: str = "1.0.0"
    rule_version: str = "1.0.0"

    def __post_init__(self):
        if not self.assessment_id or not self.assessment_id.strip():
            raise ValueError("assessment_id cannot be empty")
        if not self.investor_id or not self.investor_id.strip():
            raise ValueError("investor_id cannot be empty")
        if self.alignment_confidence_score < 0.0 or self.alignment_confidence_score > 1.0:
            raise ValueError(
                f"alignment_confidence_score must be between 0.0 and 1.0, got {self.alignment_confidence_score}"
            )
        if self.capacity_confidence_score < 0.0 or self.capacity_confidence_score > 1.0:
            raise ValueError(
                f"capacity_confidence_score must be between 0.0 and 1.0, got {self.capacity_confidence_score}"
            )
        if self.tolerance_confidence_score < 0.0 or self.tolerance_confidence_score > 1.0:
            raise ValueError(
                f"tolerance_confidence_score must be between 0.0 and 1.0, got {self.tolerance_confidence_score}"
            )
