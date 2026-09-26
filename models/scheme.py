"""
Data models for Canonical Mutual Fund Schemes and Scheme Mappings.

Supports the Scheme Master / Entity Resolution boundary (data/mapping/)
as defined in ARCHITECTURE.md Section 4.

Phase C addition: CanonicalScheme now carries an optional lifecycle_events list
populated by LifecycleResolver for point-in-time identity queries.  This field is
a read-only enrichment result — it is NOT persisted as a column in canonical_schemes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional, List, Dict, Any

if TYPE_CHECKING:
    from models.scheme_lifecycle import LifecycleEvent


class PlanType(Enum):
    """Mutual Fund Plan Type."""
    DIRECT = "DIRECT"
    REGULAR = "REGULAR"
    UNKNOWN = "UNKNOWN"


class OptionType(Enum):
    """Mutual Fund Option Type."""
    GROWTH = "GROWTH"
    IDCW = "IDCW"  # Income Distribution cum Capital Withdrawal (formerly Dividend)
    BONUS = "BONUS"
    UNKNOWN = "UNKNOWN"


class MappingConfidence(Enum):
    """
    Mapping confidence levels as mandated by ARCHITECTURE.md Section 4.
    Prevent unvalidated or ambiguous schemes from silently flowing downstream.
    """
    EXACT_MATCH = "EXACT_MATCH"
    HIGH_CONFIDENCE = "HIGH_CONFIDENCE"
    AMBIGUOUS = "AMBIGUOUS"
    UNMAPPED = "UNMAPPED"


@dataclass
class CanonicalScheme:
    """
    Single canonical internal mutual fund scheme entity.
    Guarantees that a fund variant cannot accidentally become multiple entities.
    """
    canonical_scheme_id: str
    amc_name: str
    scheme_name: str
    clean_scheme_name: str
    plan_type: PlanType
    option_type: OptionType
    category: str
    sub_category: str
    primary_amfi_code: Optional[str] = None
    isin_growth: Optional[str] = None
    isin_reinvest: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None

    # Phase C — lifecycle enrichment (read-only, not persisted as a DB column)
    # Populated by LifecycleResolver when performing point-in-time queries.
    # Default empty list preserves backward compatibility with all existing Slice 1/2 code.
    lifecycle_events: List["LifecycleEvent"] = field(default_factory=list)


@dataclass
class SchemeMapping:
    """
    Bidirectional mapping between source-specific raw keys and canonical scheme ID.
    """
    mapping_id: str
    source_id: str
    source_scheme_code: str
    source_scheme_name: str
    canonical_scheme_id: Optional[str]
    confidence: MappingConfidence
    notes: Optional[str] = None
    mapped_at: Optional[datetime] = None
