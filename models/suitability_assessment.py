"""
Suitability Assessment Output Data Contract (Phase F.2).

Defines frozen dataclasses and enums for representing the output contract of a future
Suitability & Risk Alignment Engine assessment.

Governance Rules Enforced:
- Output contract ONLY — does not calculate suitability status, lower-of-two alignment, or portfolio rules.
- Dataclass is immutable (frozen=True).
- Full auditability, versioning, confidence, and provenance fields are preserved.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from models.fund_quality_dataset import ProvenanceMetadata


class SuitabilityStatus(Enum):
    SUITABLE = "SUITABLE"
    CONDITIONALLY_SUITABLE = "CONDITIONALLY_SUITABLE"
    SUITABLE_WITH_CONSTRAINTS = "SUITABLE_WITH_CONSTRAINTS"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"
    NOT_SUITABLE = "NOT_SUITABLE"
    INVALID_ASSESSMENT = "INVALID_ASSESSMENT"


@dataclass(frozen=True)
class SuitabilityAssessmentResult:
    """
    Immutable data contract representing the reproducible suitability assessment result
    for a scheme observation date T.
    """
    assessment_id: str
    investor_id: str
    profile_version_used: str
    canonical_scheme_id: str
    amfi_code: str
    scheme_name: str
    category: str
    subcategory: str
    observation_date: date
    suitability_status: SuitabilityStatus
    goal_id: Optional[str] = None
    effective_risk_alignment: Optional[str] = None
    risk_capacity_result: Optional[str] = None
    risk_tolerance_result: Optional[str] = None
    max_permissible_asset_risk: Optional[str] = None
    effective_horizon_years: Optional[float] = None
    is_horizon_compatible: Optional[bool] = None
    is_liquidity_compatible: Optional[bool] = None
    affordability_status: Optional[str] = None
    sustainable_sip_capacity: Optional[float] = None
    fund_quality_score_consumed: Optional[float] = None
    fund_quality_confidence_consumed: float = 1.0
    suitability_confidence_score: float = 1.0
    constraints_applied: List[str] = field(default_factory=list)
    rejection_reasons: List[str] = field(default_factory=list)
    summary_explanation: str = ""
    provenance: Optional[ProvenanceMetadata] = None
    assessment_timestamp_utc: Optional[datetime] = None
    methodology_version: str = "1.0.0"
    rule_version: str = "1.0.0"

    def __post_init__(self):
        if not self.assessment_id or not self.assessment_id.strip():
            raise ValueError("assessment_id cannot be empty")
        if not self.investor_id or not self.investor_id.strip():
            raise ValueError("investor_id cannot be empty")
        if not self.canonical_scheme_id or not self.canonical_scheme_id.strip():
            raise ValueError("canonical_scheme_id cannot be empty")
        if self.suitability_confidence_score < 0.0 or self.suitability_confidence_score > 1.0:
            raise ValueError(f"suitability_confidence_score must be between 0.0 and 1.0, got {self.suitability_confidence_score}")
        if self.fund_quality_confidence_consumed < 0.0 or self.fund_quality_confidence_consumed > 1.0:
            raise ValueError(f"fund_quality_confidence_consumed must be between 0.0 and 1.0, got {self.fund_quality_confidence_consumed}")
