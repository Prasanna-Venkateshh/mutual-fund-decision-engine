"""
Data models for Data Sources and Source Registry.

As specified in ARCHITECTURE.md Section 6 and PRODUCT_SPEC.md Section 24,
every data source must be tracked with its authority level, URL, update frequency,
and validation status to ensure full source provenance.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional


class AuthorityLevel(Enum):
    """Authority priority hierarchy as defined in PRODUCT_SPEC.md Section 24.3."""
    AMFI = 1
    SEBI = 2
    RBI = 3
    INCOME_TAX_CBDT = 4
    AMC_OFFICIAL = 5
    EXCHANGE_NSE_BSE = 6
    UNVALIDATED_THIRD_PARTY = 7


class ValidationStatus(Enum):
    """Validation status for data sources."""
    VALIDATED = "VALIDATED"
    PROVISIONAL = "PROVISIONAL"
    FAILED = "FAILED"
    UNVALIDATED = "UNVALIDATED"
    UNAVAILABLE_HTTP_404 = "UNAVAILABLE_HTTP_404"
    UNUNIFORM_FRAGMENTED_AMC = "UNUNIFORM_FRAGMENTED_AMC"
    DEPRECATED = "DEPRECATED"


@dataclass
class SourceRecord:
    """
    Source metadata record capturing provenance and usage rights.
    Corresponds to Source Registry catalogue fields in ARCHITECTURE.md Section 6.
    """
    source_id: str
    source_name: str
    source_type: str  # e.g., "NAV_FEED", "TAX_RULES", "BENCHMARK"
    authority_level: AuthorityLevel
    official_url: str
    specific_data_url: str
    supported_data_fields: List[str]
    update_frequency: str  # e.g., "DAILY", "REALTIME", "ANNUAL"
    historical_availability: str
    free_status: bool = True
    licensing_status: str = "PUBLIC_DOMAIN"
    validation_status: ValidationStatus = ValidationStatus.PROVISIONAL
    last_successful_retrieval: Optional[datetime] = None
    last_validation_date: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Serialize source record to a dictionary for persistence or API export."""
        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "source_type": self.source_type,
            "authority_level": self.authority_level.name,
            "official_url": self.official_url,
            "specific_data_url": self.specific_data_url,
            "supported_data_fields": self.supported_data_fields,
            "update_frequency": self.update_frequency,
            "historical_availability": self.historical_availability,
            "free_status": self.free_status,
            "licensing_status": self.licensing_status,
            "validation_status": self.validation_status.value,
            "last_successful_retrieval": self.last_successful_retrieval.isoformat() if self.last_successful_retrieval else None,
            "last_validation_date": self.last_validation_date.isoformat() if self.last_validation_date else None,
        }
