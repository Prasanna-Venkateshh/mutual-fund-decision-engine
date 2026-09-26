"""
AMFI Authoritative Live Source Adapter (Phase F.9.2).

Performs live HTTP retrieval from official AMFI endpoints (NAVAll.txt / official APIs),
preserves raw unparsed Layer A evidence, retains actual source identifiers (AMFI Scheme Code & ISIN),
and passes normalized records through the 5-layer production dataset pipeline.
"""

from datetime import datetime, timezone, date
import hashlib
from typing import List, Dict, Any, Optional, Tuple

from data.ingestion.amfi_ingestor import AMFIIngestor
from data.ingestion.source_registry import SourceRegistry
from data.pipeline.production_dataset_pipeline import ProductionDatasetPipeline
from models.production_dataset import VersionedDatasetSnapshot, RawSourceEvidence


class AMFILiveAdapter:
    """
    Authoritative Live AMFI Data Source Adapter.
    Executes live HTTP requests to AMFI endpoints, preserves raw response provenance,
    and coordinates 5-layer ingestion without synthetic identifier generation.
    """

    DEFAULT_AMFI_NAV_URL = "https://www.amfiindia.com/spages/NAVAll.txt"

    def __init__(
        self,
        source_registry: Optional[SourceRegistry] = None,
        pipeline: Optional[ProductionDatasetPipeline] = None,
        ingestor: Optional[AMFIIngestor] = None
    ):
        self.registry = source_registry or SourceRegistry()
        self.pipeline = pipeline or ProductionDatasetPipeline(source_registry=self.registry)
        self.ingestor = ingestor or AMFIIngestor(registry=self.registry)

    def fetch_live_amfi_raw_evidence(
        self,
        endpoint_url: str = DEFAULT_AMFI_NAV_URL,
        timeout: int = 15
    ) -> Dict[str, Any]:
        """
        Executes an actual HTTP GET request to official AMFI endpoint.
        Returns retrieval metadata dict containing raw text, HTTP status, timestamp, and SHA256 hash.
        """
        raw_text, ts, status_code, content_hash = self.ingestor.fetch_live_amfi_nav_all(
            url=endpoint_url,
            timeout=timeout
        )

        return {
            "source_id": "AMFI_OFFICIAL",
            "endpoint_url": endpoint_url,
            "retrieval_timestamp_utc": ts,
            "http_status_code": status_code,
            "raw_payload_text": raw_text,
            "raw_payload_bytes_len": len(raw_text.encode("utf-8")),
            "content_sha256": content_hash,
            "is_success": (status_code == 200 and len(raw_text) > 0)
        }

    def process_live_amfi_feed(
        self,
        endpoint_url: str = DEFAULT_AMFI_NAV_URL,
        dataset_version: str = "F9.2.0",
        assessment_date: Optional[date] = None,
        timeout: int = 15
    ) -> Tuple[Optional[VersionedDatasetSnapshot], Dict[str, Any]]:
        """
        Retrieves live AMFI NAV feed and processes all records through the 5-layer pipeline.
        
        Returns:
            (snapshot, retrieval_metadata)
            If live HTTP retrieval fails or returns non-200, snapshot is None and status is recorded.
        """
        retrieval_meta = self.fetch_live_amfi_raw_evidence(endpoint_url=endpoint_url, timeout=timeout)

        if not retrieval_meta["is_success"]:
            retrieval_meta["error"] = f"HTTP retrieval failed with status {retrieval_meta['http_status_code']}"
            return None, retrieval_meta

        raw_records = self.ingestor.parse_raw_amfi_text(
            text_content=retrieval_meta["raw_payload_text"],
            retrieval_timestamp=retrieval_meta["retrieval_timestamp_utc"]
        )

        retrieval_meta["records_parsed_count"] = len(raw_records)

        # Convert RawNAVRecord list to pipeline-compatible raw_items
        raw_items: List[Dict[str, Any]] = []
        for r in raw_records:
            meta = r.additional_metadata or {}
            item = {
                "scheme_code": r.raw_scheme_code,
                "scheme_name": r.raw_scheme_name,
                "nav": r.raw_nav_value,
                "nav_date": r.raw_date,
                "isin": meta.get("isin_growth") or meta.get("isin_reinvest") or "",
                "isin_growth": meta.get("isin_growth") or "",
                "isin_reinvest": meta.get("isin_reinvest") or "",
                "plan": meta.get("plan") or "",
                "option": meta.get("option") or "",
                "amc_name": meta.get("amc_name") or "",
                "category": meta.get("category_header") or "",
                "source_url": endpoint_url,
                "raw_line_number": r.raw_line_number,
                "raw_line": meta.get("raw_line") or ""
            }
            raw_items.append(item)

        # Execute 5-layer pipeline
        snapshot = self.pipeline.process_raw_batch(
            source_id="AMFI_OFFICIAL",
            raw_items=raw_items,
            dataset_version=dataset_version,
            assessment_date=assessment_date,
            source_endpoint_url=endpoint_url
        )

        return snapshot, retrieval_meta
