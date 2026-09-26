"""
Source Registry Manager.

Loads, validates, and exposes authoritative source records from config/sources/sources.json
as specified in ARCHITECTURE.md Section 6.
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

from models.source import SourceRecord, AuthorityLevel, ValidationStatus
from db.database import DatabaseConnection


class SourceRegistry:
    """Manages the catalog of data sources, their authority levels, and validation status."""

    def __init__(self, config_path: str = "config/sources/sources.json", db: Optional[DatabaseConnection] = None):
        self.config_path = config_path
        self.db = db
        self._sources: Dict[str, SourceRecord] = {}
        self.load_registry()

    def load_registry(self) -> None:
        """Load sources from JSON config file into memory and database."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Source registry file not found at {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            source = SourceRecord(
                source_id=item["source_id"],
                source_name=item["source_name"],
                source_type=item["source_type"],
                authority_level=AuthorityLevel[item["authority_level"]],
                official_url=item["official_url"],
                specific_data_url=item["specific_data_url"],
                supported_data_fields=item["supported_data_fields"],
                update_frequency=item["update_frequency"],
                historical_availability=item["historical_availability"],
                free_status=item.get("free_status", True),
                licensing_status=item.get("licensing_status", "PUBLIC_DOMAIN"),
                validation_status=ValidationStatus[item.get("validation_status", "PROVISIONAL")],
            )
            self._sources[source.source_id] = source

        if self.db:
            self._sync_to_db()

    def get_source(self, source_id: str) -> Optional[SourceRecord]:
        """Retrieve source record by ID."""
        return self._sources.get(source_id)

    def list_sources(self) -> List[SourceRecord]:
        """Return all registered sources sorted by authority level."""
        return sorted(list(self._sources.values()), key=lambda s: s.authority_level.value)

    def update_retrieval_status(self, source_id: str, success: bool, timestamp: Optional[datetime] = None) -> None:
        """Update last retrieval timestamp and validation status for a source."""
        source = self.get_source(source_id)
        if not source:
            raise ValueError(f"Unknown source ID: {source_id}")

        ts = timestamp or datetime.now(timezone.utc)
        if success:
            source.last_successful_retrieval = ts
            source.validation_status = ValidationStatus.VALIDATED
        else:
            source.validation_status = ValidationStatus.FAILED

        if self.db:
            with self.db.get_conn() as conn:
                conn.execute(
                    """
                    UPDATE source_registry 
                    SET last_successful_retrieval = ?, validation_status = ?
                    WHERE source_id = ?
                    """,
                    (ts.isoformat(), source.validation_status.value, source_id)
                )

    def _sync_to_db(self) -> None:
        """Persist source records into SQLite database."""
        with self.db.get_conn() as conn:
            for s in self._sources.values():
                conn.execute(
                    """
                    INSERT OR REPLACE INTO source_registry (
                        source_id, source_name, source_type, authority_level,
                        official_url, specific_data_url, supported_data_fields,
                        update_frequency, historical_availability, free_status,
                        licensing_status, validation_status, last_successful_retrieval,
                        last_validation_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        s.source_id, s.source_name, s.source_type, s.authority_level.name,
                        s.official_url, s.specific_data_url, json.dumps(s.supported_data_fields),
                        s.update_frequency, s.historical_availability, 1 if s.free_status else 0,
                        s.licensing_status, s.validation_status.value,
                        s.last_successful_retrieval.isoformat() if s.last_successful_retrieval else None,
                        s.last_validation_date.isoformat() if s.last_validation_date else None,
                    )
                )
