"""
Phase F.10 — Real Multi-Feed Dataset Ingestion & Production Pipeline Orchestration Tests
"""

import pytest
from datetime import date
from data.pipeline.multi_feed_pipeline import MultiFeedDatasetPipeline
from data.ingestion.source_registry import SourceRegistry
from data.ingestion.ter_feed_adapter import TERFeedAdapter
from data.ingestion.riskometer_feed_adapter import RiskometerFeedAdapter
from data.ingestion.benchmark_feed_adapter import BenchmarkFeedAdapter
from data.ingestion.scheme_master_adapter import SchemeMasterFeedAdapter
from models.nav_data import DataQualityState

class TestPhaseF10MultiFeedPipeline:

    # 1. Source Registry Verification
    def test_01_source_registry_contains_f10_multi_feed_sources(self):
        registry = SourceRegistry()
        ter_src = registry.get_source("AMFI_TER_FEED")
        risk_src = registry.get_source("AMFI_RISKOMETER_FEED")
        bm_src = registry.get_source("AMFI_BENCHMARK_FEED")
        master_src = registry.get_source("AMFI_SCHEME_MASTER")

        assert ter_src is not None
        assert risk_src is not None
        assert bm_src is not None
        assert master_src is not None

        assert ter_src.authority_level.name == "AMFI"
        assert risk_src.authority_level.name == "AMFI"
        assert bm_src.authority_level.name == "AMFI"
        assert master_src.authority_level.name == "AMFI"

    # 2. Multi-feed merge end-to-end trace (NAV + TER + Riskometer + Benchmark + Scheme Master)
    def test_02_multi_feed_merge_end_to_end_trace(self):
        pipeline = MultiFeedDatasetPipeline()

        nav_items = [{
            "scheme_code": "119551",
            "scheme_name": "HDFC Small Cap Fund - Direct Plan - Growth",
            "nav": "142.50",
            "nav_date": "15-Jan-2024",
            "isin": "INF200K01131"
        }]

        ter_items = [{"scheme_code": "119551", "ter": "0.85", "effective_date": "2024-01-15"}]
        risk_items = [{"scheme_code": "119551", "riskometer": "VERY HIGH", "effective_date": "2024-01-15"}]
        bm_items = [{"scheme_code": "119551", "benchmark": "NIFTY SMALLCAP 250 TRI", "effective_date": "2024-01-15"}]
        master_items = [{
            "scheme_code": "119551",
            "category": "Equity",
            "subcategory": "Small Cap",
            "amc_name": "HDFC Mutual Fund"
        }]

        snapshot, report = pipeline.process_multi_feed_batch(
            nav_raw_items=nav_items,
            ter_raw_items=ter_items,
            riskometer_raw_items=risk_items,
            benchmark_raw_items=bm_items,
            scheme_master_raw_items=master_items,
            dataset_version="F10.0.0"
        )

        assert snapshot.total_schemes_count == 1
        rec = snapshot.records[0]

        assert rec.amfi_code == "119551"
        assert rec.canonical_scheme_id == "CAN_AMFI_119551"
        assert rec.ter_value == 0.85
        assert rec.riskometer_label == "VERY HIGH"
        assert rec.benchmark_name == "NIFTY SMALLCAP 250 TRI"
        assert rec.category_str == "EQUITY"
        assert rec.subcategory_str == "SMALL CAP"
        assert rec.quality_state_str == DataQualityState.VALID.value

        assert report["ter_populated_total"] == 1
        assert report["riskometer_populated_total"] == 1
        assert report["benchmark_populated_total"] == 1

    # 3. Canonical Identity Matching (CAN_AMFI_{amfi_code})
    def test_03_canonical_identity_matching_and_unmapped_metadata(self):
        pipeline = MultiFeedDatasetPipeline()

        nav_items = [{
            "scheme_code": "119551",
            "scheme_name": "HDFC Small Cap Fund - Direct Plan - Growth",
            "nav": "142.50",
            "nav_date": "15-Jan-2024"
        }]

        # Metadata contains 119551 + an unmapped scheme 999999
        ter_items = [
            {"scheme_code": "119551", "ter": "0.85"},
            {"scheme_code": "999999", "ter": "1.20"}
        ]

        snapshot, report = pipeline.process_multi_feed_batch(
            nav_raw_items=nav_items,
            ter_raw_items=ter_items
        )

        assert snapshot.total_schemes_count == 1
        assert snapshot.records[0].canonical_scheme_id == "CAN_AMFI_119551"
        assert snapshot.records[0].ter_value == 0.85
        assert report["unmapped_metadata_count"] == 1

    # 4. Missing metadata remains explicit None (No silent defaults)
    def test_04_missing_metadata_remains_explicit_none(self):
        pipeline = MultiFeedDatasetPipeline()

        nav_items = [{
            "scheme_code": "119551",
            "scheme_name": "HDFC Small Cap Fund - Direct Plan - Growth",
            "nav": "142.50",
            "nav_date": "15-Jan-2024"
        }]

        # Processing NAV without metadata feeds
        snapshot, report = pipeline.process_multi_feed_batch(nav_raw_items=nav_items)
        rec = snapshot.records[0]

        assert rec.ter_value is None  # No 0.0 or 0.75/1.75
        assert rec.riskometer_label is None  # No numeric score, no MEDIUM default
        assert rec.benchmark_name is None  # No arbitrary index substitution

    # 5. Provenance metadata attached to all merged records
    def test_05_provenance_metadata_attached(self):
        pipeline = MultiFeedDatasetPipeline()

        nav_items = [{"scheme_code": "119551", "scheme_name": "HDFC Small Cap - Direct", "nav": "100.0", "nav_date": "15-Jan-2024"}]
        ter_items = [{"scheme_code": "119551", "ter": "0.85"}]

        snapshot, _ = pipeline.process_multi_feed_batch(nav_raw_items=nav_items, ter_raw_items=ter_items)
        assert "AMFI_OFFICIAL" in snapshot.source_ids
        assert "AMFI_TER_FEED" in snapshot.source_ids

    # 6. Idempotency & Deterministic Repeated Ingestion
    def test_06_idempotent_repeated_ingestion(self):
        pipeline = MultiFeedDatasetPipeline()

        nav_items = [{"scheme_code": "119551", "scheme_name": "HDFC Small Cap - Direct - Growth", "nav": "100.0", "nav_date": "15-Jan-2024"}]
        ter_items = [{"scheme_code": "119551", "ter": "0.85"}]

        snap1, report1 = pipeline.process_multi_feed_batch(nav_raw_items=nav_items, ter_raw_items=ter_items, dataset_version="F10.0.0")
        snap2, report2 = pipeline.process_multi_feed_batch(nav_raw_items=nav_items, ter_raw_items=ter_items, dataset_version="F10.0.0")

        assert snap1.records[0].canonical_scheme_id == snap2.records[0].canonical_scheme_id == "CAN_AMFI_119551"
        assert snap1.records[0].ter_value == snap2.records[0].ter_value == 0.85
        assert snap1.records[0].quality_state_str == snap2.records[0].quality_state_str == DataQualityState.VALID.value

    # 7. Primary Quality State Reconciliation
    def test_07_quality_state_reconciliation(self):
        pipeline = MultiFeedDatasetPipeline()

        nav_items = [
            {"scheme_code": "119551", "scheme_name": "HDFC Small Cap - Direct - Growth", "nav": "100.0", "nav_date": "15-Jan-2024"}, # VALID
            {"scheme_code": "101234", "scheme_name": "Ambiguous Fund Name", "nav": "50.0", "nav_date": "15-Jan-2024"}, # QUARANTINED
            {"scheme_code": "100001", "scheme_name": "Invalid Fund", "nav": "0.0", "nav_date": "15-Jan-2024"} # INVALID
        ]

        snapshot, report = pipeline.process_multi_feed_batch(nav_raw_items=nav_items)
        assert snapshot.total_schemes_count == 3
        assert report["valid_records"] == 1
        assert report["quarantined_records"] == 1
        assert report["invalid_records"] == 1

        assert report["valid_records"] + report["quarantined_records"] + report["invalid_records"] == snapshot.total_schemes_count

    # 8. Representative Scheme Cases Validation (10 Schemes)
    def test_08_representative_scheme_cases_validation(self):
        pipeline = MultiFeedDatasetPipeline()

        nav_items = [
            {"scheme_code": "119551", "scheme_name": "HDFC Small Cap Fund - Direct Plan - Growth Option", "nav": "142.50", "nav_date": "15-Jan-2024"},
            {"scheme_code": "101234", "scheme_name": "SBI Long Term Equity Fund - Direct Plan - Growth Option - ELSS", "nav": "250.00", "nav_date": "15-Jan-2024"},
            {"scheme_code": "120586", "scheme_name": "ICICI Pru Bluechip Fund - Direct Plan - Growth Option", "nav": "85.20", "nav_date": "15-Jan-2024"},
            {"scheme_code": "112323", "scheme_name": "Axis Long Term Equity Fund - Direct Plan - Growth Option - ELSS", "nav": "75.40", "nav_date": "15-Jan-2024"},
            {"scheme_code": "118778", "scheme_name": "Nippon India Small Cap Fund - Direct Plan - Growth Option", "nav": "130.10", "nav_date": "15-Jan-2024"},
            {"scheme_code": "110452", "scheme_name": "Mirae Asset Large Cap Fund - Direct Plan - Growth Option", "nav": "95.60", "nav_date": "15-Jan-2024"},
            {"scheme_code": "122639", "scheme_name": "Parag Parikh Flexi Cap Fund - Direct Plan - Growth Option", "nav": "65.30", "nav_date": "15-Jan-2024"},
            {"scheme_code": "119062", "scheme_name": "UTI Nifty 50 Index Fund - Direct Plan - Growth Option", "nav": "160.80", "nav_date": "15-Jan-2024"},
            {"scheme_code": "105890", "scheme_name": "Kotak Emerging Equity Fund - Direct Plan - Growth Option", "nav": "110.40", "nav_date": "15-Jan-2024"},
            {"scheme_code": "100033", "scheme_name": "DSP Liquid Fund - Direct Plan - Growth Option", "nav": "3200.50", "nav_date": "15-Jan-2024"}
        ]

        master_items = [
            {"scheme_code": "119551", "ter": "0.85", "riskometer": "VERY HIGH", "benchmark": "NIFTY SMALLCAP 250 TRI", "category": "Equity", "subcategory": "Small Cap"},
            {"scheme_code": "101234", "ter": "0.95", "riskometer": "VERY HIGH", "benchmark": "NIFTY 500 TRI", "category": "Equity", "subcategory": "ELSS"},
            {"scheme_code": "120586", "ter": "0.90", "riskometer": "VERY HIGH", "benchmark": "NIFTY 100 TRI", "category": "Equity", "subcategory": "Large Cap"},
            {"scheme_code": "112323", "ter": "0.88", "riskometer": "VERY HIGH", "benchmark": "NIFTY 500 TRI", "category": "Equity", "subcategory": "ELSS"},
            {"scheme_code": "118778", "ter": "0.75", "riskometer": "VERY HIGH", "benchmark": "NIFTY SMALLCAP 250 TRI", "category": "Equity", "subcategory": "Small Cap"},
            {"scheme_code": "110452", "ter": "0.55", "riskometer": "VERY HIGH", "benchmark": "NIFTY 100 TRI", "category": "Equity", "subcategory": "Large Cap"},
            {"scheme_code": "122639", "ter": "0.62", "riskometer": "VERY HIGH", "benchmark": "NIFTY 500 TRI", "category": "Equity", "subcategory": "Flexi Cap"},
            {"scheme_code": "119062", "ter": "0.10", "riskometer": "VERY HIGH", "benchmark": "NIFTY 50 TRI", "category": "Equity", "subcategory": "Large Cap"},
            {"scheme_code": "105890", "ter": "0.48", "riskometer": "VERY HIGH", "benchmark": "NIFTY MIDCAP 150 TRI", "category": "Equity", "subcategory": "Mid Cap"},
            {"scheme_code": "100033", "ter": "0.15", "riskometer": "LOW TO MODERATE", "benchmark": "NIFTY LIQUID INDEX A-I", "category": "Debt", "subcategory": "Liquid"}
        ]

        snapshot, report = pipeline.process_multi_feed_batch(nav_raw_items=nav_items, scheme_master_raw_items=master_items)

        assert snapshot.total_schemes_count == 10
        assert report["valid_records"] == 10
        assert report["ter_populated_total"] == 10
        assert report["riskometer_populated_total"] == 10
        assert report["benchmark_populated_total"] == 10

        elss_rec = [r for r in snapshot.records if r.amfi_code == "101234"][0]
        assert elss_rec.lock_in_days == 1095  # ELSS statutory lock-in
