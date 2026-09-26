"""
Unit and Data Quality Tests for Source Registry.

Verifies metadata fields, authority priority hierarchy, and status updating.
"""

import unittest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from db.database import DatabaseConnection
from data.ingestion.source_registry import SourceRegistry
from models.source import AuthorityLevel, ValidationStatus


class TestSourceRegistry(unittest.TestCase):
    """Test suite for SourceRegistry."""

    def setUp(self):
        self.db = DatabaseConnection(":memory:")
        self.config_path = "config/sources/sources.json"
        self.registry = SourceRegistry(config_path=self.config_path, db=self.db)

    def test_load_sources_from_config(self):
        """Verify sources load cleanly from configuration file."""
        sources = self.registry.list_sources()
        self.assertGreater(len(sources), 0)
        
        amfi_source = self.registry.get_source("AMFI_OFFICIAL")
        self.assertIsNotNone(amfi_source)
        self.assertEqual(amfi_source.authority_level, AuthorityLevel.AMFI)
        self.assertEqual(amfi_source.official_url, "https://www.amfiindia.com")
        self.assertTrue(amfi_source.free_status)

    def test_authority_level_priority_sorting(self):
        """Verify sources sort correctly by authority priority hierarchy."""
        sources = self.registry.list_sources()
        # AMFI (1) should precede SEBI (2) and Third Party (7)
        self.assertEqual(sources[0].authority_level, AuthorityLevel.AMFI)

    def test_update_retrieval_status(self):
        """Verify retrieval status updates persist in database."""
        self.registry.update_retrieval_status("AMFI_OFFICIAL", success=True)
        amfi_source = self.registry.get_source("AMFI_OFFICIAL")
        self.assertEqual(amfi_source.validation_status, ValidationStatus.VALIDATED)
        self.assertIsNotNone(amfi_source.last_successful_retrieval)

        # Check DB sync
        with self.db.get_conn() as conn:
            cursor = conn.execute("SELECT validation_status FROM source_registry WHERE source_id = 'AMFI_OFFICIAL'")
            row = cursor.fetchone()
            self.assertEqual(row["validation_status"], "VALIDATED")


if __name__ == "__main__":
    unittest.main()
