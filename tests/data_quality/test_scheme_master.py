"""
Unit and Data Quality Tests for Scheme Master & Normalization.

Verifies plan/option parsing, canonical scheme resolution, mapping confidence levels,
and normalization quarantine enforcement.
"""

import unittest
from datetime import datetime, date, timezone
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from models.nav_data import RawNAVRecord, ValidationResult, DataQualityState
from models.scheme import PlanType, OptionType, MappingConfidence
from data.mapping.scheme_master import SchemeMaster
from data.normalization.nav_normalizer import NAVNormalizer


class TestSchemeMaster(unittest.TestCase):
    """Test suite for SchemeMaster and NAVNormalizer."""

    def setUp(self):
        self.scheme_master = SchemeMaster()
        self.normalizer = NAVNormalizer(self.scheme_master)
        self.ts = datetime.now(timezone.utc)

    def test_parse_plan_and_option(self):
        """Verify plan and option extraction from raw scheme names."""
        plan1, opt1 = self.scheme_master.parse_plan_and_option("Axis Banking & PSU Debt Fund - Direct Plan - Growth Option")
        self.assertEqual(plan1, PlanType.DIRECT)
        self.assertEqual(opt1, OptionType.GROWTH)

        plan2, opt2 = self.scheme_master.parse_plan_and_option("Aditya Birla Sun Life Banking & PSU Debt Fund - REGULAR - MONTHLY IDCW")
        self.assertEqual(plan2, PlanType.REGULAR)
        self.assertEqual(opt2, OptionType.IDCW)

    def test_resolve_canonical_scheme_exact_match(self):
        """Verify scheme mapping resolution with exact match confidence."""
        canonical, mapping = self.scheme_master.resolve_or_create_canonical_scheme(
            source_id="AMFI_OFFICIAL",
            source_scheme_code="119551",
            source_scheme_name="Aditya Birla Sun Life Banking & PSU Debt Fund - Direct Plan-Growth"
        )
        self.assertEqual(mapping.confidence, MappingConfidence.EXACT_MATCH)
        self.assertEqual(canonical.plan_type, PlanType.DIRECT)
        self.assertEqual(canonical.option_type, OptionType.GROWTH)
        self.assertEqual(canonical.amc_name, "Aditya Birla Sun Life")

    def test_ambiguous_scheme_name_quarantined_during_normalization(self):
        """Verify that a scheme name lacking plan/option information is marked AMBIGUOUS and quarantined during normalization."""
        raw = RawNAVRecord(
            raw_record_id="raw_ambiguous_1",
            source_id="AMFI_OFFICIAL",
            raw_scheme_code="99999",
            raw_scheme_name="Generic Fund Name Without Plan Or Option",
            raw_nav_value="50.0",
            raw_date="30-Apr-2026",
            retrieval_timestamp=self.ts
        )
        val_res = ValidationResult(
            is_valid=True,
            quality_state=DataQualityState.VALID,
            parsed_scheme_code="99999",
            parsed_scheme_name="Generic Fund Name Without Plan Or Option",
            parsed_nav=50.0,
            parsed_date=date(2026, 4, 30)
        )

        norm_rec, q_rec = self.normalizer.normalize_record(raw, val_res)
        self.assertIsNone(norm_rec)
        self.assertIsNotNone(q_rec)
        self.assertIn("AMBIGUOUS", q_rec.reason)

    def test_isin_attribute_preservation(self):
        """
        Verify that ISIN metadata (isin_growth) is correctly preserved on the CanonicalScheme entity.
        
        Note on Architectural Scope:
        The current SchemeMaster preserves ISIN attributes when provided during resolution.
        Full ISIN fallback index lookup (resolving unknown scheme codes solely via ISIN master tables)
        is an enhancement for future data slices when official AMFI ISIN master feeds are integrated.
        """
        canonical, mapping = self.scheme_master.resolve_or_create_canonical_scheme(
            source_id="AMFI_OFFICIAL",
            source_scheme_code="119551",
            source_scheme_name="Aditya Birla Sun Life Banking & PSU Debt Fund - Direct Plan-Growth",
            isin_growth="INF200K01VR1"
        )
        self.assertEqual(canonical.isin_growth, "INF200K01VR1")
        self.assertEqual(mapping.confidence, MappingConfidence.EXACT_MATCH)


if __name__ == "__main__":
    unittest.main()
