"""
Abstract Base Ingestor Interface.

Defines the contract for raw data ingestion as required by ARCHITECTURE.md Section 4 & 5.
Ingestion adapters MUST preserve raw observations without modifying data before validation.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime

from models.nav_data import RawNAVRecord
from data.ingestion.source_registry import SourceRegistry


class BaseIngestor(ABC):
    """Abstract base class for all data ingestion adapters."""

    def __init__(self, source_id: str, registry: SourceRegistry):
        self.source_id = source_id
        self.registry = registry
        self.source = registry.get_source(source_id)
        if not self.source:
            raise ValueError(f"Ingestor initialized with unregistered source_id: {source_id}")

    @abstractmethod
    def fetch_raw_data(self, **kwargs) -> List[RawNAVRecord]:
        """
        Fetch raw data from external feed or local snapshot.
        MUST return unmodified RawNAVRecord instances preserving source provenance.
        """
        pass
