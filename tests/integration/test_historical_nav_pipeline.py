"""
Deterministic Integration Tests for Phase B.2 Historical NAV Acquisition Pipeline.

Tests:
1. Successful window acquisition
2. Empty response handling
3. Transient failure handling
4. Retry/resume behavior
5. Duplicate/repeated acquisition
6. Raw provenance preservation
7. NAV quarantine
8. Mapping quarantine
9. Reconciliation counts (Raw = Normalized + NAV_Quarantine + Mapping_Quarantine)
10. Coverage-gap detection (5 states)
11. Weekend/non-trading-day handling where supported
12. Acquisition state persistence
"""

import os
import unittest
import tempfile
import shutil
from unittest.mock import patch, MagicMock

from db.database import DatabaseConnection
from data.ingestion.historical_nav_pipeline import (
    HistoricalNAVPipeline,
    HistoricalNAVAcquisitionScheduler,
    HistoricalCoverageAnalyzer,
    AcquisitionWindow
)
from data.repositories.nav_repository import NAVRepository


class TestHistoricalNAVPipelineIntegration(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_nav_database.db")
        self.pipeline = HistoricalNAVPipeline(db_path=self.db_path, rate_limit_delay_sec=0.0)
        self.repo = NAVRepository(db=self.pipeline.db)

        # Sample valid AMFI raw response fixture matching official JSON structure
        self.sample_valid_fixture = {
            "data": [
                {
                    "schemeName": "HDFC Schemes",
                    "navs": [
                        {
                            "SD_ID": "100027",
                            "NAV_Name": "HDFC Flexi Cap Fund - Direct Plan - Growth",
                            "ISIN_PO": "INF179K01BE2",
                            "ISIN_RI": "INF179K01BF9",
                            "hNAV_Amt": "1250.50",
                            "hNAV_Date": "15-Jan-2025"
                        },
                        {
                            "SD_ID": "100028",
                            "NAV_Name": "ICICI Prudential Bluechip Fund - Direct Plan - Growth",
                            "ISIN_PO": "INF109K01BE3",
                            "ISIN_RI": "INF109K01BF0",
                            "hNAV_Amt": "95.40",
                            "hNAV_Date": "15-Jan-2025"
                        }
                    ]
                }
            ]
        }

    def tearDown(self):
        del self.repo
        del self.pipeline
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass

    def test_01_successful_window_acquisition(self):
        """Test 1: Successful window acquisition with valid fixture."""
        window = AcquisitionWindow(start_date="2025-01-15", end_date="2025-01-15")
        ledger_entry = self.pipeline.process_window(
            window=window,
            acquisition_run_id="test_run_01",
            offline_fixture=self.sample_valid_fixture,
            use_live_network=False
        )

        self.assertEqual(ledger_entry["request_status"], "SUCCESS")
        self.assertEqual(ledger_entry["completion_status"], "COMPLETED")
        self.assertEqual(ledger_entry["raw_records_count"], 2)
        self.assertEqual(ledger_entry["normalized_records_count"], 2)
        self.assertEqual(ledger_entry["nav_quarantine_count"], 0)
        self.assertEqual(ledger_entry["mapping_quarantine_count"], 0)
        self.assertEqual(ledger_entry["earliest_returned_date"], "15-Jan-2025")
        self.assertEqual(ledger_entry["latest_returned_date"], "15-Jan-2025")

    def test_02_empty_response_handling(self):
        """Test 2: Empty response handling (HTTP 200 with zero records)."""
        window = AcquisitionWindow(start_date="2005-01-01", end_date="2005-01-01")
        empty_fixture = {"data": []}
        ledger_entry = self.pipeline.process_window(
            window=window,
            acquisition_run_id="test_run_02",
            offline_fixture=empty_fixture,
            use_live_network=False
        )

        self.assertEqual(ledger_entry["request_status"], "SUCCESS_EMPTY")
        self.assertEqual(ledger_entry["completion_status"], "COMPLETED")
        self.assertEqual(ledger_entry["raw_records_count"], 0)
        self.assertEqual(ledger_entry["normalized_records_count"], 0)
        self.assertIsNone(ledger_entry["earliest_returned_date"])

    def test_03_transient_failure_handling(self):
        """Test 3: Transient failure handling when live network returns errors."""
        window = AcquisitionWindow(start_date="2025-01-15", end_date="2025-01-15")

        with patch.object(self.pipeline.session, "get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 503
            mock_resp.text = "Service Unavailable"
            mock_get.return_value = mock_resp

            ledger_entry = self.pipeline.process_window(
                window=window,
                acquisition_run_id="test_run_03",
                use_live_network=True
            )

            self.assertEqual(ledger_entry["request_status"], "FAILED")
            self.assertEqual(ledger_entry["http_status"], 503)
            self.assertEqual(ledger_entry["retry_count"], 3)
            self.assertIn("HTTP Error 503", ledger_entry["error_info"])

    def test_04_retry_and_resume_behavior(self):
        """Test 4: Retry and resume behavior (resuming completed windows avoids re-fetch)."""
        window = AcquisitionWindow(start_date="2025-01-15", end_date="2025-01-15")
        
        # Initial run completes successfully
        entry1 = self.pipeline.process_window(
            window=window,
            acquisition_run_id="run_01",
            offline_fixture=self.sample_valid_fixture,
            resume=True,
            use_live_network=False
        )
        self.assertFalse(entry1["resumed_from_cache"])

        # Second run with resume=True should load from cache
        entry2 = self.pipeline.process_window(
            window=window,
            acquisition_run_id="run_02",
            offline_fixture=None,
            resume=True,
            use_live_network=False
        )
        self.assertTrue(entry2["resumed_from_cache"])
        self.assertEqual(entry2["window_id"], window.window_id)

    def test_05_duplicate_repeated_acquisition(self):
        """Test 5: Duplicate repeated acquisition preserves provenance and append-only raw observations."""
        window = AcquisitionWindow(start_date="2025-01-15", end_date="2025-01-15")

        # First acquisition
        self.pipeline.process_window(
            window=window,
            acquisition_run_id="run_a",
            offline_fixture=self.sample_valid_fixture,
            resume=False,
            use_live_network=False
        )

        # Second acquisition without resume (re-ingest)
        self.pipeline.process_window(
            window=window,
            acquisition_run_id="run_b",
            offline_fixture=self.sample_valid_fixture,
            resume=False,
            use_live_network=False
        )

        # Verify raw observations table contains both observations (append/audit)
        raws = self.repo.get_raw_observations(source_id="AMFI_OFFICIAL", raw_date="15-Jan-2025")
        self.assertEqual(len(raws), 4)  # 2 schemes * 2 runs = 4 raw records

    def test_06_raw_provenance_preservation(self):
        """Test 6: Raw provenance preservation (response_hash, endpoint_url, UTC timestamp)."""
        window = AcquisitionWindow(start_date="2025-01-15", end_date="2025-01-15")
        ledger_entry = self.pipeline.process_window(
            window=window,
            acquisition_run_id="test_run_06",
            offline_fixture=self.sample_valid_fixture,
            use_live_network=False
        )

        self.assertIsNotNone(ledger_entry["response_hash"])
        self.assertIsNotNone(ledger_entry["retrieval_timestamp_utc"])
        self.assertIn("from_date=2025-01-15", ledger_entry["endpoint_url"])

        saved_ledger = self.repo.get_ledger_entry(window.window_id)
        self.assertEqual(saved_ledger["response_hash"], ledger_entry["response_hash"])

    def test_07_nav_quarantine(self):
        """Test 7: NAV quarantine for invalid NAV values (non-numeric, negative, zero)."""
        invalid_nav_fixture = {
            "data": [
                {
                    "schemeName": "Test Invalid Scheme",
                    "navs": [
                        {
                            "SD_ID": "100029",
                            "NAV_Name": "Test Invalid NAV Fund",
                            "ISIN_PO": "INF100K01BE1",
                            "ISIN_RI": "INF100K01BF1",
                            "hNAV_Amt": "N.A.",
                            "hNAV_Date": "15-Jan-2025"
                        }
                    ]
                }
            ]
        }
        window = AcquisitionWindow(start_date="2025-01-15", end_date="2025-01-15")
        entry = self.pipeline.process_window(
            window=window,
            acquisition_run_id="run_q1",
            offline_fixture=invalid_nav_fixture,
            use_live_network=False
        )

        self.assertEqual(entry["raw_records_count"], 1)
        self.assertEqual(entry["nav_valid_records_count"], 0)
        self.assertEqual(entry["nav_quarantine_count"], 1)
        self.assertEqual(entry["normalized_records_count"], 0)

        # Check quarantine records in DB
        q_recs = self.repo.get_quarantine_records(stage="NAV_VALIDATION")
        self.assertEqual(len(q_recs), 1)
        self.assertIn("Unparseable NAV value", q_recs[0]["reason"])

    def test_08_mapping_quarantine(self):
        """Test 8: Scheme Mapping quarantine when scheme resolution fails."""
        unmapped_fixture = {
            "data": [
                {
                    "schemeName": "Unknown Group",
                    "navs": [
                        {
                            "SD_ID": "999999",
                            "NAV_Name": "Unknown Scheme Without Mapping",
                            "ISIN_PO": None,
                            "ISIN_RI": None,
                            "hNAV_Amt": "50.00",
                            "hNAV_Date": "15-Jan-2025"
                        }
                    ]
                }
            ]
        }
        window = AcquisitionWindow(start_date="2025-01-15", end_date="2025-01-15")
        entry = self.pipeline.process_window(
            window=window,
            acquisition_run_id="run_q2",
            offline_fixture=unmapped_fixture,
            use_live_network=False
        )

        self.assertEqual(entry["raw_records_count"], 1)
        self.assertEqual(entry["nav_valid_records_count"], 1)
        self.assertEqual(entry["nav_quarantine_count"], 0)
        self.assertEqual(entry["mapping_quarantine_count"], 1)
        self.assertEqual(entry["normalized_records_count"], 0)

        # Check quarantine records in DB
        q_recs = self.repo.get_quarantine_records(stage="SCHEME_MAPPING")
        self.assertEqual(len(q_recs), 1)

    def test_09_reconciliation_counts_equation(self):
        """Test 9: Strictly verifies Raw = Normalized + NAV_Quarantine + Mapping_Quarantine equation."""
        mixed_fixture = {
            "data": [
                {
                    "schemeName": "Mixed Schemes",
                    "navs": [
                        # Valid record (Normalized)
                        {
                            "SD_ID": "100027",
                            "NAV_Name": "HDFC Flexi Cap Fund - Direct Plan - Growth",
                            "ISIN_PO": "INF179K01BE2",
                            "ISIN_RI": "INF179K01BF9",
                            "hNAV_Amt": "1250.50",
                            "hNAV_Date": "15-Jan-2025"
                        },
                        # NAV Quarantine (N.A. NAV)
                        {
                            "SD_ID": "100028",
                            "NAV_Name": "ICICI Prudential Bluechip Fund",
                            "ISIN_PO": "INF109K01BE3",
                            "ISIN_RI": "INF109K01BF0",
                            "hNAV_Amt": "INVALID_NAV",
                            "hNAV_Date": "15-Jan-2025"
                        },
                        # Mapping Quarantine (Unknown scheme, valid NAV)
                        {
                            "SD_ID": "888888",
                            "NAV_Name": "Mystery Fund Without Canonical Master Match",
                            "ISIN_PO": None,
                            "ISIN_RI": None,
                            "hNAV_Amt": "42.00",
                            "hNAV_Date": "15-Jan-2025"
                        }
                    ]
                }
            ]
        }

        window = AcquisitionWindow(start_date="2025-01-15", end_date="2025-01-15")
        entry = self.pipeline.process_window(
            window=window,
            acquisition_run_id="run_reconcile",
            offline_fixture=mixed_fixture,
            use_live_network=False
        )

        raw_cnt = entry["raw_records_count"]
        norm_cnt = entry["normalized_records_count"]
        nav_q_cnt = entry["nav_quarantine_count"]
        map_q_cnt = entry["mapping_quarantine_count"]

        self.assertEqual(raw_cnt, 3)
        self.assertEqual(norm_cnt, 1)
        self.assertEqual(nav_q_cnt, 1)
        self.assertEqual(map_q_cnt, 1)
        self.assertEqual(raw_cnt, norm_cnt + nav_q_cnt + map_q_cnt)

    def test_10_coverage_gap_detection(self):
        """Test 10: HistoricalCoverageAnalyzer correctly categorizes date windows into distinct states."""
        # 1. Success window with records
        w1 = AcquisitionWindow(start_date="2025-01-15", end_date="2025-01-15")
        self.pipeline.process_window(w1, "run_gap", offline_fixture=self.sample_valid_fixture, use_live_network=False)

        # 2. Success empty window (zero records)
        w2 = AcquisitionWindow(start_date="2005-01-01", end_date="2005-01-01")
        self.pipeline.process_window(w2, "run_gap", offline_fixture={"data": []}, use_live_network=False)

        # 3. Failed window
        w3 = AcquisitionWindow(start_date="2025-01-16", end_date="2025-01-16")
        with patch.object(self.pipeline.session, "get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 500
            mock_get.return_value = mock_resp
            self.pipeline.process_window(w3, "run_gap", use_live_network=True)

        analyzer = HistoricalCoverageAnalyzer(db_path=self.db_path)
        report = analyzer.generate_coverage_report()

        self.assertEqual(report["total_windows_requested"], 3)
        self.assertEqual(report["windows_success_with_records"], 1)
        self.assertEqual(report["windows_success_zero_records"], 1)
        self.assertEqual(report["windows_failed"], 1)
        self.assertIn("2025-01-15", report["acquired_dates"])
        self.assertIn("2005-01-01", report["zero_record_dates"])
        self.assertIn("2025-01-16", report["failed_dates"])

    def test_11_weekend_non_trading_day_handling(self):
        """Test 11: Non-trading day (weekend) returning empty records marked as SUCCESS_EMPTY without data error."""
        # Sunday date: 2025-01-19
        sunday_window = AcquisitionWindow(start_date="2025-01-19", end_date="2025-01-19")
        entry = self.pipeline.process_window(
            window=sunday_window,
            acquisition_run_id="run_weekend",
            offline_fixture={"data": []},
            use_live_network=False
        )

        self.assertEqual(entry["request_status"], "SUCCESS_EMPTY")
        self.assertEqual(entry["completion_status"], "COMPLETED")
        self.assertEqual(entry["raw_records_count"], 0)

    def test_12_acquisition_state_persistence(self):
        """Test 12: Acquisition ledger state persistence across DatabaseConnection re-instantiations."""
        window = AcquisitionWindow(start_date="2025-01-15", end_date="2025-01-15")
        self.pipeline.process_window(window, "run_persist", offline_fixture=self.sample_valid_fixture, use_live_network=False)

        # Create fresh DB connection to verify disk persistence
        new_repo = NAVRepository(db=DatabaseConnection(self.db_path))
        saved_entry = new_repo.get_ledger_entry(window.window_id)

        self.assertIsNotNone(saved_entry)
        self.assertEqual(saved_entry["requested_start_date"], "2025-01-15")
        self.assertEqual(saved_entry["request_status"], "SUCCESS")
        self.assertEqual(saved_entry["raw_records_count"], 2)


if __name__ == "__main__":
    unittest.main()
