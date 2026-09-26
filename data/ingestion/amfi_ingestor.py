"""
AMFI NAV Data Ingestor Adapter (Phase F.9.2).

Ingests raw NAV observations from official AMFI live feeds (e.g., https://www.amfiindia.com/spages/NAVAll.txt)
or official AMFI JSON endpoints.
Preserves raw unparsed text strings, exact line numbers, source ID, retrieval timestamp,
and actual source identifiers (AMFI Scheme Code and ISIN) without synthetic identifier generation.
"""

import io
import csv
import json
import ssl
import urllib.request
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple

from models.nav_data import RawNAVRecord
from data.ingestion.base_ingestor import BaseIngestor
from data.ingestion.source_registry import SourceRegistry


class AMFIIngestor(BaseIngestor):
    """Authoritative Live Ingestion adapter for AMFI NAV feeds."""

    DEFAULT_NAV_ALL_URL = "https://www.amfiindia.com/spages/NAVAll.txt"

    def __init__(self, registry: Optional[SourceRegistry] = None, source_id: str = "AMFI_OFFICIAL"):
        super().__init__(source_id, registry or SourceRegistry())

    def fetch_live_amfi_nav_all(
        self,
        url: str = DEFAULT_NAV_ALL_URL,
        timeout: int = 15
    ) -> Tuple[str, datetime, int, str]:
        """
        Performs an actual live HTTP retrieval from official AMFI NAVAll.txt endpoint.
        Returns: (raw_content_text, retrieval_timestamp_utc, http_status_code, content_sha256)
        """
        ts = datetime.now(timezone.utc)
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MutualFundDecisionEngine/1.0"}
        req = urllib.request.Request(url, headers=headers)

        context = ssl.create_default_context()

        with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:
            status_code = resp.status
            raw_bytes = resp.read()
            raw_text = raw_bytes.decode("utf-8", errors="ignore")

        import hashlib
        content_hash = hashlib.sha256(raw_bytes).hexdigest()

        return raw_text, ts, status_code, content_hash

    def parse_raw_amfi_text(self, text_content: str, retrieval_timestamp: Optional[datetime] = None) -> List[RawNAVRecord]:
        """
        Parse raw AMFI text format (both 6-column legacy and 8-column official NAVAll.txt format).
        
        Official 8-column AMFI format:
        Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Plan;Option;Net Asset Value;Date
        Example:
        135762;INF846K01WO1;-;Axis Children's Fund;Direct Plan;Growth Option;29.9628;11-Sep-2026
        """
        ts = retrieval_timestamp or datetime.now(timezone.utc)
        records: List[RawNAVRecord] = []

        lines = text_content.splitlines()
        current_amc = "UNKNOWN_AMC"
        current_category = "UNSPECIFIED"

        for idx, line in enumerate(lines, start=1):
            line_str = line.strip()
            if not line_str or line_str.startswith("#"):
                continue

            # Header row check
            if "Scheme Code" in line_str and "Net Asset Value" in line_str:
                continue

            # Check for AMC or Category Header lines (e.g. "Axis Mutual Fund" or "Open Ended Schemes(...)")
            if ";" not in line_str:
                if "Open Ended Schemes" in line_str or "Close Ended Schemes" in line_str or "Interval Fund" in line_str:
                    current_category = line_str
                elif "Mutual Fund" in line_str or "AMC" in line_str:
                    current_amc = line_str
                continue

            parts = [p.strip() for p in line_str.split(";")]
            if len(parts) >= 6:
                scheme_code = parts[0]
                isin_growth = parts[1] if parts[1] != "-" else ""
                isin_reinvest = parts[2] if len(parts) > 2 and parts[2] != "-" else ""
                scheme_name = parts[3]

                if len(parts) >= 8:
                    # 8-column format
                    plan_str = parts[4]
                    option_str = parts[5]
                    nav_val = parts[6]
                    nav_date = parts[7]
                    full_name = f"{scheme_name} - {plan_str} - {option_str}" if plan_str or option_str else scheme_name
                else:
                    # 6-column format
                    plan_str = ""
                    option_str = ""
                    nav_val = parts[4]
                    nav_date = parts[5]
                    full_name = scheme_name

                # NO SYNTHETIC IDENTIFIER GENERATION: Preserve raw scheme code as is
                rec_id = f"raw_amfi_{scheme_code}_{ts.strftime('%Y%m%d%H%M%S')}_{idx}_{uuid.uuid4().hex[:6]}"
                record = RawNAVRecord(
                    raw_record_id=rec_id,
                    source_id=self.source_id,
                    retrieval_timestamp=ts,
                    raw_scheme_code=scheme_code,
                    raw_scheme_name=full_name,
                    raw_nav_value=nav_val,
                    raw_date=nav_date,
                    raw_line_number=idx,
                    additional_metadata={
                        "base_scheme_name": scheme_name,
                        "plan": plan_str,
                        "option": option_str,
                        "isin_growth": isin_growth,
                        "isin_reinvest": isin_reinvest,
                        "amc_name": current_amc,
                        "category_header": current_category,
                        "raw_line": line_str
                    }
                )
                records.append(record)

        return records

    def parse_raw_csv_snapshot(self, csv_content: str, retrieval_timestamp: Optional[datetime] = None) -> List[RawNAVRecord]:
        """
        Parse raw CSV snapshot (e.g., local amfi_data.csv fixture: scheme_name,nav,date).
        NOTE: Does NOT synthesize AMFI scheme codes if missing.
        """
        ts = retrieval_timestamp or datetime.now(timezone.utc)
        records: List[RawNAVRecord] = []

        reader = csv.DictReader(io.StringIO(csv_content))
        for idx, row in enumerate(reader, start=2):
            scheme_name = row.get("scheme_name", "").strip()
            nav_val = row.get("nav", "").strip()
            nav_date = row.get("date", "").strip()
            # NO SYNTHETIC CODE GENERATION: If scheme_code is absent in CSV row, preserve as empty string
            scheme_code = row.get("scheme_code", "").strip()

            rec_id = f"raw_csv_{idx}_{ts.strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"
            record = RawNAVRecord(
                raw_record_id=rec_id,
                source_id=self.source_id,
                retrieval_timestamp=ts,
                raw_scheme_code=scheme_code,
                raw_scheme_name=scheme_name,
                raw_nav_value=nav_val,
                raw_date=nav_date,
                raw_line_number=idx,
                additional_metadata={"raw_row": row, "is_offline_fixture": True}
            )
            records.append(record)

        return records

    def parse_raw_amfi_json(self, json_data: Any, retrieval_timestamp: Optional[datetime] = None) -> List[RawNAVRecord]:
        """
        Parse raw JSON response from official AMFI API.
        """
        ts = retrieval_timestamp or datetime.now(timezone.utc)
        records: List[RawNAVRecord] = []

        if isinstance(json_data, str):
            try:
                payload = json.loads(json_data)
            except Exception:
                return records
        elif isinstance(json_data, dict):
            payload = json_data
        else:
            return records

        data_groups = payload.get("data", [])
        if not isinstance(data_groups, list):
            return records

        record_idx = 0
        for group in data_groups:
            if not isinstance(group, dict):
                continue
            mf_name = group.get("mfName", "")
            scheme_list = group.get("schemes", [group]) if "schemes" in group else [group]
            if not isinstance(scheme_list, list):
                continue

            for scheme_item in scheme_list:
                if not isinstance(scheme_item, dict):
                    continue
                group_scheme_name = scheme_item.get("schemeName", "")
                nav_list = scheme_item.get("navs", [])
                if not isinstance(nav_list, list):
                    continue

                for nav_item in nav_list:
                    if not isinstance(nav_item, dict):
                        continue
                    record_idx += 1
                    # Preserve real AMFI SD_ID code exactly
                    scheme_code = str(nav_item.get("SD_ID", "")).strip()
                    scheme_name = str(nav_item.get("NAV_Name", "")).strip()
                    nav_val = str(nav_item.get("hNAV_Amt", "")).strip()
                    nav_date = str(nav_item.get("hNAV_Date", "")).strip()

                    rec_id = f"raw_amfi_json_{scheme_code}_{ts.strftime('%Y%m%d%H%M%S')}_{record_idx}_{uuid.uuid4().hex[:6]}"
                    record = RawNAVRecord(
                        raw_record_id=rec_id,
                        source_id=self.source_id,
                        retrieval_timestamp=ts,
                        raw_scheme_code=scheme_code,
                        raw_scheme_name=scheme_name,
                        raw_nav_value=nav_val,
                        raw_date=nav_date,
                        raw_line_number=record_idx,
                        additional_metadata={
                            "amc_name": mf_name,
                            "group_scheme_name": group_scheme_name,
                            "isin_growth": nav_item.get("ISIN_PO") or "",
                            "isin_reinvest": nav_item.get("ISIN_RI") or "",
                            "plan": nav_item.get("Plan"),
                            "option": nav_item.get("Option"),
                            "hNAV_Dtstamp": nav_item.get("hNAV_Dtstamp"),
                            "raw_item": nav_item
                        }
                    )
                    records.append(record)

        return records

    def fetch_raw_data(self, content: Optional[Any] = None, format_type: str = "txt", **kwargs) -> List[RawNAVRecord]:
        """Fetch raw NAV records from provided content string/object or live endpoint if content is None."""
        if content is None:
            raw_text, ts, status, _ = self.fetch_live_amfi_nav_all()
            return self.parse_raw_amfi_text(raw_text, retrieval_timestamp=ts)

        if format_type == "json":
            return self.parse_raw_amfi_json(content)
        if format_type == "csv":
            return self.parse_raw_csv_snapshot(content)
        return self.parse_raw_amfi_text(content)
