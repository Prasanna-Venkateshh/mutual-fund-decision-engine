"""
Integration Tests for Slice 1 Data Pipeline.

Verifies end-to-end data ingestion, validation, canonical entity resolution,
SQLite database persistence, and historical NAV query operations.
"""

import unittest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from db.database import DatabaseConnection
from data.ingestion.source_registry import SourceRegistry
from data.ingestion.amfi_ingestor import AMFIIngestor
from data.validation.nav_validator import NAVValidator
from data.mapping.scheme_master import SchemeMaster
from data.normalization.nav_normalizer import NAVNormalizer
from data.repositories.nav_repository import NAVRepository


class TestIngestionPipelineIntegration(unittest.TestCase):
    """Integration test suite for Slice 1 data architecture."""

    def setUp(self):
        self.db = DatabaseConnection(":memory:")
        self.registry = SourceRegistry(config_path="config/sources/sources.json", db=self.db)
        self.ingestor = AMFIIngestor(registry=self.registry)
        self.validator = NAVValidator()
        self.scheme_master = SchemeMaster()
        self.normalizer = NAVNormalizer(self.scheme_master)
        self.repo = NAVRepository(db=self.db)

    def test_end_to_end_amfi_text_ingestion(self):
        """Test full pipeline execution from raw text to database query."""
        raw_text = """
119551;INF200K01VR1;INF200K01VS9;Aditya Birla Sun Life Banking & PSU Debt Fund - Direct Plan-Growth;394.9197;30-Apr-2026
119552;INF200K01VT7;INF200K01VU5;Aditya Birla Sun Life Banking & PSU Debt Fund - Regular Plan-Growth;379.4426;30-Apr-2026
INVALID_CODE;;;Bad Fund Name Without Code;-100.0;30-Apr-2026
        """

        # Step 1: Raw Ingestion
        raw_records = self.ingestor.fetch_raw_data(content=raw_text, format_type="txt")
        self.assertEqual(len(raw_records), 3)
        inserted_raw = self.repo.save_raw_observations(raw_records)
        self.assertEqual(inserted_raw, 3)

        # Step 2: Validation Gate
        valid_tuples, quarantine1 = self.validator.process_and_quarantine(raw_records)
        self.assertEqual(len(valid_tuples), 2)
        self.assertEqual(len(quarantine1), 1)  # Bad NAV Fund quarantined

        # Step 3: Normalization & Scheme Master
        normalized_records, quarantine2 = self.normalizer.normalize_batch(valid_tuples)
        self.assertEqual(len(normalized_records), 2)
        
        all_quarantine = quarantine1 + quarantine2
        self.repo.save_quarantine_records(all_quarantine)

        # Save Canonical Schemes and Mappings
        for norm in normalized_records:
            canonical = self.scheme_master._canonical_schemes.get(norm.canonical_scheme_id)
            if canonical:
                self.repo.save_canonical_scheme(canonical)

        # Save Normalized Records
        inserted_norm = self.repo.save_normalized_records(normalized_records)
        self.assertEqual(inserted_norm, 2)

        # Step 4: Verify Database Persistence & Query
        history = self.repo.get_normalized_nav_history("CAN_AMFI_119551")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["nav_value"], 394.9197)
        self.assertEqual(history[0]["nav_date"], "2026-04-30")
        self.assertEqual(history[0]["source_id"], "AMFI_OFFICIAL")

        # Step 5: Verify Quarantine Count
        self.assertEqual(self.repo.get_quarantine_count(), 1)

    def test_idempotent_raw_observation_persistence(self):
        """Verify re-ingesting duplicate raw observations does not overwrite historical records."""
        raw_text = "119551;INF200K01VR1;INF200K01VS9;Aditya Birla Sun Life Banking & PSU Debt Fund - Direct Plan-Growth;394.9197;30-Apr-2026"
        raw_records = self.ingestor.fetch_raw_data(content=raw_text, format_type="txt")

        inserted1 = self.repo.save_raw_observations(raw_records)
        self.assertEqual(inserted1, 1)

        # Attempt to insert exact same raw record IDs
        inserted2 = self.repo.save_raw_observations(raw_records)
        self.assertEqual(inserted2, 0)  # IGNORED by SQLite INSERT OR IGNORE


if __name__ == "__main__":
    unittest.main()
