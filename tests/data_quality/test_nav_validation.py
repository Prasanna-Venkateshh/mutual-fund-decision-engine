"""
Unit and Data Quality Tests for NAV Validation Gate.

Verifies strict validation rules: positive NAV values, date parsing, missing values,
and quarantine isolation.
"""

import unittest
from datetime import datetime, date, timezone
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from models.nav_data import RawNAVRecord, DataQualityState
from data.validation.nav_validator import NAVValidator


class TestNAVValidator(unittest.TestCase):
    """Test suite for NAVValidator."""

    def setUp(self):
        self.validator = NAVValidator()
        self.ts = datetime.now(timezone.utc)

    def test_valid_record(self):
        """Test that a valid raw observation passes validation gate."""
        raw = RawNAVRecord(
            raw_record_id="raw_1",
            source_id="AMFI_OFFICIAL",
            retrieval_timestamp=self.ts,
            raw_scheme_code="119551",
            raw_scheme_name="Aditya Birla Sun Life Banking & PSU Debt Fund - Direct Plan-Growth",
            raw_nav_value="394.9197",
            raw_date="30-Apr-2026"
        )
        res = self.validator.validate_raw_record(raw)
        self.assertTrue(res.is_valid)
        self.assertEqual(res.quality_state, DataQualityState.VALID)
        self.assertEqual(res.parsed_nav, 394.9197)
        self.assertEqual(res.parsed_date, date(2026, 4, 30))

    def test_missing_scheme_name_incomplete(self):
        """Test that missing scheme name results in INCOMPLETE quality state."""
        raw = RawNAVRecord(
            raw_record_id="raw_2",
            source_id="AMFI_OFFICIAL",
            retrieval_timestamp=self.ts,
            raw_scheme_code="119551",
            raw_scheme_name="",
            raw_nav_value="100.0",
            raw_date="30-Apr-2026"
        )
        res = self.validator.validate_raw_record(raw)
        self.assertFalse(res.is_valid)
        self.assertEqual(res.quality_state, DataQualityState.INCOMPLETE)

    def test_negative_or_zero_nav_invalid(self):
        """Test that zero or negative NAV is rejected as INVALID."""
        raw_zero = RawNAVRecord(
            raw_record_id="raw_3",
            source_id="AMFI_OFFICIAL",
            retrieval_timestamp=self.ts,
            raw_scheme_code="119551",
            raw_scheme_name="Sample Fund",
            raw_nav_value="0.0",
            raw_date="30-Apr-2026"
        )
        res_zero = self.validator.validate_raw_record(raw_zero)
        self.assertFalse(res_zero.is_valid)
        self.assertEqual(res_zero.quality_state, DataQualityState.INVALID)

        raw_neg = RawNAVRecord(
            raw_record_id="raw_4",
            source_id="AMFI_OFFICIAL",
            retrieval_timestamp=self.ts,
            raw_scheme_code="119551",
            raw_scheme_name="Sample Fund",
            raw_nav_value="-10.5",
            raw_date="30-Apr-2026"
        )
        res_neg = self.validator.validate_raw_record(raw_neg)
        self.assertFalse(res_neg.is_valid)
        self.assertEqual(res_neg.quality_state, DataQualityState.INVALID)

    def test_malformed_nav_string_invalid(self):
        """Test that non-numeric NAV strings are rejected."""
        raw = RawNAVRecord(
            raw_record_id="raw_5",
            source_id="AMFI_OFFICIAL",
            retrieval_timestamp=self.ts,
            raw_scheme_code="119551",
            raw_scheme_name="Sample Fund",
            raw_nav_value="N/A",
            raw_date="30-Apr-2026"
        )
        res = self.validator.validate_raw_record(raw)
        self.assertFalse(res.is_valid)
        self.assertEqual(res.quality_state, DataQualityState.INVALID)

    def test_malformed_date_invalid(self):
        """Test that invalid date strings are rejected."""
        raw = RawNAVRecord(
            raw_record_id="raw_6",
            source_id="AMFI_OFFICIAL",
            retrieval_timestamp=self.ts,
            raw_scheme_code="119551",
            raw_scheme_name="Sample Fund",
            raw_nav_value="150.0",
            raw_date="INVALID-DATE-999"
        )
        res = self.validator.validate_raw_record(raw)
        self.assertFalse(res.is_valid)
        self.assertEqual(res.quality_state, DataQualityState.INVALID)

    def test_batch_quarantine_isolation(self):
        """Test that invalid records in a batch are isolated into quarantine objects."""
        records = [
            RawNAVRecord("r1", "AMFI", self.ts, "101", "Good Fund", "100.0", "30-Apr-2026"),
            RawNAVRecord("r2", "AMFI", self.ts, "102", "Bad NAV Fund", "-50.0", "30-Apr-2026"),
            RawNAVRecord("r3", "AMFI", self.ts, "103", "Bad Date Fund", "100.0", "BAD-DATE"),
        ]
        valid_tuples, quarantine = self.validator.process_and_quarantine(records)
        self.assertEqual(len(valid_tuples), 1)
        self.assertEqual(len(quarantine), 2)
        self.assertEqual(valid_tuples[0][0].raw_scheme_code, "101")


if __name__ == "__main__":
    unittest.main()
