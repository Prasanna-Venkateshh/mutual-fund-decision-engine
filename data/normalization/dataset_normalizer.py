"""
Dataset Normalizer (Phase F.9 — Layer B).

Converts raw source evidence records (Layer A) into normalized records (Layer B).
Applies deterministic transformations for dates, floats, plan types, option types,
and scheme metadata without performing downstream financial scoring calculations.
"""

from datetime import date, datetime, timezone
import hashlib
import re
from typing import Optional, Tuple

from models.production_dataset import RawSourceEvidence, NormalizedRecord


class DatasetNormalizer:
    """Normalizes Layer A RawSourceEvidence into Layer B NormalizedRecord."""

    DATE_FORMATS = [
        "%Y-%m-%d",
        "%d-%b-%Y",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%b %d, %Y",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
    ]

    def normalize_raw_evidence(
        self,
        evidence: RawSourceEvidence,
        raw_scheme_code: str,
        raw_scheme_name: str,
        raw_nav_str: str,
        raw_date_str: str,
        raw_category_str: Optional[str] = None,
        raw_subcategory_str: Optional[str] = None,
        raw_amc_name_str: Optional[str] = None,
        raw_ter_str: Optional[str] = None,
        raw_ter_date_str: Optional[str] = None,
        raw_exit_load_str: Optional[str] = None,
        raw_riskometer_str: Optional[str] = None,
        raw_benchmark_str: Optional[str] = None,
        raw_isin_str: Optional[str] = None,
        raw_plan_str: Optional[str] = None,
        raw_option_str: Optional[str] = None,
        raw_lock_in_days: Optional[int] = None,
        raw_lifecycle_status_str: Optional[str] = None,
        raw_launch_date_str: Optional[str] = None
    ) -> NormalizedRecord:
        """
        Normalizes raw fields into a Layer B NormalizedRecord.
        """
        record_id = f"norm_{evidence.evidence_id}_{hashlib.md5(raw_scheme_code.encode()).hexdigest()[:8]}"

        # 1. Parse Dates
        parsed_obs_date = self.parse_date(raw_date_str) or evidence.publication_date or evidence.retrieval_timestamp_utc.date()
        parsed_ter_date = self.parse_date(raw_ter_date_str) if raw_ter_date_str else None
        parsed_launch_date = self.parse_date(raw_launch_date_str) if raw_launch_date_str else None

        # 2. Parse Numeric Floats safely (Missing/N.A. -> None, NEVER 0.0)
        nav_val = self.parse_float(raw_nav_str)
        ter_val = self.parse_float(raw_ter_str)

        # 3. Detect Plan & Option Types
        plan_type = self.detect_plan_type(raw_scheme_name, raw_plan_str)
        option_type = self.detect_option_type(raw_scheme_name, raw_option_str)

        # 4. Normalize Scheme Name & AMC Name
        norm_scheme_name = self.normalize_text(raw_scheme_name)
        norm_amc_name = self.normalize_text(raw_amc_name_str) if raw_amc_name_str else "UNKNOWN_AMC"

        # 5. Normalize Category & Subcategory
        category_str = self.normalize_text(raw_category_str) if raw_category_str else "UNSPECIFIED"
        subcategory_str = self.normalize_text(raw_subcategory_str) if raw_subcategory_str else "UNSPECIFIED"

        # 6. Lock-in Statutory Derivation for ELSS schemes
        lock_in_days = raw_lock_in_days
        if lock_in_days is None and subcategory_str.upper() == "ELSS":
            lock_in_days = 1095

        return NormalizedRecord(
            record_id=record_id,
            raw_evidence_id=evidence.evidence_id,
            source_id=evidence.source_id,
            ingestion_run_id=evidence.ingestion_run_id,
            retrieval_timestamp_utc=evidence.retrieval_timestamp_utc,
            raw_scheme_code=raw_scheme_code.strip(),
            raw_scheme_name=raw_scheme_name.strip(),
            normalized_scheme_name=norm_scheme_name,
            plan_type_str=plan_type,
            option_type_str=option_type,
            amc_name_str=norm_amc_name,
            category_str=category_str,
            subcategory_str=subcategory_str,
            observation_date=parsed_obs_date,
            nav_value=nav_val,
            ter_value=ter_val,
            ter_observation_date=parsed_ter_date,
            exit_load_text=raw_exit_load_str.strip() if raw_exit_load_str else None,
            riskometer_label=raw_riskometer_str.strip().upper() if raw_riskometer_str else None,
            benchmark_name=raw_benchmark_str.strip() if raw_benchmark_str else None,
            isin_code=raw_isin_str.strip().upper() if raw_isin_str else None,
            publication_date=evidence.publication_date,
            lock_in_days=lock_in_days,
            lifecycle_status_str=raw_lifecycle_status_str.strip().upper() if raw_lifecycle_status_str else "ACTIVE",
            launch_date=parsed_launch_date
        )


    def parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parses raw string into date object safely."""
        if not date_str or date_str.strip() in ("", "N.A.", "NA", "-", "null", "None"):
            return None

        clean_str = date_str.strip()
        for fmt in self.DATE_FORMATS:
            try:
                return datetime.strptime(clean_str, fmt).date()
            except ValueError:
                continue

        return None

    def parse_float(self, float_str: Optional[str]) -> Optional[float]:
        """Parses numeric float string safely. Returns None if invalid or missing, NEVER 0.0."""
        if not float_str:
            return None

        clean_str = float_str.strip().replace(",", "")
        if clean_str in ("", "N.A.", "NA", "-", "null", "None"):
            return None

        try:
            val = float(clean_str)
            return val
        except ValueError:
            return None

    def detect_plan_type(self, scheme_name: str, raw_plan_str: Optional[str] = None) -> str:
        """Detects whether scheme name or raw plan string represents a Direct or Regular plan."""
        text_to_check = f"{scheme_name} {raw_plan_str or ''}".upper()
        if "DIRECT" in text_to_check or "- DIR -" in text_to_check or " DIR " in text_to_check:
            return "DIRECT"
        elif "REGULAR" in text_to_check or "- REG -" in text_to_check or " REG " in text_to_check or "RETAIL" in text_to_check:
            return "REGULAR"
        return "UNKNOWN"

    def detect_option_type(self, scheme_name: str, raw_option_str: Optional[str] = None) -> str:
        """Detects option type (Growth vs IDCW/Dividend variants)."""
        text_to_check = f"{scheme_name} {raw_option_str or ''}".upper()
        if "IDCW" in text_to_check or "DIVIDEND" in text_to_check:
            if "REINVEST" in text_to_check:
                return "IDCW_REINVESTMENT"
            elif "PAYOUT" in text_to_check:
                return "IDCW_PAYOUT"
            return "IDCW_PAYOUT"  # Default IDCW variant if unspecified
        elif "GROWTH" in text_to_check or "- GR" in text_to_check:
            return "GROWTH"
        return "UNKNOWN"

    def normalize_text(self, text: Optional[str]) -> str:
        """Normalizes free-form text strings cleanly."""
        if not text:
            return "UNKNOWN"
        cleaned = re.sub(r"\s+", " ", text.strip())
        return cleaned.upper()
