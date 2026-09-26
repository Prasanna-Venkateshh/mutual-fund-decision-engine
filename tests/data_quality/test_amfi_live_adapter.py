"""
Unit & Integration Tests for Authoritative Live AMFI Adapter & Identifier Preservation (Phase F.9.2).
"""

import unittest
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

from data.ingestion.amfi_ingestor import AMFIIngestor
from data.ingestion.amfi_live_adapter import AMFILiveAdapter
from data.pipeline.production_dataset_pipeline import ProductionDatasetPipeline
from models.nav_data import DataQualityState, RawNAVRecord


class TestAMFILiveAdapter(unittest.TestCase):
    """Test suite for live AMFI source integration and identifier preservation."""

    SAMPLE_8_COLUMN_AMFI_TEXT = (
        "Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Plan;Option;Net Asset Value;Date\n"
        "Axis Mutual Fund\n"
        "Open Ended Schemes( Equity Scheme - Large Cap Fund )\n"
        "135762;INF846K01WO1;-;Axis Bluechip Fund;Direct Plan;Growth Option;45.1234;11-Sep-2026\n"
        "135763;INF846K01WP8;-;Axis Bluechip Fund;Regular Plan;Growth Option;41.5678;11-Sep-2026\n"
        "135764;INF846K01WQ6;INF846K01WR4;Axis Bluechip Fund;Direct Plan;IDCW Option;18.9012;11-Sep-2026\n"
    )

    SAMPLE_TEXT_WITHOUT_CODE = (
        ";;;Uncoded Scheme Without Code;Direct Plan;Growth Option;10.5000;11-Sep-2026\n"
    )

    def setUp(self):
        self.ingestor = AMFIIngestor()
        self.pipeline = ProductionDatasetPipeline()
        self.adapter = AMFILiveAdapter(pipeline=self.pipeline, ingestor=self.ingestor)

    def test_parse_raw_amfi_text_8_column_preserves_identifiers(self):
        """Verify parsing 8-column AMFI text preserves real scheme codes, ISINs, plans, and options."""
        records = self.ingestor.parse_raw_amfi_text(self.SAMPLE_8_COLUMN_AMFI_TEXT)
        self.assertEqual(len(records), 3)

        rec1 = records[0]
        self.assertEqual(rec1.raw_scheme_code, "135762")
        self.assertIn("Axis Bluechip Fund", rec1.raw_scheme_name)
        self.assertEqual(rec1.raw_nav_value, "45.1234")
        self.assertEqual(rec1.raw_date, "11-Sep-2026")

        meta1 = rec1.additional_metadata
        self.assertEqual(meta1["isin_growth"], "INF846K01WO1")
        self.assertEqual(meta1["plan"], "Direct Plan")
        self.assertEqual(meta1["option"], "Growth Option")
        self.assertEqual(meta1["amc_name"], "Axis Mutual Fund")

    def test_no_synthetic_identifier_generation_when_code_missing(self):
        """Verify that missing scheme code is NOT replaced with a synthetic code like SYNTH_ or 100000+idx."""
        records = self.ingestor.parse_raw_amfi_text(self.SAMPLE_TEXT_WITHOUT_CODE)
        self.assertEqual(len(records), 1)
        rec = records[0]
        self.assertEqual(rec.raw_scheme_code, "")
        self.assertFalse(rec.raw_scheme_code.startswith("SYNTH_"))
        self.assertFalse(rec.raw_scheme_code.isdigit())

    def test_csv_parser_no_synthetic_code_fallback(self):
        """Verify local amfi_data.csv parser does not synthesize scheme codes when missing."""
        csv_payload = "scheme_name,nav,date\nTest Debt Fund,12.34,2026-05-04\n"
        records = self.ingestor.parse_raw_csv_snapshot(csv_payload)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].raw_scheme_code, "")

    def test_live_adapter_successful_pipeline_execution(self):
        """Verify AMFILiveAdapter executes 5-layer pipeline cleanly on 8-column text."""
        with patch.object(self.ingestor, "fetch_live_amfi_nav_all") as mock_fetch:
            now_utc = datetime.now(timezone.utc)
            mock_fetch.return_value = (self.SAMPLE_8_COLUMN_AMFI_TEXT, now_utc, 200, "dummy_hash_123")

            snapshot, meta = self.adapter.process_live_amfi_feed(dataset_version="F9.2.0_TEST")

            self.assertIsNotNone(snapshot)
            self.assertTrue(meta["is_success"])
            self.assertEqual(meta["http_status_code"], 200)
            self.assertEqual(len(snapshot.records), 3)

            # Check identifier preservation in Layer D records
            rec1 = snapshot.records[0]
            self.assertEqual(rec1.amfi_code, "135762")
            self.assertEqual(rec1.isin, "INF846K01WO1")
            self.assertNotEqual(rec1.amfi_code, rec1.canonical_scheme_id)
            self.assertEqual(rec1.canonical_scheme_id, "CAN_AMFI_135762")

    def test_direct_regular_plan_separation(self):
        """Verify Direct and Regular plans remain distinct canonical entities."""
        with patch.object(self.ingestor, "fetch_live_amfi_nav_all") as mock_fetch:
            now_utc = datetime.now(timezone.utc)
            mock_fetch.return_value = (self.SAMPLE_8_COLUMN_AMFI_TEXT, now_utc, 200, "dummy_hash")

            snapshot, _ = self.adapter.process_live_amfi_feed(dataset_version="F9.2.0_TEST")

            rec_dir = snapshot.records[0]  # Direct Plan
            rec_reg = snapshot.records[1]  # Regular Plan

            self.assertEqual(rec_dir.plan_type_str, "DIRECT")
            self.assertEqual(rec_reg.plan_type_str, "REGULAR")
            self.assertNotEqual(rec_dir.canonical_scheme_id, rec_reg.canonical_scheme_id)

    def test_growth_idcw_option_separation(self):
        """Verify Growth and IDCW options remain distinct canonical entities."""
        with patch.object(self.ingestor, "fetch_live_amfi_nav_all") as mock_fetch:
            now_utc = datetime.now(timezone.utc)
            mock_fetch.return_value = (self.SAMPLE_8_COLUMN_AMFI_TEXT, now_utc, 200, "dummy_hash")

            snapshot, _ = self.adapter.process_live_amfi_feed(dataset_version="F9.2.0_TEST")

            rec_growth = snapshot.records[0]  # Growth Option
            rec_idcw = snapshot.records[2]    # IDCW Option

            self.assertEqual(rec_growth.option_type_str, "GROWTH")
            self.assertIn("IDCW", rec_idcw.option_type_str)
            self.assertNotEqual(rec_growth.canonical_scheme_id, rec_idcw.canonical_scheme_id)

    def test_missing_identifier_quarantine(self):
        """Verify records with missing scheme codes are quarantined rather than given fake codes."""
        raw_items = [{
            "scheme_code": "",
            "scheme_name": "",
            "nav": "10.5",
            "nav_date": "11-Sep-2026"
        }]

        snapshot = self.pipeline.process_raw_batch(
            source_id="AMFI_OFFICIAL",
            raw_items=raw_items,
            dataset_version="F9.2.0_TEST"
        )

        rec = snapshot.records[0]
        self.assertTrue(rec.is_quarantined)
        self.assertTrue(rec.canonical_scheme_id.startswith("CAN_"))

    def test_live_adapter_http_failure_handling(self):
        """Verify adapter handles HTTP 500 or network failure gracefully without creating a dataset snapshot."""
        with patch.object(self.ingestor, "fetch_live_amfi_nav_all") as mock_fetch:
            now_utc = datetime.now(timezone.utc)
            mock_fetch.return_value = ("", now_utc, 500, "")

            snapshot, meta = self.adapter.process_live_amfi_feed(dataset_version="F9.2.0_TEST")

            self.assertIsNone(snapshot)
            self.assertFalse(meta["is_success"])
            self.assertEqual(meta["http_status_code"], 500)
            self.assertIn("HTTP retrieval failed", meta["error"])

    def test_repeat_ingestion_idempotency(self):
        """Verify repeated processing of the same payload produces identical canonical mappings."""
        with patch.object(self.ingestor, "fetch_live_amfi_nav_all") as mock_fetch:
            now_utc = datetime.now(timezone.utc)
            mock_fetch.return_value = (self.SAMPLE_8_COLUMN_AMFI_TEXT, now_utc, 200, "hash_xyz")

            snap1, _ = self.adapter.process_live_amfi_feed(dataset_version="F9.2.0_RUN1")
            snap2, _ = self.adapter.process_live_amfi_feed(dataset_version="F9.2.0_RUN2")

            canon1 = [r.canonical_scheme_id for r in snap1.records]
            canon2 = [r.canonical_scheme_id for r in snap2.records]

            self.assertEqual(canon1, canon2)

    def test_missing_metadata_never_defaults_to_favorable_values(self):
        """Verify TER, Riskometer, and Benchmark remain None when missing in source records."""
        raw_items = [{
            "scheme_code": "135762",
            "scheme_name": "Axis Bluechip Fund - Direct Plan - Growth",
            "nav": "45.12",
            "nav_date": "11-Sep-2026",
            "ter": None,
            "riskometer": None,
            "benchmark": None
        }]

        snapshot = self.pipeline.process_raw_batch(
            source_id="AMFI_OFFICIAL",
            raw_items=raw_items,
            dataset_version="F9.2.0_TEST"
        )

        rec = snapshot.records[0]
        self.assertIsNone(rec.ter_value)
        self.assertIsNone(rec.riskometer_label)
        self.assertIsNone(rec.benchmark_name)

    def test_quarantine_reconciliation_invariants(self):
        """Verify primary quality state counts in IngestionRunRecord reconcile 100% with total records."""
        with patch.object(self.ingestor, "fetch_live_amfi_nav_all") as mock_fetch:
            now_utc = datetime.now(timezone.utc)
            text_with_invalid = self.SAMPLE_8_COLUMN_AMFI_TEXT + "135765;INF846K01WS2;-;Axis Invalid Fund;Direct;Growth;0.0;11-Sep-2026\n"
            mock_fetch.return_value = (text_with_invalid, now_utc, 200, "hash_abc")

            snapshot, _ = self.adapter.process_live_amfi_feed(dataset_version="F9.2.2_RECON")
            runs = self.pipeline.run_manager.list_completed_runs()
            self.assertTrue(len(runs) > 0)
            r = runs[-1]

            run_sum = r.valid_record_count + r.partial_record_count + r.invalid_record_count + r.quarantined_record_count + r.conflict_record_count
            self.assertEqual(run_sum, r.total_records_processed)
            self.assertEqual(r.total_records_processed, 4)
            self.assertEqual(r.valid_record_count, 3)
            self.assertEqual(r.invalid_record_count, 1)
            self.assertEqual(r.quarantined_record_count, 0)

    def test_canonical_id_deterministic_derivation(self):
        """Verify canonical IDs are deterministically derived from AMFI source scheme codes."""
        raw_items = [{
            "scheme_code": "120503",
            "scheme_name": "SBI Bluechip Fund - Direct Plan - Growth",
            "nav": "75.40",
            "nav_date": "11-Sep-2026"
        }]

        snapshot = self.pipeline.process_raw_batch(
            source_id="AMFI_OFFICIAL",
            raw_items=raw_items,
            dataset_version="F9.2.2_TEST"
        )

        rec = snapshot.records[0]
        self.assertEqual(rec.amfi_code, "120503")
        self.assertEqual(rec.canonical_scheme_id, "CAN_AMFI_120503")
        self.assertNotIn("SYNTH", rec.canonical_scheme_id)

    def test_amfi_code_identifies_scheme_plan_option(self):
        """Verify AMFI scheme codes uniquely identify distinct scheme+plan+option variants."""
        records = self.ingestor.parse_raw_amfi_text(self.SAMPLE_8_COLUMN_AMFI_TEXT)
        codes = [r.raw_scheme_code for r in records]
        self.assertEqual(len(codes), 3)
        self.assertEqual(len(set(codes)), 3)
        self.assertEqual(codes, ["135762", "135763", "135764"])

    def test_invalid_record_carrying_quarantine_diagnostic_flag(self):
        """Verify INVALID records with non-positive NAV retain INVALID primary state while carrying is_quarantined=True."""
        raw_items = [{
            "scheme_code": "135765",
            "scheme_name": "Axis Bluechip Fund - Direct Plan - Growth",
            "nav": "0.0",
            "nav_date": "11-Sep-2026"
        }]

        snapshot = self.pipeline.process_raw_batch(
            source_id="AMFI_OFFICIAL",
            raw_items=raw_items,
            dataset_version="F9.2.3_TEST"
        )

        rec = snapshot.records[0]
        self.assertEqual(rec.quality_state_str, DataQualityState.INVALID.value)
        self.assertTrue(rec.is_quarantined)

    def test_primary_authoritative_identity_vs_secondary_consistency_check(self):
        """Verify AMFI code supplies primary identity while text parsing acts as secondary consistency validation."""
        raw_items = [{
            "scheme_code": "119552",
            "scheme_name": "Aditya Birla Sun Life Banking Fund - Monthly IDCW",
            "nav": "15.40",
            "nav_date": "11-Sep-2026"
        }]

        snapshot = self.pipeline.process_raw_batch(
            source_id="AMFI_OFFICIAL",
            raw_items=raw_items,
            dataset_version="F9.2.4_TEST"
        )

        rec = snapshot.records[0]
        # Primary identity preserved
        self.assertEqual(rec.amfi_code, "119552")
        # Quarantined because secondary textual plan/option consistency check failed
        self.assertEqual(rec.quality_state_str, DataQualityState.QUARANTINED.value)
        self.assertTrue(rec.is_quarantined)

    def test_quarantine_retains_authoritative_amfi_code(self):
        """Verify quarantined record preserves raw AMFI code and uses deterministic CAN_AMFI_ canonical ID."""
        raw_items = [{
            "scheme_code": "123691",
            "scheme_name": "Kotak Banking Fund - NonStandard Option Text",
            "nav": "22.10",
            "nav_date": "11-Sep-2026"
        }]

        snapshot = self.pipeline.process_raw_batch(
            source_id="AMFI_OFFICIAL",
            raw_items=raw_items,
            dataset_version="F9.2.4_TEST"
        )

        rec = snapshot.records[0]
        self.assertEqual(rec.amfi_code, "123691")
        self.assertEqual(rec.canonical_scheme_id, "CAN_AMFI_123691")
        self.assertNotIn("SYNTH", rec.canonical_scheme_id)

    def test_canonical_identity_stability_across_revalidation(self):
        """Verify canonical entity ID remains stable when a QUARANTINED record becomes VALID."""
        raw_quarantined = [{
            "scheme_code": "123691",
            "scheme_name": "Kotak Banking Fund - NonStandard Option Text",
            "nav": "22.10",
            "nav_date": "11-Sep-2026"
        }]
        raw_valid = [{
            "scheme_code": "123691",
            "scheme_name": "Kotak Banking Fund - Direct Plan - Growth",
            "nav": "22.10",
            "nav_date": "12-Sep-2026"
        }]

        snap1 = self.pipeline.process_raw_batch(source_id="AMFI_OFFICIAL", raw_items=raw_quarantined, dataset_version="F9.2.5_RUN1")
        rec1 = snap1.records[0]
        self.assertEqual(rec1.quality_state_str, DataQualityState.QUARANTINED.value)
        self.assertEqual(rec1.canonical_scheme_id, "CAN_AMFI_123691")

        snap2 = self.pipeline.process_raw_batch(source_id="AMFI_OFFICIAL", raw_items=raw_valid, dataset_version="F9.2.5_RUN2")
        rec2 = snap2.records[0]
        self.assertEqual(rec2.quality_state_str, DataQualityState.VALID.value)
        self.assertEqual(rec2.canonical_scheme_id, "CAN_AMFI_123691")

        # Invariant: Canonical entity ID is 100% stable across quality state transition
        self.assertEqual(rec1.canonical_scheme_id, rec2.canonical_scheme_id)


if __name__ == "__main__":
    unittest.main()
