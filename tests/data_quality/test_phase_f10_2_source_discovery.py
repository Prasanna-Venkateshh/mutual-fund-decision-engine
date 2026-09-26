"""
Phase F.10.2 — Authoritative TER, Riskometer & Benchmark Source Discovery and Validation Tests
"""

import pytest
from data.ingestion.source_registry import SourceRegistry
from data.ingestion.amfi_live_adapter import AMFILiveAdapter
from data.pipeline.multi_feed_pipeline import MultiFeedDatasetPipeline

class TestPhaseF102SourceDiscovery:

    # 1. Source Registry Status & Metadata Entry Audit
    def test_01_source_registry_status_and_metadata_audit(self):
        registry = SourceRegistry()
        nav_src = registry.get_source("AMFI_OFFICIAL")
        ter_src = registry.get_source("AMFI_TER_FEED")
        risk_src = registry.get_source("AMFI_RISKOMETER_FEED")
        bm_src = registry.get_source("AMFI_BENCHMARK_FEED")
        master_src = registry.get_source("AMFI_SCHEME_MASTER")

        assert nav_src is not None
        assert nav_src.validation_status.name == "VALIDATED"

        assert ter_src is not None
        assert ter_src.validation_status.name == "UNAVAILABLE_HTTP_404"

        assert risk_src is not None
        assert risk_src.validation_status.name == "UNAVAILABLE_HTTP_404"

        assert bm_src is not None
        assert bm_src.validation_status.name == "UNAVAILABLE_HTTP_404"

        assert master_src is not None
        assert master_src.validation_status.name == "UNAVAILABLE_HTTP_404"

    # 2. Live NAV Feed Retrieval Verification
    def test_02_live_nav_feed_retrieval(self):
        adapter = AMFILiveAdapter()
        meta = adapter.fetch_live_amfi_raw_evidence()

        assert meta["is_success"] is True
        assert meta["http_status_code"] == 200
        assert meta["raw_payload_bytes_len"] > 1000000

    # 3. Third-Party Secondary Feed Classification
    def test_03_third_party_secondary_feed_classification(self):
        registry = SourceRegistry()
        mfapi_src = registry.get_source("MFAPI_PROTOTYPE")

        assert mfapi_src is not None
        assert mfapi_src.authority_level.name == "UNVALIDATED_THIRD_PARTY"
        assert mfapi_src.validation_status.name == "PROVISIONAL"

    # 4. Live Production Snapshot Metadata Unpopulated Audit
    def test_04_live_production_snapshot_metadata_unpopulated(self):
        pipeline = MultiFeedDatasetPipeline()
        adapter = AMFILiveAdapter()
        meta = adapter.fetch_live_amfi_raw_evidence()
        records = adapter.ingestor.parse_raw_amfi_text(meta["raw_payload_text"], meta["retrieval_timestamp_utc"])

        raw_items = []
        for r in records[:100]:  # Sample top 100 live records
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

        snapshot, report = pipeline.process_multi_feed_batch(nav_raw_items=raw_items)

        assert snapshot.total_schemes_count == 100
        assert report["ter_populated_total"] == 0
        assert report["riskometer_populated_total"] == 0
        assert report["benchmark_populated_total"] == 0

    # 5. Missing Metadata Fields Remain Explicit None (No Synthetic Substitution)
    def test_05_missing_metadata_fields_remain_explicit_none(self):
        pipeline = MultiFeedDatasetPipeline()
        nav_items = [{
            "scheme_code": "119551",
            "scheme_name": "Aditya Birla Sun Life Banking & PSU Debt Fund - Direct - IDCW",
            "nav": "107.0790",
            "nav_date": "11-Sep-2026"
        }]

        snapshot, _ = pipeline.process_multi_feed_batch(nav_raw_items=nav_items)
        rec = snapshot.records[0]

        assert rec.ter_value is None
        assert rec.riskometer_label is None
        assert rec.benchmark_name is None

    # 6. Real Scheme Verification from Live NAV Feed
    def test_06_real_scheme_verification_from_live_nav_feed(self):
        adapter = AMFILiveAdapter()
        meta = adapter.fetch_live_amfi_raw_evidence()
        records = adapter.ingestor.parse_raw_amfi_text(meta["raw_payload_text"], meta["retrieval_timestamp_utc"])

        codes = {r.raw_scheme_code: r.raw_scheme_name for r in records}
        assert "119551" in codes
        assert "135762" in codes
        assert "100033" in codes
