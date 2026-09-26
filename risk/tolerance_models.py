"""
Risk Tolerance Assessment Output Data Contracts (Phase F.3.2).

Defines frozen, versioned dataclasses and enums for representing the output of the
Risk Tolerance Engine.

Governance Rules Enforced:
- Output contract ONLY — does not calculate suitability status, lower-of-two alignment, or portfolio rules.
- Dataclasses are immutable (frozen=True).
- Full auditability, versioning, confidence, and provenance fields are preserved.
- Missing or insufficient inputs produce clear status tags (PARTIAL, INSUFFICIENT_INFORMATION, CONFIGURATION_ERROR).
- Risk Tolerance remains completely independent of Risk Capacity and financial data.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from models.fund_quality_dataset import ProvenanceMetadata
from models.investor_profile import RiskToleranceLevel
from config.risk.capacity_config import StartupMode
from risk.capacity_models import AssessmentStatus


class BehavioralConsistencyLevel(Enum):
    HIGHLY_CONSISTENT = "HIGHLY_CONSISTENT"
    MODERATELY_INCONSISTENT = "MODERATELY_INCONSISTENT"
    MATERIALLY_INCONSISTENT = "MATERIALLY_INCONSISTENT"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class RiskToleranceAssessmentResult:
    """
    Immutable data contract representing the reproducible Risk Tolerance assessment result
    for investor profile snapshot at observation date T.
    """
    assessment_id: str
    investor_id: str
    profile_version_used: str
    observation_date: date
    assessment_timestamp_utc: datetime
    startup_mode: StartupMode
    assessment_status: AssessmentStatus
    overall_tolerance_tier: Optional[RiskToleranceLevel] = None
    raw_tolerance_score: Optional[float] = None
    loss_acceptance_score: Optional[float] = None
    stagnation_patience_score: Optional[float] = None
    drawdown_behavior_score: Optional[float] = None
    volatility_tolerance_score: Optional[float] = None
    behavioral_consistency_score: Optional[float] = None
    consistency_level: BehavioralConsistencyLevel = BehavioralConsistencyLevel.UNKNOWN
    confidence_score: float = 1.0
    explanation_tokens: List[str] = field(default_factory=list)
    provenance: Optional[ProvenanceMetadata] = None
    output_tag: Optional[str] = None
    questionnaire_version: str = "1.0.0"
    methodology_version: str = "1.0.0"
    rule_version: str = "1.0.0"


    def __post_init__(self):
        if not self.assessment_id or not self.assessment_id.strip():
            raise ValueError("assessment_id cannot be empty")
        if not self.investor_id or not self.investor_id.strip():
            raise ValueError("investor_id cannot be empty")
        if self.confidence_score < 0.0 or self.confidence_score > 1.0:
            raise ValueError(f"confidence_score must be between 0.0 and 1.0, got {self.confidence_score}")
