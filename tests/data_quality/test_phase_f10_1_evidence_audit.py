"""
Phase F.10.1 — Live Multi-Feed Source & Production Snapshot Evidence Audit Tests
"""

import pytest
from datetime import date
from data.ingestion.amfi_live_adapter import AMFILiveAdapter
from data.pipeline.multi_feed_pipeline import MultiFeedDatasetPipeline
from data.ingestion.source_registry import SourceRegistry
from models.nav_data import DataQualityState

class TestPhaseF101EvidenceAudit:

    # 1. Live AMFI NAV Source Retrieval & Evidence Audit
    def test_01_live_amfi_nav_source_retrieval(self):
        adapter = AMFILiveAdapter()
        meta = adapter.fetch_live_amfi_raw_evidence()

        assert meta["is_success"] is True
        assert meta["http_status_code"] == 200
        assert meta["raw_payload_bytes_len"] > 1000000
        assert len(meta["content_sha256"]) == 64

    # 2. Live Multi-Feed Production Snapshot Population Audit
    def test_02_live_multi_feed_snapshot_population_counts(self):
        adapter = AMFILiveAdapter()
        meta = adapter.fetch_live_amfi_raw_evidence()
        records = adapter.ingestor.parse_raw_amfi_text(meta["raw_payload_text"], meta["retrieval_timestamp_utc"])

        raw_items = []
        for r in records:
            m = r.additional_metadata or {}
            raw_items.append({
                "scheme_code": r.raw_scheme_code,
                "scheme_name": r.raw_scheme_name,
                "nav": r.raw_nav_value,
                "nav_date": r.raw_date,
                "isin": m.get("isin_growth") or m.get("isin_reinvest") or "",
                "plan": m.get("plan") or "",
                "option": m.get("option") or "",
                "amc_name": m.get("amc_name") or "",
                "category": m.get("category_header") or "",
                "source_url": adapter.DEFAULT_AMFI_NAV_URL
            })

        pipeline = MultiFeedDatasetPipeline()
        snapshot, report = pipeline.process_multi_feed_batch(
            nav_raw_items=raw_items,
            dataset_version="F10.1.0"
        )

        # Verify live snapshot contains expected scheme population (Live feed volume > 14,000 schemes)
        assert snapshot.total_schemes_count > 14000
        assert report["valid_records"] > 7500
        assert report["quarantined_records"] > 5500

        # Forensic proof: Unpopulated metadata feeds in live NAVAll snapshot
        assert report["ter_populated_total"] == 0
        assert report["riskometer_populated_total"] == 0
        assert report["benchmark_populated_total"] == 0

    # 3. Real AMFI Scheme Code Verification (No Synthetic Fixture Overclaim)
    def test_03_real_amfi_scheme_code_verification(self):
        adapter = AMFILiveAdapter()
        meta = adapter.fetch_live_amfi_raw_evidence()
        records = adapter.ingestor.parse_raw_amfi_text(meta["raw_payload_text"], meta["retrieval_timestamp_utc"])

        live_codes = {r.raw_scheme_code: r.raw_scheme_name for r in records}

        # Real AMFI codes present in NAVAll.txt
        assert "119551" in live_codes
        assert "135762" in live_codes
        assert "100033" in live_codes
        assert "100034" in live_codes

        # Verified scheme name mapping
        assert "Aditya Birla Sun Life Large & Mid Cap Fund" in live_codes["100033"]
        assert "Axis Children's Fund" in live_codes["135762"]

        # Synthetic code 999999 is NOT in live NAVAll.txt
        assert "999999" not in live_codes

    # 4. Explicit None for Missing Metadata
    def test_04_missing_metadata_remains_explicit_none(self):
        pipeline = MultiFeedDatasetPipeline()
        nav_items = [{
            "scheme_code": "119551",
            "scheme_name": "HDFC Small Cap Fund - Direct Plan - Growth",
            "nav": "142.50",
            "nav_date": "15-Jan-2024"
        }]

        snapshot, _ = pipeline.process_multi_feed_batch(nav_raw_items=nav_items)
        rec = snapshot.records[0]

        assert rec.ter_value is None
        assert rec.riskometer_label is None
        assert rec.benchmark_name is None

    # 5. ELSS Statutory Lock-in Derivation
    def test_05_elss_statutory_lock_in_derivation(self):
        pipeline = MultiFeedDatasetPipeline()
        nav_items = [{
            "scheme_code": "101234",
            "scheme_name": "SBI Long Term Equity Fund - Direct Plan - Growth Option - ELSS",
            "nav": "250.00",
            "nav_date": "15-Jan-2024",
            "category": "Equity",
            "subcategory": "ELSS"
        }]

        snapshot, _ = pipeline.process_multi_feed_batch(nav_raw_items=nav_items)
        rec = snapshot.records[0]

        assert rec.lock_in_days == 1095

    # 6. Quality State Accounting Formula Verification
    def test_06_quality_state_accounting(self):
        pipeline = MultiFeedDatasetPipeline()
        nav_items = [
            {"scheme_code": "119551", "scheme_name": "HDFC Small Cap - Direct - Growth", "nav": "100.0", "nav_date": "15-Jan-2024"},
            {"scheme_code": "101234", "scheme_name": "Ambiguous Fund Name", "nav": "50.0", "nav_date": "15-Jan-2024"},
            {"scheme_code": "100001", "scheme_name": "Invalid Fund", "nav": "0.0", "nav_date": "15-Jan-2024"}
        ]

        snapshot, report = pipeline.process_multi_feed_batch(nav_raw_items=nav_items)
        assert report["valid_records"] + report["quarantined_records"] + report["invalid_records"] == snapshot.total_schemes_count
