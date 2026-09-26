"""
Data Validation Gate.

Operates BEFORE normalization as required by ARCHITECTURE.md Section 4 & PRODUCT_SPEC.md Section 25.
Validates completeness, date formats, positive NAV values, and isolates malformed data into Quarantine.
Missing data is NEVER silently converted to zero or guessed values.
"""

from datetime import datetime, date, timezone
from typing import Optional, Tuple, List

from models.nav_data import RawNAVRecord, ValidationResult, DataQualityState, QuarantineRecord


class NAVValidator:
    """Validation Gate executing strict data quality rules on raw NAV observations."""

    SUPPORTED_DATE_FORMATS = [
        "%d-%b-%Y",  # e.g., 30-Apr-2026
        "%d-%m-%Y",  # e.g., 30-04-2026
        "%Y-%m-%d",  # e.g., 2026-04-30
        "%d/%m/%Y",  # e.g., 30/04/2026
        "%Y-%m-%dT%H:%M:%S.%fZ",  # e.g., 2015-01-15T00:00:00.000Z
        "%Y-%m-%dT%H:%M:%SZ",    # e.g., 2015-01-15T00:00:00Z
    ]

    def validate_raw_record(self, record: RawNAVRecord) -> ValidationResult:
        """
        Validate a single RawNAVRecord.
        
        Rules:
        1. Scheme code and scheme name must not be empty.
        2. NAV value must parse to a positive float (> 0.0). Zero/negative/N/A values are INVALID.
        3. Date string must parse to a valid date object.
        """
        # Rule 1: Check required string identifiers
        if not record.raw_scheme_name or record.raw_scheme_name.strip() == "":
            return ValidationResult(
                is_valid=False,
                quality_state=DataQualityState.INCOMPLETE,
                error_message="Missing scheme name."
            )

        if not record.raw_scheme_code or record.raw_scheme_code.strip() == "":
            return ValidationResult(
                is_valid=False,
                quality_state=DataQualityState.INCOMPLETE,
                error_message="Missing scheme code."
            )

        # Rule 2: Validate NAV value
        parsed_nav: Optional[float] = None
        try:
            cleaned_nav_str = record.raw_nav_value.replace(",", "").strip()
            parsed_nav = float(cleaned_nav_str)
            if parsed_nav <= 0.0:
                return ValidationResult(
                    is_valid=False,
                    quality_state=DataQualityState.INVALID,
                    error_message=f"Non-positive NAV value: {record.raw_nav_value} (must be > 0.0)."
                )
        except (ValueError, AttributeError):
            return ValidationResult(
                is_valid=False,
                quality_state=DataQualityState.INVALID,
                error_message=f"Unparseable NAV value: '{record.raw_nav_value}'."
            )

        # Rule 3: Validate Date string
        parsed_date: Optional[date] = None
        cleaned_date_str = record.raw_date.strip()
        for fmt in self.SUPPORTED_DATE_FORMATS:
            try:
                dt = datetime.strptime(cleaned_date_str, fmt)
                parsed_date = dt.date()
                break
            except ValueError:
                continue

        if not parsed_date:
            return ValidationResult(
                is_valid=False,
                quality_state=DataQualityState.INVALID,
                error_message=f"Unparseable date string: '{record.raw_date}'."
            )

        # Rule 4: Staleness check (Optional warning flag if date is far in future or ancient)
        if parsed_date > date.today():
            # Future dates could indicate future projections or test data, flag accordingly
            pass

        return ValidationResult(
            is_valid=True,
            quality_state=DataQualityState.VALID,
            parsed_scheme_code=record.raw_scheme_code.strip(),
            parsed_scheme_name=record.raw_scheme_name.strip(),
            parsed_nav=parsed_nav,
            parsed_date=parsed_date
        )

    def process_and_quarantine(self, records: List[RawNAVRecord]) -> Tuple[List[Tuple[RawNAVRecord, ValidationResult]], List[QuarantineRecord]]:
        """
        Batch validate raw records, producing valid tuples and quarantine records.
        Prevents invalid records from silently flowing downstream.
        """
        valid_records: List[Tuple[RawNAVRecord, ValidationResult]] = []
        quarantine_records: List[QuarantineRecord] = []
        now = datetime.now(timezone.utc)

        for idx, rec in enumerate(records, start=1):
            res = self.validate_raw_record(rec)
            if res.is_valid:
                valid_records.append((rec, res))
            else:
                q_id = f"quarantine_{rec.raw_record_id}_{idx}"
                q_rec = QuarantineRecord(
                    quarantine_id=q_id,
                    raw_record_id=rec.raw_record_id,
                    source_id=rec.source_id,
                    reason=res.error_message or "Failed validation gate.",
                    quarantined_at=now,
                    raw_payload=f"code={rec.raw_scheme_code}|name={rec.raw_scheme_name}|nav={rec.raw_nav_value}|date={rec.raw_date}"
                )
                quarantine_records.append(q_rec)

        return valid_records, quarantine_records
