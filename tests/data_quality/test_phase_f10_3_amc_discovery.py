"""
Phase F.10.3 — Official AMC Metadata Source Discovery & Coverage Assessment Test Suite

Verifies:
1. AMC Universe Discovery (dynamic count from live AMFI NAVAll.txt dataset).
2. Source Registry extension (`AMC_DIRECT_DISCLOSURES` and `UNUNIFORM_FRAGMENTED_AMC`).
3. Situation C metadata unpopulated enforcement (`ter=None`, `riskometer=None`, `benchmark=None`).
4. Zero synthetic metadata default substitution safety.
5. Canonical Identity Stability preservation across schemes.
"""

from pathlib import Path
import pytest

from models.source import ValidationStatus
from data.ingestion.source_registry import SourceRegistry
from data.ingestion.amfi_live_adapter import AMFILiveAdapter
from data.pipeline.multi_feed_pipeline import MultiFeedDatasetPipeline


class TestPhaseF103AMCDiscovery:

    def test_01_amc_universe_discovery_count(self):
        """Verify dynamic AMC universe discovery from live AMFI NAVAll.txt feed."""
        adapter = AMFILiveAdapter()
        meta = adapter.fetch_live_amfi_raw_evidence()
        assert meta["is_success"] is True, "Fetching live NAV feed must succeed"
        
        parsed_records = adapter.ingestor.parse_raw_amfi_text(meta["raw_payload_text"], meta["retrieval_timestamp_utc"])
        distinct_amcs = set()
        for rec in parsed_records:
            amc = (rec.additional_metadata or {}).get("amc_name")
            if amc:
                distinct_amcs.add(amc.strip())
        
        # Must discover at least 40 distinct AMCs in the live universe (actual live universe = 53)
        assert len(distinct_amcs) >= 40, f"Expected >=40 distinct AMCs, found {len(distinct_amcs)}"

    def test_02_source_registry_amc_entry_validation(self):
        """Verify AMC_DIRECT_DISCLOSURES source record in source registry."""
        sources_path = Path("config/sources/sources.json")
        assert sources_path.exists(), "config/sources/sources.json must exist"
        
        registry = SourceRegistry(config_path=str(sources_path))
        amc_source = registry.get_source("AMC_DIRECT_DISCLOSURES")
        
        assert amc_source is not None, "AMC_DIRECT_DISCLOSURES source entry must be registered"
        assert amc_source.validation_status == ValidationStatus.UNUNIFORM_FRAGMENTED_AMC

    def test_03_situation_c_metadata_unpopulated_enforcement(self):
        """Verify that live production snapshot maintains explicit None for unpopulated metadata fields under Situation C."""
        pipeline = MultiFeedDatasetPipeline()
        adapter = AMFILiveAdapter()
        meta = adapter.fetch_live_amfi_raw_evidence()
        records = adapter.ingestor.parse_raw_amfi_text(meta["raw_payload_text"], meta["retrieval_timestamp_utc"])

        raw_items = []
        for r in records[:50]:
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
        assert snapshot.total_schemes_count == 50
        for rec in snapshot.records:
            assert rec.ter_value is None, f"Scheme {rec.scheme_code} TER must be None"
            assert rec.riskometer_label is None, f"Scheme {rec.scheme_code} Riskometer must be None"
            assert rec.benchmark_name is None, f"Scheme {rec.scheme_code} Benchmark must be None"

    def test_04_no_synthetic_metadata_defaults(self):
        """Verify zero synthetic fallback values are used for missing metadata."""
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

    def test_05_canonical_identity_stability_preserved(self):
        """Verify canonical scheme ID stability invariant CAN_AMFI_{code}."""
        pipeline = MultiFeedDatasetPipeline()
        nav_items = [{
            "scheme_code": "119551",
            "scheme_name": "Aditya Birla Sun Life Banking & PSU Debt Fund - Direct - IDCW",
            "nav": "107.0790",
            "nav_date": "11-Sep-2026"
        }]

        snapshot, _ = pipeline.process_multi_feed_batch(nav_raw_items=nav_items)
        rec = snapshot.records[0]
        assert rec.canonical_scheme_id == "CAN_AMFI_119551"
