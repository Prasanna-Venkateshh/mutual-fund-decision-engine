"""
Integration Tests for Controlled Historical NAV Acquisition Prototype (Phase B).

Tests retrieval, JSON parsing, validation, Scheme Master mapping, duplicate preservation,
and quarantine routing using deterministic local fixtures.
"""

import unittest
from datetime import datetime, timezone

from db.database import DatabaseConnection
from data.ingestion.historical_nav_prototype import HistoricalNAVPrototype
from data.ingestion.amfi_ingestor import AMFIIngestor
from data.ingestion.source_registry import SourceRegistry
from data.validation.nav_validator import NAVValidator


class TestHistoricalNAVPrototype(unittest.TestCase):

    def setUp(self):
        self.db = DatabaseConnection(":memory:")
        self.prototype = HistoricalNAVPrototype(db_path=":memory:")

        # Sample deterministic AMFI API fixture matching official response payload format
        self.sample_amfi_fixture = {
            "data": [
                {
                    "schemeName": "360 ONE LIQUID FUND",
                    "navs": [
                        {
                            "SD_ID": "125337",
                            "NAV_Name": "360 ONE LIQUID FUND REGULAR PLAN  WEEKLY DIVIDEND",
                            "hNAV_Amt": "1005.4355",
                            "ISIN_RI": "INF579M01571",
                            "ISIN_PO": "INF579M01514",
                            "hNAV_Date": "2015-01-15T00:00:00.000Z",
                            "hNAV_Dtstamp": "2015-01-15T20:09:45.000Z",
                            "Plan": "Regular Plan",
                            "Option": "IDCW Option"
                        },
                        {
                            "SD_ID": "125338",
                            "NAV_Name": "360 ONE LIQUID FUND DIRECT PLAN GROWTH",
                            "hNAV_Amt": "1100.2500",
                            "ISIN_RI": "",
                            "ISIN_PO": "INF579M01506",
                            "hNAV_Date": "2015-01-15T00:00:00.000Z",
                            "hNAV_Dtstamp": "2015-01-15T20:09:45.000Z",
                            "Plan": "Direct Plan",
                            "Option": "GROWTH Option"
                        }
                    ]
                },
                {
                    "schemeName": "IIFL NIFTY ETF",
                    "navs": [
                        {
                            "SD_ID": "115912",
                            "NAV_Name": "IIFL NIFTY ETF REGULAR PLAN GROWTH",
                            "hNAV_Amt": "879.8477",
                            "ISIN_RI": "",
                            "ISIN_PO": "INF579M01019",
                            "hNAV_Date": "2015-01-15T00:00:00.000Z",
                            "hNAV_Dtstamp": "2015-01-15T20:09:45.000Z",
                            "Plan": "Regular Plan",
                            "Option": "GROWTH Option"
                        }
                    ]
                }
            ]
        }

    def test_prototype_parsing_and_pipeline_with_fixture(self):
        """Verify historical NAV parsing, validation, mapping, and database persistence."""
        res = self.prototype.fetch_historical_date_window(
            date_str="2015-01-15",
            offline_fixture=self.sample_amfi_fixture,
            use_live_network=False
        )

        self.assertEqual(res["requested_date"], "2015-01-15")
        self.assertEqual(res["http_status"], 200)
        self.assertEqual(res["raw_records_count"], 3)
        self.assertEqual(res["distinct_schemes_count"], 3)
        self.assertEqual(res["valid_records_count"], 3)
        self.assertEqual(res["quarantined_records_count"], 0)
        self.assertEqual(res["normalized_records_count"], 3)
        self.assertIn("2015-01-15", res["earliest_observation"])

    def test_duplicate_retrieval_reproducibility_and_raw_preservation(self):
        """Verify that repeated retrievals append raw records without destroying historical observations."""
        res1 = self.prototype.fetch_historical_date_window("2015-01-15", offline_fixture=self.sample_amfi_fixture, use_live_network=False)
        res2 = self.prototype.fetch_historical_date_window("2015-01-15", offline_fixture=self.sample_amfi_fixture, use_live_network=False)

        self.assertEqual(res1["raw_records_count"], 3)
        self.assertEqual(res2["raw_records_count"], 3)

        # Check raw observations table count in SQLite DB
        with self.prototype.db.get_conn() as conn:
            cursor = conn.execute("SELECT COUNT(*) as cnt FROM raw_nav_observations")
            total_raw = cursor.fetchone()["cnt"]
            self.assertEqual(total_raw, 6)  # Both retrievals preserved with distinct raw_record_ids

    def test_quarantine_handling_for_invalid_historical_records(self):
        """Verify that malformed historical records (negative NAV, unparseable date) are quarantined."""
        invalid_fixture = {
            "data": [
                {
                    "schemeName": "TEST BAD FUND",
                    "navs": [
                        {
                            "SD_ID": "999001",
                            "NAV_Name": "TEST INVALID NAV FUND",
                            "hNAV_Amt": "-5.0000",  # Invalid negative NAV
                            "hNAV_Date": "2015-01-15T00:00:00.000Z",
                        },
                        {
                            "SD_ID": "999002",
                            "NAV_Name": "TEST INVALID DATE FUND",
                            "hNAV_Amt": "100.0000",
                            "hNAV_Date": "INVALID-DATE-STRING",  # Unparseable date
                        }
                    ]
                }
            ]
        }

        res = self.prototype.fetch_historical_date_window("2015-01-15", offline_fixture=invalid_fixture, use_live_network=False)
        self.assertEqual(res["raw_records_count"], 2)
        self.assertEqual(res["valid_records_count"], 0)
        self.assertEqual(res["quarantined_records_count"], 2)
        self.assertEqual(self.prototype.repo.get_quarantine_count(), 2)

    def test_pre_2010_empty_boundary_response(self):
        """Verify behavior when source returns 'No records to display' for pre-2010 boundary windows."""
        empty_fixture = {"message": "No records to display"}
        res = self.prototype.fetch_historical_date_window("2006-01-15", offline_fixture=empty_fixture, use_live_network=False)

        self.assertEqual(res["raw_records_count"], 0)
        self.assertEqual(res["valid_records_count"], 0)
        self.assertEqual(res["quarantined_records_count"], 0)
        self.assertIsNone(res["earliest_observation"])


if __name__ == "__main__":
    unittest.main()
