"""
Data models for Raw and Normalized NAV Observations, Quality States, and Quarantine Records.

Implements strict separation between raw unvalidated observations and downstream
normalized NAV records as mandated by ARCHITECTURE.md Section 5.
"""

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Optional, Dict, Any


class DataQualityState(Enum):
    """Data quality classification as required by Phase F.8 Master State Model."""
    VALID = "VALID"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"
    INVALID = "INVALID"
    CONFLICTED = "CONFLICTED"
    QUARANTINED = "QUARANTINED"
    STALE = "STALE"

    # Backward compatibility aliases for existing phase tests
    INCOMPLETE = "PARTIAL"
    CONFLICTING = "CONFLICTED"
    UNAVAILABLE = "UNKNOWN"


@dataclass
class RawNAVRecord:
    """
    Unmodified raw observation received from an external data source.
    Preserves exact source string, line number, source ID, and retrieval timestamp
    to ensure full raw data reproducibility.
    """
    raw_record_id: str
    source_id: str
    retrieval_timestamp: datetime
    raw_scheme_code: str
    raw_scheme_name: str
    raw_nav_value: str
    raw_date: str
    raw_line_number: Optional[int] = None
    additional_metadata: Optional[Dict[str, Any]] = None


@dataclass
class ValidationResult:
    """Result payload from the Data Validation Gate."""
    is_valid: bool
    quality_state: DataQualityState
    parsed_scheme_code: Optional[str] = None
    parsed_scheme_name: Optional[str] = None
    parsed_nav: Optional[float] = None
    parsed_date: Optional[date] = None
    error_message: Optional[str] = None


@dataclass
class NormalizedNAVRecord:
    """
    Validated and normalized NAV observation linked to a Canonical Scheme ID.
    Retains full source provenance tracking identifiers.
    """
    nav_id: str
    canonical_scheme_id: str
    nav_date: date
    nav_value: float
    source_id: str
    raw_record_id: str
    retrieval_timestamp: datetime
    quality_state: DataQualityState = DataQualityState.VALID
    observation_date: Optional[date] = None


@dataclass
class QuarantineRecord:
    """
    Quarantine record for malformed, unmapped, or invalid observations.
    Prevents invalid data from silently flowing downstream while preserving evidence.
    """
    quarantine_id: str
    raw_record_id: str
    source_id: str
    reason: str
    quarantined_at: datetime
    raw_payload: str
